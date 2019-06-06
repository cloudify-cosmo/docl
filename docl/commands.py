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
from time import sleep

from cloudify_cli import env as cli_env

from docl import constants
from docl import resources
from docl import install_rpm_server
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
@argh.arg(
    '-u', '--manager-image-url',
    help="Manager image URL. If specified, `docl pull-image` will download an "
         "image from this URL.")
@argh.arg(
    '-m', '--manager-image-docker-tag',
    help="Default Docker image tag to use (for example `docl run` with no "
         "parameters will use this value to run a local image with this tag).")
@argh.arg(
    '-a', '--manager-image-commit-sha-url',
    help="URL for the checksum of the provided Manager image file. Used to "
         "prevent downloading the last image downloaded with `docl pull-image`"
         ", again.")
def init(manager_image_url=constants.MANAGER_IMAGE_URL,
         manager_image_docker_tag=constants.MANAGER_IMAGE_DOCKER_TAG,
         manager_image_commit_sha_url=constants.MANAGER_IMAGE_COMMIT_SHA_URL,
         docker_host=None,
         ssh_key_path=constants.SSH_KEY,
         clean_image_docker_tag=constants.CLEAN_IMAGE_DOCKER_TAG,
         source_root=constants.SOURCE_ROOT,
         workdir=None,
         reset=False,
         debug_ip=None):
    ssh_key_path = path(ssh_key_path).expanduser()
    if not ssh_key_path.isfile():
        raise argh.CommandError(
            'You need to create a key (see man ssh-keygen) first'
        )
    configuration.save(
        docker_host=docker_host,
        ssh_key_path=ssh_key_path.abspath(),
        clean_image_docker_tag=clean_image_docker_tag,
        manager_image_docker_tag=manager_image_docker_tag,
        source_root=source_root,
        workdir=workdir,
        reset=reset,
        debug_ip=debug_ip,
        manager_image_url=manager_image_url,
        manager_image_commit_sha_url=manager_image_commit_sha_url)
    logger.info('Configuration is saved to {}. Feel free to change it to your '
                'liking.'.format(configuration.conf_path))
    work.init()


@command
@argh.arg('-l', '--label', action='append')
def prepare(config_output=None, label=None, details_path=None, tag=None):
    config_output = config_output or constants.CONFIG_YAML
    container_id, container_ip = _create_base_container(
        label=label,
        details_path=details_path,
        tag=tag)
    logger.info('Container {0} started on ip {1}'
                .format(container_id, container_ip))
    _ssh_setup(container_id=container_id, container_ip=container_ip)
    _write_config(container_ip=container_ip, config_path=config_output)
    return container_id, container_ip


@command
@argh.arg('-i', '--inputs', action='append')
@argh.arg('-l', '--label', action='append')
def bootstrap(inputs=None, label=None, details_path=None, tag=None,
              container_id=None,
              serve_install_rpm=False,
              serve_install_rpm_invalidate_cache=False,
              serve_install_rpm_no_progress=False,
              rpm_url=None):
    inputs = inputs or []
    with tempfile.NamedTemporaryFile() as f:
        if not container_id:
            container_id, _ = prepare(config_output=f.name,
                                      label=label,
                                      details_path=details_path,
                                      tag=tag)
            inputs.insert(0, f.name)
        if serve_install_rpm:
            with install_rpm_server.with_server(
                    invalidate_cache=serve_install_rpm_invalidate_cache,
                    no_progress=serve_install_rpm_no_progress) as url:
                _install_manager(container_id, config_path=f.name, rpm_url=url)
        else:
            _install_manager(container_id, config_path=f.name, rpm_url=rpm_url)


