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

import logging
import sys


logger = logging.getLogger('docl')


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    fmt = '%(asctime)s [%(levelname)s] %(message)s'
    handler.setFormatter(logging.Formatter(fmt))
    handler.setLevel(logging.INFO)
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    sh_logger = logging.getLogger('sh')
    sh_logger.setLevel(logging.WARNING)
