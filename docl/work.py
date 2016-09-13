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

from docl.configuration import configuration


class Work(object):

    def init(self):
        if not self.dir.exists():
            self.dir.makedirs()

    @property
    def dir(self):
        return configuration.workdir

    @property
    def last_container_id(self):
        return (self.dir / 'last_container_id').text()

    @property
    def last_container_ip(self):
        return (self.dir / 'last_container_ip').text()

    @property
    def cached_resources_tar_path(self):
        return self.dir / 'resources.tar.gz'

    @property
    def pulled_image_path(self):
        return self.dir / 'manager-image.tar.gz'

    @property
    def last_pulled_image_commit_sha1(self):
        file_path = self.dir / 'pulled_image.sha1'
        if not file_path.exists():
            return None
        return file_path.text().strip()

    @last_pulled_image_commit_sha1.setter
    def last_pulled_image_commit_sha1(self, value):
        file_path = self.dir / 'pulled_image.sha1'
        file_path.write_text(value)

    def save_last_container_id_and_ip(self, container_id, container_ip):
        (self.dir / 'last_container_id').write_text(container_id)
        (self.dir / 'last_container_ip').write_text(container_ip)
work = Work()
