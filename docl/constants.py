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
CLEAN_IMAGE_DOCKER_TAG = 'cloudify/centos:7'
MANAGER_IMAGE_DOCKER_TAG = 'cloudify/centos-manager:7'
SOURCE_ROOT = '~/dev/cloudify'
HOSTNAME = 'cfy-manager'
AGENT_PACKAGE_PATH = '/opt/manager/resources/packages/agents/centos-core-agent.tar.gz'  # noqa
AGENT_TEMPLATE_DIR = '/opt/agent-template'
AGENT_STUB_SERVICE = 'agent-service'
DOCL_HOME_ENV_VAR = 'DOCL_HOME'
PREPARE_SAVE_IMAGE_TARGET_PATH = '/root/prepare_save_image.py'
PY_SCRIPT_TARGET_PATH = '/root/update_running_system.py'
DATA_JSON_TARGET_PATH = '/root/data.json'
CREDENTIALS_TARGET_PATH = '/root/test_credentials.json'
BUFFER_SIZE = 1024 * 64
MANAGER_IMAGE_URL = 'http://cloudify-tests-files.s3.amazonaws.com/docl-images/docl-manager.tar.gz'  # noqa
MANAGER_IMAGE_COMMIT_SHA_URL = 'http://cloudify-tests-files.s3.amazonaws.com/docl-images/docl-manager.sha1'  # noqa
PYDEVD_EGG_URL = 'http://cloudify-tests-files.s3.amazonaws.com/components/pycharm-debug.egg'  # noqa


EXPOSE = (22, 80, 443, 5671, 5672, 15672, 9200, 5432, 8086, 9999)
PUBLISH = ()

SERVICES = (
    'cloudify-amqpinflux',
    'cloudify-mgmtworker',
    'cloudify-restservice',
)

ALL_IP_SERVICES = SERVICES + (
    'logstash',
    'cloudify-webui',
    'cloudify-riemann',
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
    'cloudify_system_workflows': 'cloudify-manager/workflows',
    'flask_securest': 'flask-securest',
    'riemann_controller': 'cloudify-manager/plugins/riemann-controller',
    'diamond_agent': 'cloudify-diamond-plugin',
    'cloudify_handler': 'cloudify-diamond-plugin'
}

PACKAGE_SERVICES = {
    'amqp_influxdb': ('cloudify-amqpinflux',),
    'cloudify': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'cloudify_agent': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'cloudify_rest_client': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'dsl_parser': ('cloudify-restservice',),
    'manager_rest': ('cloudify-restservice',),
    'plugin_installer': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'script_runner': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'windows_agent_installer': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'windows_plugin_installer': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'worker_installer': (
        'cloudify-restservice',
        'cloudify-mgmtworker',
        AGENT_STUB_SERVICE
    ),
    'cloudify_system_workflows': ('cloudify-mgmtworker',),
    'riemann_controller': ('cloudify-mgmtworker',),
    'flask_securest': ('cloudify-restservice',),
    'diamond_agent': (AGENT_STUB_SERVICE,),
    'cloudify_handler': (AGENT_STUB_SERVICE,),
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
        'flask_securest',
    ),
    'mgmtworker': (
        'cloudify',
        'cloudify_agent',
        'cloudify_system_workflows',
        'cloudify_rest_client',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
        'riemann_controller',
    ),
    'agent-template': (
        'cloudify',
        'cloudify_agent',
        'cloudify_rest_client',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
        'diamond_agent',
        'cloudify_handler',
    )
}

RESOURCES = (
    {
        'src': 'cloudify-manager/resources/rest-service/cloudify',
        'dst': '/opt/manager/resources/cloudify'
    },
    {
        'src': 'cloudify-manager/plugins/riemann-controller/riemann_controller/resources/manager.config',  # noqa
        'dst': '/etc/riemann/conf.d/manager.config'
    },
)
