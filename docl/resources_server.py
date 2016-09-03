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

from contextlib import contextmanager

import requests
import sh
import yaml

from cloudify_cli.utils import generate_progress_handler
from cloudify_rest_client import bytes_stream_utils
from cloudify_rest_client import client

from docl.configuration import configuration
from docl.work import work
from docl.logs import logger
from docl.subprocess import serve


@contextmanager
def with_server(invalidate_cache, no_progress=False):
    process, local_resources_url = start(invalidate_cache=invalidate_cache,
                                         no_progress=no_progress)
    try:
        yield local_resources_url
    finally:
        process.kill()
        try:
            process.wait()
        except sh.SignalException:
            pass


def start(invalidate_cache=False, no_progress=False):
    if invalidate_cache or not work.cached_resources_tar_path.exists():
        _download_resources_tar(no_progress=no_progress)
    return _serve()


def _serve():
    host = configuration.docker_host
    if '://' in host:
        host = host.split('://')[1]
    if ':' in host:
        host = host.split(':')[0]
    port = 9797
    local_resources_url = 'http://{}:{}/{}'.format(
        host, port, work.cached_resources_tar_path.basename())
    process = serve(work.dir, host=host, port=port, _bg=True)
    logger.info('Resources tar available at {}'.format(local_resources_url))
    return process, local_resources_url


def _download_resources_tar(no_progress):
    resources_local_path = work.cached_resources_tar_path
    if resources_local_path.exists():
        resources_local_path.unlink()
    resources_url = _get_resources_url()
    logger.info('Downloading resources tar from {}. This might take a '
                'while'.format(resources_url))
    response = requests.get(resources_url, stream=True)
    streamed_response = client.StreamedResponse(response)
    progress_handler = None
    if not no_progress:
        progress_handler = generate_progress_handler(resources_local_path)
    bytes_stream_utils.write_response_stream_to_file(
        streamed_response=streamed_response,
        output_file=resources_local_path,
        progress_callback=progress_handler)


def _get_resources_url():
    manager_blueprint_path = configuration.simple_manager_blueprint_path
    manager_inputs_path = (manager_blueprint_path.dirname() / 'inputs' /
                           'manager-inputs.yaml')
    manager_inputs = yaml.safe_load(manager_inputs_path.text())
    return manager_inputs[
        'inputs']['manager_resources_package']['default']
