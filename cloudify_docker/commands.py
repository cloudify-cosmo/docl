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

import sys
import sched
import tempfile
import time
import logging
from threading import Lock

import argh
import sh
import yaml
from watchdog import events
from watchdog.observers import Observer
from path import path
from proxy_tools import Proxy

from cloudify_docker import resources
from cloudify_docker.configuration import configuration
from cloudify_docker.work import work


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

PACKAGE_DIR_SERVICES = {
    'amqp_influxdb': {'amqpinflux'},
    'cloudify': {'restservice', 'mgmtworker'},
    'cloudify_agent': {'restservice', 'mgmtworker'},
    'cloudify_rest_client': {'restservice', 'mgmtworker'},
    'dsl_parser': {'restservice', 'mgmtworker'},
    'manager_rest': {'restservice'},
    'plugin_installer': {'restservice', 'mgmtworker'},
    'script_runner': {'restservice', 'mgmtworker'},
    'windows_agent_installer': {'restservice', 'mgmtworker'},
    'windows_plugin_installer': {'restservice', 'mgmtworker'},
    'worker_installer': {'restservice', 'mgmtworker'},
    'cloudify_system_workflows': {'mgmtworker'}
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


def bake(cmd):
    return cmd.bake(_err_to_out=True,
                    _out=lambda l: sys.stdout.write(l),
                    _tee=True)


def docker_proxy():
    return bake(sh.docker).bake('-H', configuration.docker_host)


logger = logging.getLogger(__name__)

app = argh.EntryPoint('cloudify-docker')
command = app

docker = Proxy(docker_proxy)
ssh_keygen = bake(sh.Command('ssh-keygen'))
cfy = bake(sh.cfy)


@command
@argh.arg('--simple-manager-blueprint-path', required=True)
def init(docker_host='fd://',
         ssh_key_path='~/.ssh/.id_rsa',
         simple_manager_blueprint_path=None,
         clean_image_docker_tag='cloudify/centos-manager:7',
         installed_image_docker_tag='cloudify/centos-manager-installed:7',
         source_root='~/dev/cloudify',
         workdir=None,
         reset=False):
    ssh_key_path = path(ssh_key_path).expanduser()
    simple_manager_blueprint_path = path(
        simple_manager_blueprint_path).expanduser()
    required_files = {
        simple_manager_blueprint_path: 'You must specify a path '
                                       'to a manager blueprint',
        ssh_key_path: 'You need to create a key (see man ssh-keygen) first',
    }
    for required_file, message in required_files.items():
        if not required_file.isfile():
            raise argh.CommandError(message)

    ssh_public_key = ssh_keygen('-y', '-f', ssh_key_path).stdout.strip()

    configuration.save(
        docker_host=docker_host,
        simple_manager_blueprint_path=simple_manager_blueprint_path.abspath(),
        ssh_key_path=ssh_key_path.abspath(),
        ssh_public_key=ssh_public_key,
        clean_image_docker_tag=clean_image_docker_tag,
        installed_image_docker_tag=installed_image_docker_tag,
        source_root=source_root,
        workdir=workdir,
        reset=reset)
    work.init()


@command
def bootstrap(inputs=None):
    inputs = inputs or []
    container_id, container_ip = _create_base_container()
    _ssh_setup(container_id=container_id, container_ip=container_ip)
    _cfy_bootstrap(container_ip=container_ip, inputs=inputs)


@command
def save_image(container_id=None):
    container_id = container_id or work.last_container_id
    docker_tag = configuration.installed_image_docker_tag
    docker.stop(container_id)
    docker.commit(container_id, docker_tag)
    docker.rm('-f', container_id)


@command
def run(mount=False):
    docker_tag = configuration.installed_image_docker_tag
    volumes = None
    if mount:
        volumes = _build_volumes()
    _run_container(docker_tag=docker_tag, volume=volumes)


@command
def restart_services(container_id=None):
    container_id = container_id or work.last_container_id
    for service in ['amqpinflux', 'mgmtworker', 'restservice']:
        _restart_service(container_id, service)


def _restart_service(container_id, service):
    service_name = 'cloudify-{}'.format(service)
    logger.info('Restarting {}'.format(service_name))
    docker('exec', container_id, 'systemctl', 'restart', service_name)


@command
def watch(container_id=None):
    container_id = container_id or work.last_container_id
    services_to_restart = set()
    services_to_restart_lock = Lock()

    class Handler(events.FileSystemEventHandler):
        def __init__(self, services, package):
            self.services = services
            self.package = package

        def on_modified(self, ev):
            if ev.is_directory and ev.event_type == events.EVENT_TYPE_MODIFIED:
                with services_to_restart_lock:
                    services_to_restart.update(self.services)
    observer = Observer()
    for package, services in PACKAGE_DIR_SERVICES.items():
        src = '{}/{}/{}'.format(configuration.source_root,
                                PACKAGE_DIR[package],
                                package)
        observer.schedule(Handler(services, package),
                          path=src,
                          recursive=True)
    observer.start()

    scheduler = sched.scheduler(time.time, time.sleep)

    def restart_changed_services():
        with services_to_restart_lock:
            current_services_to_restart = services_to_restart.copy()
            services_to_restart.clear()
        while current_services_to_restart:
            service = current_services_to_restart.pop()
            _restart_service(container_id, service)
        scheduler.enter(2, 1, restart_changed_services, ())
    restart_changed_services()

    try:
        scheduler.run()
    except KeyboardInterrupt:
        pass


def _build_volumes():
    volumes = []
    for env, packages in ENV_PACKAGES.items():
        for package in packages:
            src = '{}/{}/{}'.format(configuration.source_root,
                                    PACKAGE_DIR[package],
                                    package)
            dst = '/opt/{}/env/lib/python2.7/site-packages/{}'.format(env,
                                                                      package)
            volumes.append('{}:{}:ro'.format(src, dst))
    return volumes


@command
def clean():
    docker_tag = configuration.installed_image_docker_tag
    containers = docker.ps('-aq', '--filter', 'ancestor={}'.format(docker_tag)
                           ).strip().split('\n')
    containers = [c.strip() for c in containers if c.strip()]
    if containers:
        docker.rm('-f', ' '.join(containers))


def _create_base_container():
    docker_tag = configuration.clean_image_docker_tag
    docker.build('-t', configuration.clean_image_docker_tag, resources.DIR)
    container_id, container_ip = _run_container(docker_tag=docker_tag,
                                                expose=EXPOSE,
                                                publish=PUBLISH)
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
    work.save_last_container_id_and_ip(container_id=container_id,
                                       container_ip=container_ip)
    return container_id, container_ip


def _ssh_setup(container_id, container_ip):
    ssh_keygen('-R', container_ip)
    try:
        docker('exec', container_id, 'mkdir', '-m700', '/root/.ssh')
    except sh.ErrorReturnCode as e:
        if e.exit_code != 1:
            raise
    with tempfile.NamedTemporaryFile() as f:
        f.write(configuration.ssh_public_key)
        f.flush()
        docker.cp(f.name, '{}:/root/.ssh/authorized_keys'.format(container_id))


def _cfy_bootstrap(container_ip, inputs):
    with tempfile.NamedTemporaryFile() as f:
        f.write(yaml.safe_dump({
            'public_ip': container_ip,
            'private_ip': container_ip,
            'ssh_user': 'root',
            'ssh_key_filename': str(configuration.ssh_key_path),
        }))
        f.flush()
        inputs.insert(0, f.name)
        cfy.init('-r')
        cfy.bootstrap(
            blueprint_path=configuration.simple_manager_blueprint_path,
            *['--inputs={}'.format(i) for i in inputs])
