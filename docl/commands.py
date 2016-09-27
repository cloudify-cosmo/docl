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

import json
import sched
import shlex
import tempfile
import time
import threading
import os
import base64

import sh
import argh
import yaml
import requests
from watchdog import events
from watchdog import observers
from path import path

from cloudify_cli import env as cli_env

from docl import constants
from docl import resources
from docl import resources_server
from docl import files
from docl.configuration import configuration
from docl.work import work
from docl.subprocess import docker
from docl.subprocess import quiet_docker
from docl.subprocess import ssh as _ssh
from docl.subprocess import ssh_keygen
from docl.subprocess import ssh_keyscan
from docl.subprocess import cfy
from docl.subprocess import gzip
from docl.logs import logger

app = argh.EntryPoint('docl')
command = app


@command
@argh.arg('--simple-manager-blueprint-path', required=True)
def init(simple_manager_blueprint_path=None,
         docker_host=constants.DOCKER_HOST,
         ssh_key_path=constants.SSH_KEY,
         clean_image_docker_tag=constants.CLEAN_IMAGE_DOCKER_TAG,
         manager_image_docker_tag=constants.MANAGER_IMAGE_DOCKER_TAG,
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
        manager_image_docker_tag=manager_image_docker_tag,
        source_root=source_root,
        workdir=workdir,
        reset=reset)
    logger.info('Configuration is saved to {}. Feel free to change it to your '
                'liking.'.format(configuration.conf_path))
    work.init()


@command
@argh.arg('-l', '--label', action='append')
def prepare(inputs_output=None, label=None, details_path=None, tag=None):
    inputs_output = inputs_output or constants.INPUTS_YAML
    container_id, container_ip = _create_base_container(
        label=label,
        details_path=details_path,
        tag=tag)
    logger.info('Container {0} started on ip {1}'
                .format(container_id, container_ip))
    _ssh_setup(container_id=container_id, container_ip=container_ip)
    _write_inputs(container_ip=container_ip, inputs_path=inputs_output)


@command
@argh.arg('-i', '--inputs', action='append')
@argh.arg('-l', '--label', action='append')
def bootstrap(inputs=None, label=None, details_path=None, tag=None,
              container_id=None,
              serve_resources_tar=False,
              serve_resources_tar_invalidate_cache=False,
              serve_resources_tar_no_progress=False,
              cfy_args=None):
    inputs = inputs or []
    with tempfile.NamedTemporaryFile() as f:
        if not container_id:
            prepare(inputs_output=f.name,
                    label=label,
                    details_path=details_path,
                    tag=tag)
            inputs.insert(0, f.name)
        if serve_resources_tar:
            with resources_server.with_server(
                    invalidate_cache=serve_resources_tar_invalidate_cache,
                    no_progress=serve_resources_tar_no_progress) as url:
                inputs.append('manager_resources_package={}'.format(url))
                _cfy_bootstrap(inputs=inputs, cfy_args=cfy_args)
        else:
            _cfy_bootstrap(inputs=inputs, cfy_args=cfy_args)


@command
def restart_container(container_id=None):
    container_id = container_id or work.last_container_id
    quiet_docker.restart(container_id, time=0)


@command
def save_image(container_id=None,
               tag=None,
               output_file=None,
               skip_agent_prepare=False):
    container_id = container_id or work.last_container_id
    docker_tag = tag or configuration.manager_image_docker_tag
    logger.info('Preparing manager container before saving as docker image')
    _run_container_preparation_scripts(container_id, skip_agent_prepare)
    logger.info('Saving manager container to image {}'.format(docker_tag))
    quiet_docker.stop(container_id)
    quiet_docker.commit(container_id, docker_tag)
    logger.info("Removing container. Run 'docl run' to start it again")
    quiet_docker.rm('-f', container_id)
    if output_file:
        logger.info('Saving manager image to {}. This may take a while'
                    .format(output_file))
        gzip(quiet_docker.save(docker_tag,
                               _piped=True,
                               _tty_out=False,
                               _out_bufsize=constants.BUFFER_SIZE),
             _in_bufsize=constants.BUFFER_SIZE,
             _out=output_file)


def _run_container_preparation_scripts(container_id, skip_agent_prepare):
    cp(source=resources.DIR / 'update_running_system.py',
       target=':{}'.format(constants.PY_SCRIPT_TARGET_PATH),
       container_id=container_id)
    cp(source=resources.DIR / 'prepare_save_image.py',
       target=':{}'.format(constants.PREPARE_SAVE_IMAGE_TARGET_PATH),
       container_id=container_id)
    params = {
        'data_json_path': constants.DATA_JSON_TARGET_PATH,
        'pydevd_egg_url': configuration.pydevd_egg_url,
        'skip_agent_prepare': skip_agent_prepare,
        'agent_template_dir': constants.AGENT_TEMPLATE_DIR,
        'agent_package_path': configuration.agent_package_path,
        'credentials_path': constants.CREDENTIALS_TARGET_PATH,
        'admin_username': cli_env.get_username(),
        'admin_password': cli_env.get_password()
    }
    docker('exec', container_id, 'python',
           constants.PREPARE_SAVE_IMAGE_TARGET_PATH,
           base64.b64encode(json.dumps(params)))

