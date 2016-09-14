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
import subprocess


def _run(command):
    subprocess.Popen(command.split(' ')).wait()


def _write(path, line):
    with open(path, 'r') as f:
        s = f.read()
    if line not in s:
        with open(path, 'a') as f:
            f.write('\n{}\n'.format(line))


def _write_to_files(data_json_path):
    _write('/var/lib/pgsql/9.5/data/pg_hba.conf', 'host all all 0.0.0.0/0 md5')
    _write('/var/lib/pgsql/9.5/data/postgresql.conf', "listen_addresses = '*'")
    _write('/etc/sysconfig/cloudify-restservice',
           "DEBUG_CONFIG='{}'".format(data_json_path))


def _remove_old_json(data_json_path):
    if os.path.exists(data_json_path):
        os.remove(data_json_path)


def _install_pycharm(pydevd_egg_url):
    egg_path = '/root/pycharm-debug.egg'
    if not os.path.isfile(egg_path):
        _run('curl -o {} {}'.format(egg_path, pydevd_egg_url))
    _run('/opt/manager/env/bin/easy_install {}'.format(egg_path))
    _run('/opt/mgmtworker/env/bin/easy_install {}'.format(egg_path))


def main():
    data_json_path = sys.argv[1]
    pydevd_egg_url = sys.argv[2]
    _write_to_files(data_json_path)
    _remove_old_json(data_json_path)
    _install_pycharm(pydevd_egg_url)


if __name__ == '__main__':
    main()
