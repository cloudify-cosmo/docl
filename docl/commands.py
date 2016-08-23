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

import sched
import tempfile
import time
import threading

import sh
import argh
import yaml
from watchdog import events
from watchdog import observers
from path import path

from docl import constants
from docl import resources
from docl.configuration import configuration
from docl.work import work
from docl.subprocess import docker
from docl.subprocess import ssh as _ssh
from docl.subprocess import ssh_keygen
from docl.subprocess import cfy
from docl.logs import logger

app = argh.EntryPoint('docl')
command = app


@command
@argh.arg('--simple-manager-blueprint-path', required=True)
def init(simple_manager_blueprint_path=None,
         docker_host=constants.DOCKER_HOST,
         ssh_key_path=constants.SSH_KEY,
         clean_image_docker_tag=constants.CLEAN_IMAGE_DOCKER_TAG,
         installed_image_docker_tag=constants.INSTALLED_IMAGE_DOCKER_TAG,
         source_root=constants.SOURCE_ROOT,
         workdir=None,
         reset=False):
    ssh_key_path = path(ssh_key_path).expanduser()
    simple_manager_blueprint_path = path(
        simple_manager_blueprint_path).expanduser()
    required_files = {
        simple_manager_blueprint_path: 'You must specify a path '
                                       'to a simple manager blueprint',
        ssh_key_path: 'You need to create a key (see man ssh-keygen) first',
    }
    for required_file, message in required_files.items():
        if not required_file.isfile():
            raise argh.CommandError(message)
    configuration.save(
        docker_host=docker_host,
        simple_manager_blueprint_path=simple_manager_blueprint_path.abspath(),
        ssh_key_path=ssh_key_path.abspath(),
        clean_image_docker_tag=clean_image_docker_tag,
        installed_image_docker_tag=installed_image_docker_tag,
        source_root=source_root,
        workdir=workdir,
        reset=reset)
    logger.info('Configuration is saved to {}. Feel free to change it to your '
                'liking.'.format(configuration.conf_path))
    work.init()


@command
def prepare(inputs_output=None):
    inputs_output = inputs_output or constants.INPUTS_YAML
    container_id, container_ip = _create_base_container()
    _ssh_setup(container_id=container_id, container_ip=container_ip)
    _write_inputs(container_ip=container_ip, inputs_path=inputs_output)


@command
@argh.arg('-i', '--inputs', action='append')
def bootstrap(inputs=None):
    inputs = inputs or []
    with tempfile.NamedTemporaryFile() as f:
        prepare(inputs_output=f.name)
        inputs.insert(0, f.name)
        _cfy_bootstrap(inputs=inputs)


@command
def save_image(container_id=None, prepare_agent=False):
    container_id = container_id or work.last_container_id
    docker_tag = configuration.installed_image_docker_tag
    if prepare_agent:
        docker('exec', container_id, 'mkdir', '-p',
               constants.AGENT_TEMPLATE_DIR)
        docker('exec', container_id, 'tar', 'xf',
               configuration.agent_package_path, '--strip=1', '-C',
               constants.AGENT_TEMPLATE_DIR)
    docker.stop(container_id)
    docker.commit(container_id, docker_tag)
    docker.rm('-f', container_id)


@command
def run(mount=False):
    docker_tag = configuration.installed_image_docker_tag
    volumes = _build_volumes() if mount else None
    _run_container(docker_tag=docker_tag, volume=volumes)


@command
def install_docker(version=None, container_id=None):
    container_id = container_id or work.last_container_id
    try:
        exc('which docker', container_id)
        return
    except sh.ErrorReturnCode:
        pass
    cp(resources.DIR / 'docker.repo', ':/etc/yum.repos.d/docker.repo',
       container_id=container_id)
    if not version:
        try:
            version = docker.version('-f', '{{.Client.Version}}').strip()
        except sh.ErrorReturnCode as e:
            version = e.stdout.strip()
    install_docker_command = 'yum install -y -q docker-engine-{}'.format(
        version)
    exc(install_docker_command, container_id=container_id)


@command
def clean(label=None):
    docker_tag1 = configuration.clean_image_docker_tag
    docker_tag2 = configuration.installed_image_docker_tag
    ps_command = [
        '-aq',
        '--filter', 'ancestor={}'.format(docker_tag1),
        '--filter', 'ancestor={}'.format(docker_tag2)
    ]
    if label:
        ps_command += ['--filter', 'label={}']
    containers = docker.ps(ps_command).split('\n')
    containers = [c.strip() for c in containers if c.strip()]
    for container in containers:
        docker.rm('-f', container)


@command
def restart_services(container_id=None, rebuild_agent=False):
    container_id = container_id or work.last_container_id
    for service in configuration.services:
        _restart_service(container_id, service)
    if rebuild_agent:
        build_agent(container_id)


@command
def ssh(container_id=None):
    if not container_id:
        container_ip = work.last_container_ip
    else:
        container_ip = _extract_container_ip(container_id)
    _ssh(container_ip, configuration.ssh_key_path)


@command
def build_agent(container_id=None):
    logger.info('Rebuilding agent package')
    container_id = container_id or work.last_container_id
    docker('exec', container_id, 'tar', 'czf',
           configuration.agent_package_path, '-C',
           path(constants.AGENT_TEMPLATE_DIR).dirname(),
           path(constants.AGENT_TEMPLATE_DIR).basename())