@command
def pull_image(no_progress=False):
    online_sha1 = requests.get(
        configuration.manager_image_commit_sha_url).text.strip()
    local_sha1 = work.last_pulled_image_commit_sha1
    if online_sha1 == local_sha1:
        logger.info('Current image is the latest image. It is based on the '
                    'following commit in the manager blueprints repo: {}'
                    .format(local_sha1))
        return
    logger.info('Download manager image from {} to {}'
                .format(configuration.manager_image_url,
                        work.pulled_image_path))
    if os.path.exists(work.pulled_image_path):
        os.remove(work.pulled_image_path)
    files.download(url=configuration.manager_image_url,
                   output_path=work.pulled_image_path,
                   no_progress=no_progress)
    logger.info('Loading image into docker')
    docker.load(gzip('-dc', work.pulled_image_path,
                     _piped=True,
                     _out_bufsize=constants.BUFFER_SIZE),
                _in_bufsize=constants.BUFFER_SIZE)
    work.last_pulled_image_commit_sha1 = online_sha1


@command
@argh.arg('-t', '--tag', required=True)
def remove_image(tag=None):
    logger.info('Removing image {}'.format(tag))
    quiet_docker.rmi(tag)


@command
@argh.arg('-l', '--label', action='append')
def run(mount=False, label=None, details_path=None, tag=None):
    docker_tag = tag or configuration.manager_image_docker_tag
    volumes = _build_volumes() if mount else None
    container_id, container_ip = _run_container(docker_tag=docker_tag,
                                                volume=volumes,
                                                label=label,
                                                details_path=details_path)
    _ssh_setup(container_id, container_ip)
    _update_container(container_id, container_ip)
    cfy.use(container_ip)


def _update_container(container_id, container_ip):
    logger.info('Updating files on the container')
    with tempfile.NamedTemporaryFile() as f:
        json.dump({
            'ip': container_ip,
            'services': constants.ALL_IP_SERVICES,
            'credentials_path': constants.CREDENTIALS_TARGET_PATH,
            'rest_port': cli_env.profile.rest_port,
            'rest_protocol': cli_env.profile.rest_protocol,
            'is_debug_on': bool(os.environ.get('DEBUG_MODE')),
            'host_ip': resources_server.get_host()
        }, f)
        f.flush()
        cp(source=f.name,
           target=':{}'.format(constants.DATA_JSON_TARGET_PATH),
           container_id=container_id)
    docker('exec', container_id,
           '/opt/mgmtworker/env/bin/python', '-u',
           constants.PY_SCRIPT_TARGET_PATH,
           constants.DATA_JSON_TARGET_PATH)


@command
def install_docker(version=None, container_id=None):
    container_id = container_id or work.last_container_id
    try:
        quiet_docker('exec', container_id, *'which docker'.split(' '))
        logger.info('Docker already installed on container. Doing nothing')
        return
    except sh.ErrorReturnCode:
        pass
    cp(resources.DIR / 'docker.repo', ':/etc/yum.repos.d/docker.repo',
       container_id=container_id)
    if not version:
        try:
            version = quiet_docker.version('-f', '{{.Client.Version}}').strip()
        except sh.ErrorReturnCode as e:
            version = e.stdout.strip()
    install_docker_command = 'yum install -y -q docker-engine-{}'.format(
        version)
    docker('exec', container_id, *install_docker_command.split(' '))


@command
@argh.arg('-l', '--label', action='append')
def clean(label=None):
    label = label or []
    docker_tag1 = configuration.clean_image_docker_tag
    docker_tag2 = configuration.manager_image_docker_tag
    ps_command = [
        '-aq',
        '--filter', 'ancestor={}'.format(docker_tag1),
        '--filter', 'ancestor={}'.format(docker_tag2)
    ]
    for l in label:
        ps_command += ['--filter', 'label={}'.format(l)]
    containers = quiet_docker.ps(ps_command).split('\n')
    containers = [c.strip() for c in containers if c.strip()]
    logger.info('Removing containers')
    for container in containers:
        docker.rm('-f', container)


