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
############

import argh
import yaml
from path import path


class Configuration(object):

    def save(self,
             docker_host,
             ssh_key_path,
             simple_manager_blueprint_path,
             clean_image_docker_tag,
             installed_image_docker_tag,
             source_root,
             workdir,
             reset):
        if not self.conf_dir.exists():
            self.conf_dir.mkdir()
        conf = self.conf_dir / 'config.yaml'
        if conf.exists() and not reset:
            raise argh.CommandError('Already initialized. '
                                    'Run "docl init --reset"')
        workdir = workdir or self.conf_dir / 'work'
        workdir = path(workdir).expanduser().abspath()
        conf.write_text(yaml.safe_dump({
            'simple_manager_blueprint_path': str(simple_manager_blueprint_path),  # noqa
            'ssh_key_path': str(ssh_key_path),
            'docker_host': docker_host,
            'clean_image_docker_tag': clean_image_docker_tag,
            'installed_image_docker_tag': installed_image_docker_tag,
            'source_root': source_root,
            'workdir': str(workdir)
        }, default_flow_style=False))

    @property
    def conf_dir(self):
        return path('~/.docl').expanduser()

    @property
    def conf(self):
        conf = self.conf_dir / 'config.yaml'
        if not conf.exists():
            raise argh.CommandError('Not initialized. Run "docl init"')
        return yaml.safe_load(conf.text())

    @property
    def docker_host(self):
        return self.conf.get('docker_host')

    @property
    def ssh_key_path(self):
        return path(self.conf.get('ssh_key_path'))

    @property
    def simple_manager_blueprint_path(self):
        return path(self.conf.get('simple_manager_blueprint_path'))

    @property
    def clean_image_docker_tag(self):
        return self.conf.get('clean_image_docker_tag')

    @property
    def installed_image_docker_tag(self):
        return self.conf.get('installed_image_docker_tag')

    @property
    def source_root(self):
        return path(self.conf.get('source_root')).expanduser().abspath()

    @property
    def workdir(self):
        return path(self.conf['workdir'])
configuration = Configuration()