@command
def watch(container_id=None, rebuild_agent=False, interval=2):
    container_id = container_id or work.last_container_id
    services_to_restart = set()
    services_to_restart_lock = threading.Lock()

    class Handler(events.FileSystemEventHandler):
        def __init__(self, services):
            self.services = set(services)

        def on_modified(self, event):
            if event.is_directory:
                with services_to_restart_lock:
                    services_to_restart.update(self.services)
    observer = observers.Observer()
    for package, services in configuration.package_services.items():
        src = '{}/{}/{}'.format(configuration.source_root,
                                configuration.package_dir[package],
                                package)
        observer.schedule(Handler(services), path=src, recursive=True)
    observer.start()

    scheduler = sched.scheduler(time.time, time.sleep)

    def restart_changed_services():
        with services_to_restart_lock:
            current_services_to_restart = services_to_restart.copy()
            services_to_restart.clear()
        for service in current_services_to_restart:
            if service == constants.AGENT_STUB_SERVICE and rebuild_agent:
                build_agent(container_id)
            else:
                _restart_service(container_id, service)
        scheduler.enter(interval, 1, restart_changed_services, ())
    restart_changed_services()

    try:
        scheduler.run()
    except KeyboardInterrupt:
        pass


@command
@argh.named('exec')
def exc(command, container_id=None):
    container_id = container_id or work.last_container_id
    docker('exec', container_id, *command.split(' '))


@command
def cp(source, target, container_id=None):
    container_id = container_id or work.last_container_id
    if source.startswith(':'):
        source = '{}{}'.format(container_id, source)
    elif target.startswith(':'):
        target = '{}{}'.format(container_id, target)
    else:
        raise argh.CommandError('Either source or target should be prefixed '
                                'with : to denote the container.')
    docker.cp(source, target)


def _restart_service(container_id, service):
    logger.info('Restarting {}'.format(service))
    docker('exec', container_id, 'systemctl', 'restart', service)


def _build_volumes():
    # resources should be able to override env packages which is why
    # we use a dist based in the destination directory
    volumes = {}
    for env, packages in configuration.env_packages.items():
        for package in packages:
            src = '{}/{}/{}'.format(configuration.source_root,
                                    configuration.package_dir[package],
                                    package)
            dst = '/opt/{}/env/lib/python2.7/site-packages/{}'.format(env,
                                                                      package)
            volumes[dst] = '{}:{}:ro'.format(src, dst)
    for resource in configuration.resources:
        dst = resource['dst']
        if resource.get('write'):
            permissions = 'rw'
        else:
            permissions = 'ro'
        src = resource['src']
        if not path(src).isabs():
            src = '{}/{}'.format(configuration.source_root, src)
        volumes[dst] = '{}:{}:{}'.format(src, dst, permissions)
    return volumes.values()


def _create_base_container():
    docker_tag = configuration.clean_image_docker_tag
    docker.build('-t', configuration.clean_image_docker_tag, resources.DIR)
    container_id, container_ip = _run_container(docker_tag=docker_tag)
    docker('exec', container_id, 'systemctl', 'start', 'dbus')
    return container_id, container_ip


def _run_container(docker_tag, volume=None):
    volume = volume or []
    expose = configuration.expose
    publish = configuration.publish
    hostname = configuration.container_hostname
    container_id = docker.run(*['--privileged', '--detach'] +
                               ['--hostname={}'.format(hostname)] +
                               ['--expose={}'.format(e) for e in expose] +
                               ['--publish={}'.format(p) for p in publish] +
                               ['--volume={}'.format(v) for v in volume] +
                               [docker_tag]).strip()
    container_ip = _extract_container_ip(container_id)
    work.save_last_container_id_and_ip(container_id=container_id,
                                       container_ip=container_ip)
    return container_id, container_ip


def _extract_container_ip(container_id):
    return docker.inspect(
        '--format={{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id,
    ).strip()


def _ssh_setup(container_id, container_ip):
    ssh_keygen('-R', container_ip)
    docker('exec', container_id, 'mkdir', '-p', '/root/.ssh')
    ssh_public_key = ssh_keygen('-y', '-f', configuration.ssh_key_path).strip()
    with tempfile.NamedTemporaryFile() as f:
        f.write(ssh_public_key)
        f.flush()
        docker.cp(f.name, '{}:/root/.ssh/authorized_keys'.format(container_id))


def _cfy_bootstrap(inputs):
    cfy.init(r=True)
    try:
        from cloudify_cli import env  # noqa
        cfy.bootstrap(configuration.simple_manager_blueprint_path,
                      *['--inputs={}'.format(i) for i in inputs])
    except ImportError:
        cfy_config_path = path('.cloudify') / 'config.yaml'
        cfy_config = yaml.safe_load(cfy_config_path.text())
        cfy_config['colors'] = True
        cfy_config_path.write_text(yaml.safe_dump(cfy_config,
                                                  default_flow_style=False))
        cfy.bootstrap(
            blueprint_path=configuration.simple_manager_blueprint_path,
            *['--inputs={}'.format(i) for i in inputs])


def _write_inputs(container_ip, inputs_path):
    path(inputs_path).write_text(yaml.safe_dump({
        'public_ip': container_ip,
        'private_ip': container_ip,
        'ssh_user': 'root',
        'ssh_key_filename': str(configuration.ssh_key_path),
    }))
