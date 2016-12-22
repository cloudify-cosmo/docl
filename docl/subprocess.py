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

from __future__ import absolute_import

import os
import subprocess
import functools
import sys

import proxy_tools
import sh

from docl.configuration import configuration


def bake(cmd):
    return cmd.bake(_err_to_out=True,
                    _out=lambda l: sys.stdout.write(l),
                    _tee=True)


def docker_proxy(quiet=False):
    result = docker_command.bake('-H', configuration.docker_host)
    if not quiet:
        result = bake(result)
    return result


docker = proxy_tools.Proxy(docker_proxy)
quiet_docker = proxy_tools.Proxy(functools.partial(docker_proxy, quiet=True))

try:
    ssh_keygen = sh.Command('ssh-keygen')
    ssh_keyscan = sh.Command('ssh-keyscan')
    gzip = sh.gzip
    docker_command = sh.docker
except sh.CommandNotFound:
    # required programs not found on the PATH - maybe PATH was not set;
    # try the default locations
    ssh_keygen = sh.Command('/usr/bin/ssh-keygen')
    ssh_keyscan = sh.Command('/usr/bin/ssh-keyscan')
    gzip = sh.Command('/bin/gzip')
    docker_command = sh.Command('/usr/bin/docker')

gzip = gzip.bake(_tty_out=False)

try:
    cfy = bake(sh.cfy)
    serve = sh.serve
except sh.CommandNotFound:
    # use cfy and serve from the same virtualenv
    cfy = bake(sh.Command(
        os.path.join(os.path.dirname(sys.executable), 'cfy')))
    serve = sh.Command(os.path.join(os.path.dirname(sys.executable), 'serve'))


def ssh(ip, keypath):
    subprocess.call(['ssh', '-i', keypath, 'root@{}'.format(ip)])
