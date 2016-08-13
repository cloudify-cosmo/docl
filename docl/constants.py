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

EXPOSE = (22, 80, 443, 5671)
PUBLISH = ()

SERVICES = ('amqpinflux', 'mgmtworker', 'restservice')

PACKAGE_DIR = {
    'amqp_influxdb': 'cloudify-amqp-influxdb',
    'cloudify': 'cloudify-plugins-common',
    'cloudify_agent': 'cloudify-agent',
    'cloudify_rest_client': 'cloudify-rest-client',
    'dsl_parser': 'cloudify-dsl-parser',
    'manager_rest': 'cloudify-manager/rest-service',
    'plugin_installer': 'cloudify-agent',
    'script_runner': 'cloudify-script-plugin',
    'windows_agent_installer': 'cloudify-agent',
    'windows_plugin_installer': 'cloudify-agent',
    'worker_installer': 'cloudify-agent',
    'cloudify_system_workflows': 'cloudify-manager/workflows'
}

PACKAGE_DIR_SERVICES = {
    'amqp_influxdb': {'amqpinflux'},
    'cloudify': {'restservice', 'mgmtworker'},
    'cloudify_agent': {'restservice', 'mgmtworker'},
    'cloudify_rest_client': {'restservice', 'mgmtworker'},
    'dsl_parser': {'restservice', 'mgmtworker'},
    'manager_rest': {'restservice'},
    'plugin_installer': {'restservice', 'mgmtworker'},
    'script_runner': {'restservice', 'mgmtworker'},
    'windows_agent_installer': {'restservice', 'mgmtworker'},
    'windows_plugin_installer': {'restservice', 'mgmtworker'},
    'worker_installer': {'restservice', 'mgmtworker'},
    'cloudify_system_workflows': {'mgmtworker'}
}

ENV_PACKAGES = {
    'amqpinflux': (
        'amqp_influxdb',
    ),
    'manager': (
        'cloudify',
        'cloudify_agent',
        'cloudify_rest_client',
        'dsl_parser',
        'manager_rest',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
    ),
    'mgmtworker': (
        'cloudify',
        'cloudify_agent',
        'cloudify_system_workflows',
        'cloudify_rest_client',
        'dsl_parser',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
    )
}
