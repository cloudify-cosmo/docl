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

import requests
from contextlib import contextmanager
from requests.exceptions import ConnectionError

import sh
import os
import yaml
from time import sleep

from docl import files
from docl.configuration import configuration
from docl.work import work
from docl.logs import logger
from docl.subprocess import serve


@contextmanager
def with_server(invalidate_cache, no_progress=False):
    process, local_rpm_url = start(invalidate_cache=invalidate_cache,
                                   no_progress=no_progress)
    try:
        yield local_rpm_url
    finally:
        process.kill()
        try:
            process.wait()
        except sh.SignalException:
            pass


def start(invalidate_cache=False, no_progress=False):
    if invalidate_cache or not work.cached_install_rpm_path.exists():
        _download_install_rpm(no_progress=no_progress)
    return _serve()


def get_host():
    host = configuration.docker_host
    if not host:
        return
    if '://' in host:
        host = host.split('://')[1]
    if ':' in host:
        host = host.split(':')[0]
    return host


def _serve():
    host = get_host()
    port = 9797
    local_rpm_url = 'http://{}:{}/{}'.format(
        host, port, work.cached_install_rpm_path.basename())
    process = serve(work.dir, host=host, port=port, _bg=True)
    logger.info('Install RPM available at {}'.format(local_rpm_url))
    _wait_for_file_server(local_rpm_url)
    return process, local_rpm_url


def _wait_for_file_server(url, max_retries=300):
    while max_retries:
        sleep(0.1)
        max_retries -= 1
        try:
            result = requests.head(url)
            if result.status_code == 200:
                return
        except ConnectionError:
            pass
    raise StandardError('Could not download requested URL: {0}'.format(url))


def _download_install_rpm(no_progress):
    rpm_local_path = work.cached_install_rpm_path
    if rpm_local_path.exists():
        rpm_local_path.unlink()
    rpm_url = get_rpm_url()
    logger.info('Downloading install RPM from {}. This might take a '
                'while'.format(rpm_url))
    files.download(url=rpm_url,
                   output_path=rpm_local_path,
                   no_progress=no_progress)


def get_rpm_url():
    rpm_path_yaml = os.path.join(
        configuration.source_root,
        'cloudify-premium',
        'packages-urls',
        'manager-install-rpm.yaml'
    )
    with open(rpm_path_yaml, 'r') as f:
        return yaml.load(f)
