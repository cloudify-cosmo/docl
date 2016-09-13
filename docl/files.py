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

import requests

from cloudify_cli.utils import generate_progress_handler
from cloudify_rest_client import bytes_stream_utils
from cloudify_rest_client import client

from docl import constants


def download(url, output_path, no_progress):
    response = requests.get(url, stream=True)
    streamed_response = client.StreamedResponse(response)
    progress_handler = None
    if not no_progress:
        progress_handler = generate_progress_handler(output_path)
    bytes_stream_utils.write_response_stream_to_file(
        buffer_size=constants.BUFFER_SIZE,
        streamed_response=streamed_response,
        output_file=output_path,
        progress_callback=progress_handler)