@command
def restart_services(container_id=None):
    container_id = container_id or work.last_container_id
    for service in configuration.services:
        _restart_service(container_id, service)


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
    quiet_docker('exec', container_id, 'tar', 'czf',
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

    message = 'Filesystem watch started.'
    if rebuild_agent:
        message = ('{} Relevant services will be restarted and CentOS agent '
                   'package (dockercompute) rebuilt on code changes.'
                   .format(message))
    else:
        message = ('{} Relevant services will be restarted on code changes. '
                   'Use --rebuild-agent to also rebuild Centos agent package '
                   '(dockercompute) on code changes.'
                   .format(message))
    logger.info(message)
    try:
        scheduler.run()
    except KeyboardInterrupt:
        pass


@command
@argh.named('exec')
def exc(command, container_id=None):
    container_id = container_id or work.last_container_id
    docker('exec', container_id, *shlex.split(command))


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
    quiet_docker.cp(source, target)


@command
def serve_resources_tar(invalidate_cache=False, no_progress=False):
    with resources_server.with_server(invalidate_cache=invalidate_cache,
                                      no_progress=no_progress):
        while True:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                break


def _restart_service(container_id, service):
    logger.info('Restarting {}'.format(service))
    quiet_docker('exec', container_id, 'systemctl', 'restart', service)


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


def _create_base_container(label, details_path, tag):
    docker_tag = tag or configuration.clean_image_docker_tag
    docker.build('-t', configuration.clean_image_docker_tag, resources.DIR)
    container_id, container_ip = _run_container(docker_tag=docker_tag,
                                                details_path=details_path,
                                                label=label)
    quiet_docker('exec', container_id, 'systemctl', 'start', 'dbus')
    return container_id, container_ip


def _run_container(docker_tag, volume=None, label=None, details_path=None):
    label = label or []
    volume = volume or []
    expose = configuration.expose
    publish = configuration.publish
    hostname = configuration.container_hostname
    container_id = quiet_docker.run(
        *['--privileged', '--detach'] +
         ['--hostname={}'.format(hostname)] +
         ['--expose={}'.format(e) for e in expose] +
         ['--publish={}'.format(p) for p in publish] +
         ['--volume={}'.format(v) for v in volume] +
         ['--label={}'.format(l) for l in label] +
         [docker_tag]).strip()
    container_ip = _extract_container_ip(container_id)
    work.save_last_container_id_and_ip(container_id=container_id,
                                       container_ip=container_ip)
    if details_path:
        _write_container_details(container_id=container_id,
                                 container_ip=container_ip,
                                 details_path=details_path)
    return container_id, container_ip


def _extract_container_ip(container_id):
    return quiet_docker.inspect(
        '--format={{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id,
    ).strip()


def _ssh_setup(container_id, container_ip):
    logger.info('Applying ssh configuration to manager container')
    try:
        known_hosts = path('~/.ssh/known_hosts').expanduser()
        # Known hosts file may not exist
        ssh_keygen('-R', container_ip)
        fingerprint = None
        while not fingerprint:
            fingerprint = ssh_keyscan(
                container_ip).stdout.split('\n')[0].strip()
            time.sleep(0.01)
        if fingerprint and known_hosts.exists():
            current = known_hosts.text()
            prefix = ''
            if not current.endswith('\n'):
                prefix = '\n'
            known_hosts.write_text(
                '{}{}\n'.format(prefix, fingerprint), append=True)
    except sh.ErrorReturnCode:
        pass
    quiet_docker('exec', container_id, 'mkdir', '-p', '/root/.ssh')
    ssh_public_key = ssh_keygen('-y', '-f', configuration.ssh_key_path).strip()
    with tempfile.NamedTemporaryFile() as f:
        f.write(ssh_public_key)
        f.flush()
        quiet_docker.cp(f.name, '{}:/root/.ssh/authorized_keys'.format(
            container_id))


def _cfy_bootstrap(inputs, cfy_args):
    cfy.init(r=True)
    args = ['--inputs={}'.format(i) for i in inputs]
    if cfy_args:
        args += shlex.split(cfy_args)
    try:
        from cloudify_cli import env  # noqa
        cfy.bootstrap(configuration.simple_manager_blueprint_path, *args)
    except ImportError:
        cfy_config_path = path('.cloudify') / 'config.yaml'
        cfy_config = yaml.safe_load(cfy_config_path.text())
        cfy_config['colors'] = True
        cfy_config_path.write_text(yaml.safe_dump(cfy_config,
                                                  default_flow_style=False))
        cfy.bootstrap(
            blueprint_path=configuration.simple_manager_blueprint_path, *args)


def _write_inputs(container_ip, inputs_path):
    path(inputs_path).write_text(yaml.safe_dump({
        'public_ip': container_ip,
        'private_ip': container_ip,
        'ssh_user': 'root',
        'ssh_key_filename': str(configuration.ssh_key_path),
        'dsl_resources': [],
    }))


def _write_container_details(container_id, container_ip, details_path):
    path(details_path).write_text(yaml.safe_dump({
        'id': container_id,
        'ip': container_ip,
    }))
