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

INPUTS_YAML = 'inputs.yaml'
DOCKER_HOST = 'fd://'
SSH_KEY = '~/.ssh/.id_rsa'
CLEAN_IMAGE_DOCKER_TAG = 'cloudify/centos-manager:7'
INSTALLED_IMAGE_DOCKER_TAG = 'cloudify/centos-manager-installed:7'
SOURCE_ROOT = '~/dev/cloudify'
HOSTNAME = 'cfy-manager'

EXPOSE = (22, 80, 443, 5671)
PUBLISH = ()

SERVICES = (
    'cloudify-amqpinflux',
    'cloudify-mgmtworker',
    'cloudify-restservice',
)

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

PACKAGE_SERVICES = {
    'amqp_influxdb': ('cloudify-amqpinflux',),
    'cloudify': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'cloudify_agent': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'cloudify_rest_client': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'dsl_parser': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'manager_rest': ('cloudify-restservice',),
    'plugin_installer': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'script_runner': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'windows_agent_installer': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'windows_plugin_installer': ('cloudify-restservice', 'cloudify-mgmtworker'),  # noqa
    'worker_installer': ('cloudify-restservice', 'cloudify-mgmtworker'),
    'cloudify_system_workflows': ('cloudify-mgmtworker',),
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
