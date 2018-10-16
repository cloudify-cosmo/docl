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

import base64
import json
import os
import sys
import subprocess
from glob import glob


def _run(command):
    subprocess.check_call(command.split(' '))


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


def _prepare_agent_template(agent_template_dir, agent_package_path):
    if not os.path.exists(agent_template_dir):
        os.makedirs(agent_template_dir)
    _run('tar xf {} --strip=1 -C {}'.format(agent_package_path,
                                            agent_template_dir))


def _install_pydevd():
    for venv in ['manager', 'mgmtworker']:
        pip = os.path.join('/opt', venv, 'env', 'bin', 'pip')
        _run('{0} install pydevd'.format(str(pip)))


def _print_cfy_manager_location():
    # This should get us the location of the cfy_manager code
    location = glob('/root/.pex/install/cloudify_manager_install*/'
                    'cloudify_manager_install*.whl/cfy_manager')[0]
    # The output will be parsed by docl
    print location


def main():
    params = json.loads(base64.b64decode(sys.argv[1]))
    data_json_path = params['data_json_path']
    skip_agent_prepare = params['skip_agent_prepare']
    agent_template_dir = params['agent_template_dir']
    agent_package_path = params['agent_package_path']
    if not skip_agent_prepare:
        _prepare_agent_template(agent_template_dir, agent_package_path)
    _write_to_files(data_json_path)
    _remove_old_json(data_json_path)
    _install_pydevd()
    _print_cfy_manager_location()


if __name__ == '__main__':
    main()
