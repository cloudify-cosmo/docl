#!/usr/bin/env python
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from __future__ import print_function

import argparse
import os
from functools import partial
from subprocess import check_call, check_output, CalledProcessError
from tempfile import mkdtemp
from time import sleep

import yaml


EXPOSE = [22, 80, 443, 5671]

# Add forwarding specifications here if you want to open ports on the host
# (see man docker-run)
PUBLISH = []


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Deploy a simple manager blueprint "
                    "into a local docker container",
        )
    parser.add_argument('path', nargs='?', default='simple-manager-blueprint.yaml')

    parser.add_argument(
        '--ssh-key',
        default=os.path.expanduser('~/.ssh/id_rsa'),
        )
    parser.add_argument(
        '--docker-tag',
        default='cloudify/centos-manager:7',
        )
    parser.add_argument(
        '--docker-context',
        default=os.path.join(os.path.dirname(__file__), 'dockerify'),
        )

    parser.add_argument(
        '-i', '--inputs', nargs='*',
        help="Extra inputs arguments that will be passed through to cfy",
        )

    args = parser.parse_args(args)

    files = {
        args.path: "you must specify a path to a manager blueprint",
        args.ssh_key: "you need to create a key (see man ssh-keygen) first",
        }

    for path, message in files.items():
        if not os.path.isfile(path):
            raise ValueError(message)

    id, ip = create_container(args.docker_context, args.docker_tag)
    print("Created container: " + id)

    ssh_swap(id, ip, args.ssh_key)

    install(args.path, id, ip, args.ssh_key, args.inputs)


def create_container(context, tag):
    # Ensure the image is up to date
    docker.build(['-t', tag, context])

    # Create the container
    container_id = docker.run(
            ['--privileged', '--detach'] +
            ['--expose={}'.format(p) for p in EXPOSE] +
            ['--publish={}'.format(p) for p in PUBLISH] +
            [tag],
            ).strip()

    container_ip = docker.inspect([
        '--format={{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id,
        ]).strip()

    # Launch DBUS because restservice seems to try to access it weirdly
    docker.exc([container_id, 'systemctl', 'start', 'dbus'])

    return container_id, container_ip


def _wait_for_file(container_id, file):
    attempt = 0
    while attempt < 100:
        try:
            return getattr(docker, 'exec')([container_id, 'cat', file])
        except CalledProcessError as e:
            if e.returncode != 1:
                # Some error other than not found. Bad!
                raise
            attempt += 1
            sleep(0.1)
    raise


def ssh_swap(id, ip, keyname):
    """
    Inject the user's SSH key into root's authorized_keys
    Also clears out references to the container's IP in the local known_hosts
    """
    # Remove old keys referring to the container's IP
    check_call(['ssh-keygen', '-R', ip])

    # new container shouldn't have an authorized_keys file yet
    try:
        docker.exc([id, 'mkdir', '-m700', '/root/.ssh'])
    except CalledProcessError as e:
        if e.returncode != 1:
            raise
        # Hopefully that means it's already there
    docker.cp([
            keyname + '.pub',
            '{id}:/root/.ssh/authorized_keys'.format(id=id)
            ])


def install(path, id, ip, key_filename, inputs):

    inputs = inputs or []
    tmpdir = mkdtemp('dockerify')
    # Write the inputs file
    with open(os.path.join(tmpdir, 'docker-bootstrap-inputs.yaml'), 'w') as f:
        f.write(yaml.safe_dump({
                    'public_ip': ip,
                    'private_ip': ip,
                    'ssh_user': 'root',
                    'ssh_key_filename': key_filename,
                    },
                allow_unicode=True))

    # Clean the environment
    check_output(['cfy', 'init', '-r'])

    # Bootstrap the manager
    check_call([
            'cfy', 'bootstrap', '--install-plugins',
            '-p', path,
            '-i', os.path.join(tmpdir, 'docker-bootstrap-inputs.yaml')] +
            ['-i {}'.format(i) for i in inputs]
            )


class docker(object):
    """Helper for running docker commands"""
    def _action(self, action, options, *args, **kwargs):
        if action == 'exc':
            # Because `exec` is a keyword in Python2
            action = 'exec'
        return check_output(
                ['docker', action] + options,
                *args, **kwargs)

    def __getattr__(self, attr):
        """return a function that will run the named command"""
        return partial(self._action, attr)


docker = docker()


if __name__ == "__main__":
    main()