def _install_manager(container_id, config_path, rpm_url=None):
    rpm_url = rpm_url or install_rpm_server.get_rpm_url()
    logger.info('Downloading install RPM from: {0}'.format(rpm_url))
    exc(
        'curl {0} -o {1}'.format(rpm_url, constants.INSTALL_RPM_PATH),
        container_id
    )
    logger.info('Installing RPM...')
    exc(
        'yum install -y {0}'.format(constants.INSTALL_RPM_PATH),
        container_id
    )
    logger.info('Removing install RPM...')
    exc('rm {0}'.format(constants.INSTALL_RPM_PATH))
    logger.info('Copying configuration...')
    cp(config_path, ':/etc/cloudify/config.yaml')
    logger.info('Installing Cloudify Manager...')
    exc('cfy_manager install', container_id)


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
    cp(source=resources.DIR / 'prepare_save_image.py',
       target=':{}'.format(constants.PREPARE_SAVE_IMAGE_TARGET_PATH),
       container_id=container_id)
    params = {
        'data_json_path': constants.DATA_JSON_TARGET_PATH,
        'skip_agent_prepare': skip_agent_prepare,
        'agent_template_dir': constants.AGENT_TEMPLATE_DIR,
        'agent_package_path': configuration.agent_package_path
    }
    output = docker('exec', container_id, 'python',
                    constants.PREPARE_SAVE_IMAGE_TARGET_PATH,
                    base64.b64encode(json.dumps(params)))

    # The last line printed by the script is the location of cfy_manager dir
    cfy_manager_location = output.strip().split('\n')[-1]
    configuration.update_cfy_manager_location(cfy_manager_location)


