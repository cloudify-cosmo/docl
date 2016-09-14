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

import os

import argh
import yaml
from path import path

from docl import constants


class Configuration(object):

    def save(self,
             docker_host,
             ssh_key_path,
             simple_manager_blueprint_path,
             clean_image_docker_tag,
             manager_image_docker_tag,
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
            'manager_image_docker_tag': manager_image_docker_tag,
            'source_root': source_root,
            'workdir': str(workdir),
            'services': constants.SERVICES,
            'expose': constants.EXPOSE,
            'publish': constants.PUBLISH,
            'container_hostname': constants.HOSTNAME,
            'package_dir': constants.PACKAGE_DIR,
            'package_services': constants.PACKAGE_SERVICES,
            'env_packages': constants.ENV_PACKAGES,
            'resources': constants.RESOURCES,
            'agent_package_path': constants.AGENT_PACKAGE_PATH,
            'manager_image_url': constants.MANAGER_IMAGE_URL,
            'manager_image_commit_sha_url':
                constants.MANAGER_IMAGE_COMMIT_SHA_URL,
            'pydevd_egg_url': constants.PYDEVD_EGG_URL,
        }, default_flow_style=False))

    @property
    def conf_dir(self):
        return path(os.environ.get(constants.DOCL_HOME_ENV_VAR,
                                   '~/.docl')).expanduser()

    @property
    def conf_path(self):
        return self.conf_dir / 'config.yaml'

    @property
    def conf(self):
        if not self.conf_path.exists():
            raise argh.CommandError('Not initialized. Run "docl init"')
        return yaml.safe_load(self.conf_path.text())

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
    def manager_image_docker_tag(self):
        return self.conf.get('manager_image_docker_tag')

    @property
    def source_root(self):
        return path(self.conf.get('source_root')).expanduser().abspath()

    @property
    def services(self):
        return self.conf.get('services')

    @property
    def expose(self):
        return self.conf.get('expose')

    @property
    def publish(self):
        return self.conf.get('publish')

    @property
    def container_hostname(self):
        return self.conf.get('container_hostname')

    @property
    def package_dir(self):
        return self.conf.get('package_dir')

    @property
    def package_services(self):
        return self.conf.get('package_services')

    @property
    def env_packages(self):
        return self.conf.get('env_packages')

    @property
    def resources(self):
        return self.conf.get('resources')

    @property
    def agent_package_path(self):
        return self.conf.get('agent_package_path')

    @property
    def workdir(self):
        return path(self.conf['workdir'])

    @property
    def manager_image_url(self):
        return self.conf.get('manager_image_url')

    @property
    def manager_image_commit_sha_url(self):
        return self.conf.get('manager_image_commit_sha_url')

    @property
    def pydevd_egg_url(self):
        return self.conf.get('pydevd_egg_url')

configuration = Configuration()
