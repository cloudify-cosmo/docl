########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import tempfile

import argh
import sh
import yaml

from cloudify_docker import resources


EXPOSE = [22, 80, 443, 5671]
PUBLISH = []


PACKAGE_DIR = {
    'amqp_influxdb': 'cloudify-amqp-influxdb',
    'cloudify': 'cloudify-plugins-common',
    'cloudify_agent': 'cloudify-agent',
    'cloudify_rest_client': 'cloudify-rest-client',
    'dsl_parser': 'cloudify-dsl-parser',
    'manager_rest': 'cloudify-manager/rest-service',
    'plugin_installer': 'cloudify-agent',
    'script_runner': 'cloudify-script-plugin',
    'windows_agent_installer': 'cloudify-agent',
    'windows_plugin_installer': 'cloudify-agent',
    'worker_installer': 'cloudify-agent',
    'cloudify_system_workflows': 'cloudify-manager/workflows'
}

ENV_PACKAGES = {
    'amqpinflux': [
        'amqp_influxdb'
    ],
    'manager': [
        'cloudify',
        'cloudify_agent',
        'cloudify_rest_client',
        'dsl_parser',
        'manager_rest',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
    ],
    'mgmtworker': [
        'cloudify',
        'cloudify_agent',
        'cloudify_system_workflows',
        'cloudify_rest_client',
        'dsl_parser',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
    ]
}


app = argh.EntryPoint('cloudify-docker')
command = app


def bake(cmd):
    return cmd.bake(_err_to_out=True,
                    _out=lambda l: sys.stdout.write(l),
                    _tee=True)


docker = bake(sh.docker)
ssh_keygen = bake(sh.Command('ssh-keygen'))
cfy = bake(sh.cfy)


@command
def bootstrap(simple_blueprint_manager_path,
              ssh_key='~/.ssh/.id_rsa',
              docker_tag='cloudify/centos-manager:7',
              inputs=None):
    inputs = inputs or []
    required_files = {
        simple_blueprint_manager_path: 'You must specify a path '
                                       'to a manager blueprint',
        ssh_key: 'You need to create a key (see man ssh-keygen) first',
        '{}.pub'.format(ssh_key): 'The ssh public key is expected to exist'
                                  ' at {}'.format('{}.pub'.format(ssh_key))
    }
    for required_file, message in required_files.items():
        if not os.path.isfile(required_file):
            raise argh.CommandError(message)
    container_id, container_ip = _create_base_container(docker_tag=docker_tag)
    _ssh_setup(container_id=container_id,
               container_ip=container_ip,
               ssh_key=ssh_key)
    _cfy_bootstrap(simple_blueprint_manager_path=simple_blueprint_manager_path,
                   container_ip=container_ip,
                   ssh_key=ssh_key,
                   inputs=inputs)


@command
def save(container_id,
         docker_tag='cloudify/centos-manager-installed:7'):
    docker.stop(container_id)
    docker.commit(container_id, docker_tag)
    docker.rm('-f', container_id)


@command
def run(docker_tag='cloudify/centos-manager-installed:7',
        source_root=None):
    volumes = None
    if source_root:
        source_root = os.path.expanduser(source_root)
        volumes = _build_volumes(source_root)
    _run_container(docker_tag=docker_tag, volume=volumes)


@command
def restart_services(container_id):
    for service in ['amqpinflux', 'mgmtworker', 'restservice']:
        docker('exec', container_id, 'systemctl', 'restart',
               'cloudify-{}'.format(service))


def _build_volumes(source_root):
    volumes = []
    for env, packages in ENV_PACKAGES.items():
        for package in packages:
            src = '{}/{}/{}'.format(source_root,
                                    PACKAGE_DIR[package],
                                    package)
            dst = '/opt/{}/env/lib/python2.7/site-packages/{}'.format(
                env, package)
            volumes.append('{}:{}:ro'.format(src, dst))
    return volumes


@command
def clean(docker_tag='cloudify/centos-manager-installed:7'):
    containers = docker.ps('-aq', '--filter', 'ancestor={}'.format(docker_tag)
                           ).strip().split('\n')
    containers = [c.strip() for c in containers if c.strip()]
    if containers:
        docker.rm('-f', ' '.join(containers))


def _create_base_container(docker_tag):
    docker.build('-t', docker_tag, resources.DIR)
    container_id, container_ip = _run_container(docker_tag=docker_tag,
                                                expose=EXPOSE,
                                                publish=PUBLISH)
    # DBus is used by the manager for cfy status
    docker('exec', container_id, 'systemctl', 'start', 'dbus')
    return container_id, container_ip


def _run_container(docker_tag, expose=None, publish=None, volume=None):
    expose = expose or []
    publish = publish or []
    volume = volume or []

    container_id = docker.run(*['--privileged', '--detach'] +
                               ['--hostname=cfy-manager'] +
                               ['--expose={}'.format(e) for e in expose] +
                               ['--publish={}'.format(p) for p in publish] +
                               ['--volume={}'.format(v) for v in volume] +
                               [docker_tag]).strip()
    container_ip = docker.inspect(
        '--format={{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id,
    ).strip()
    return container_id, container_ip


def _ssh_setup(container_id, container_ip, ssh_key):
    """
    Inject the user's SSH key into root's authorized_keys
    Also clears out references to the container's IP in the local known_hosts
    """
    # Remove old keys referring to the container's IP
    ssh_keygen('-R', container_ip)
    # new container shouldn't have an authorized_keys file yet
    try:
        docker('exec', container_id, 'mkdir', '-m700', '/root/.ssh')
    except sh.ErrorReturnCode as e:
        if e.exit_code != 1:
            raise
            # Hopefully that means it's already there
    docker.cp('{}.pub'.format(ssh_key),
              '{id}:/root/.ssh/authorized_keys'.format(id=container_id))


def _cfy_bootstrap(simple_blueprint_manager_path,
                   container_ip,
                   ssh_key,
                   inputs):
    with tempfile.NamedTemporaryFile() as f:
        f.write(yaml.safe_dump({
            'public_ip': container_ip,
            'private_ip': container_ip,
            'ssh_user': 'root',
            'ssh_key_filename': ssh_key,
        }))
        f.flush()
        inputs.insert(0, f.name)
        cfy.init('-r')
        cfy.bootstrap(blueprint_path=simple_blueprint_manager_path,
                      *['--inputs={}'.format(i) for i in inputs])