@command
def pull_image(no_progress=False):
    # try contacting the docker daemon first, to break early if it's not
    # reachable - before the long download
    quiet_docker.version()

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
    logger.info('Loading image into docker (may take a while)')
    quiet_docker.load(gzip('-dc', work.pulled_image_path,
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
@argh.arg('-n', '--name')
def run(mount=False, label=None, name=None, details_path=None, tag=None,
        mount_docker=False):
    docker_tag = tag or configuration.manager_image_docker_tag
    volumes = _build_volumes() if mount else []
    if mount_docker:
        volumes += _mount_docker_volumes()
    container_id, container_ip = _run_container(docker_tag=docker_tag,
                                                volume=volumes,
                                                label=label,
                                                name=name,
                                                details_path=details_path)
    _ssh_setup(container_id, container_ip)

    credentials = _get_manager_credentials(container_id)
    _retry(_get_credentials_and_use_manager, credentials, container_ip)
    _update_container(container_id, container_ip)


def _mount_docker_volumes():
    """Volume configuration for mounting the docker socket.

    This allows mounting the docker socket (if specified in docker_host,
    or /var/run/docker.sock by default).
    Systemd will clean /var/run on startup, so this mounts the socket
    in /tmp, and provides a systemd unit that links that to /var/run.

    Returns a list of arguments to be used with --volume in docker run.
    """
    docker_host = configuration.docker_host
    if docker_host and not docker_host.startswith('unix:'):
        raise argh.CommandError('Mounting the docker socket is only possible '
                                'when docker_host is a unix socket (and '
                                'starts with unix://), but was {0}'
                                .format(configuration.docker_host))
    docker_host = docker_host.replace('unix://', '')
    copy_service_path = ('/etc/systemd/system/multi-user.target.wants'
                         '/link-docker-socket.service')

    return [
        '{0}:{1}'.format(resources.DIR / 'link-docker-socket.service',
                         copy_service_path),
        '{0}:/tmp/docker.sock'.format(docker_host)
    ]


def _retry(func, *args, **kwargs):
    for _ in range(300):
        try:
            func(*args, **kwargs)
            break
        except sh.ErrorReturnCode:
            sleep(0.1)
    else:
        raise argh.CommandError()


def _get_manager_credentials(container_id):
    """ Read the cloudify CLI profile context from the container """

    result = quiet_docker(
        'exec',
        container_id,
        'cat',
        constants.CLOUDIFY_CONTEXT_PATH
    )
    context_str = result.strip()

    # Getting rid of the first line, as it contains !CloudifyProfileContext
    first_line_break = context_str.find('\n') + 1
    context_str = context_str[first_line_break:]

    return yaml.load(context_str)


def _get_credentials_and_use_manager(credentials, container_ip):
    cfy.profiles.use(container_ip, skip_credentials_validation=True)
    # Using sh.cfy directly to avoid extra output
    sh.cfy.profiles.set(
        manager_username=credentials['manager_username'],
        manager_password=credentials['manager_password'],
        manager_tenant=credentials['manager_tenant'],
        ssh_user='root',
        ssh_key=configuration.ssh_key_path
    )
    cli_env.profile = cli_env.get_profile_context(container_ip)


def _get_debug_ip():
    """Return the IP on which to remotely debug code on the manager"""
    # If the debug IP was provided explicitly, it should supersede
    debug_ip = configuration.debug_ip
    if not debug_ip:
        debug_ip = install_rpm_server.get_host()
    return debug_ip


def _update_container(container_id, container_ip):
    logger.info('Updating files on the container')

    with tempfile.NamedTemporaryFile() as f:
        json.dump({
            'ip': container_ip,
            'is_debug_on': bool(os.environ.get('DEBUG_MODE')),
            'host': _get_debug_ip(),
            'services': constants.ALL_IP_SERVICES
        }, f)
        f.flush()
        cp(source=f.name,
           target=':{}'.format(constants.DATA_JSON_TARGET_PATH),
           container_id=container_id)


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
    version = version or _get_docker_version()
    install_docker_command = 'yum install -y -q docker-engine-{}'.format(
        version)
    docker('exec', container_id, *install_docker_command.split(' '))


def _get_docker_version():
    try:
        version = quiet_docker.version('-f', '{{.Client.Version}}').strip()
    except sh.ErrorReturnCode as e:
        version = e.stdout.strip()

    # Replacing the -ce in the version with .ce, as the versions in
    # https://yum.dockerproject.org/repo/main/centos/7/Packages/
    # adhere to this notation
    if version.endswith('-ce'):
        version = version.replace('-ce', '.ce')
    return version


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
    logger.warning('`docl ssh` is deprecated, use `docl shell` instead')
    if not container_id:
        container_ip = work.last_container_ip
    else:
        container_ip = _extract_container_ip(container_id)
    _ssh(container_ip, configuration.ssh_key_path)


@command
def shell(container_id=None):
    container_id = container_id or work.last_container_id
    docker('exec', '-it', container_id, '/bin/bash')


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
def serve_install_rpm(invalidate_cache=False, no_progress=False):
    with install_rpm_server.with_server(invalidate_cache=invalidate_cache,
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
        # Might not be declared yet (e.g. cfy_manager)
        if not dst:
            continue
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
    _retry(quiet_docker, 'exec', container_id, 'systemctl', 'start', 'dbus')
    return container_id, container_ip


def _run_container(docker_tag, volume=None, label=None, name=None,
                   details_path=None):
    label = label or []
    volume = volume or []
    expose = configuration.expose
    publish = configuration.publish
    hostname = configuration.container_hostname
    docker_args = ['--privileged', '--detach']
    if name:
        docker_args.append('--name={}'.format(name))
    container_id = quiet_docker.run(
        *docker_args +
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
    # due to a bug in docker 17.06, the file keeps ownership and is not
    # chowned to the main container user automatically
    quiet_docker('exec', container_id, 'chown', 'root:root',
                 '/root/.ssh/authorized_keys')


def _write_config(container_ip, config_path):
    path(config_path).write_text(yaml.safe_dump({
        'manager': {
            'public_ip': container_ip,
            'private_ip': container_ip,
            'set_manager_ip_on_boot': True,
            'security': {
                'admin_password': 'admin'
            }
        },
        'usage_collector': {
            'collect_cloudify_uptime': {
                'active': False
            },
            'collect_cloudify_usage': {
                'active': False
            }
        }
    }))


def _write_container_details(container_id, container_ip, details_path):
    path(details_path).write_text(yaml.safe_dump({
        'id': container_id,
        'ip': container_ip,
    }))
