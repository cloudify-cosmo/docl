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
    result = sh.docker.bake('-H', configuration.docker_host)
    if not quiet:
        result = bake(result)
    return result


docker = proxy_tools.Proxy(docker_proxy)
quiet_docker = proxy_tools.Proxy(functools.partial(docker_proxy, quiet=True))
ssh_keygen = sh.Command('ssh-keygen')
ssh_keyscan = sh.Command('ssh-keyscan')
cfy = bake(sh.cfy)
serve = sh.serve
gzip = sh.gzip.bake(_tty_out=False)


def ssh(ip, keypath):
    subprocess.call(['ssh', '-i', keypath, 'root@{}'.format(ip)])
