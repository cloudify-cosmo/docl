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

# flake8: noqa

import json
import os
import re
import sys

import requests.packages.urllib3

requests.packages.urllib3.disable_warnings()


def sed(path, regex, sub):
    with open(path) as sources:
        lines = sources.readlines()
    with open(path, 'w') as sources:
        for line in lines:
            sources.write(re.sub(regex, sub, line))


def fix_ip_in_files(ip):
    print ('Patching services related files with container ip address '
           '{0}'.format(ip))
    patches = (
        ('/etc/sysconfig/cloudify-mgmtworker',
         'REST_HOST=.*',
         'REST_HOST={ip}'),
        ('/etc/sysconfig/cloudify-mgmtworker',
         'FILE_SERVER_HOST=.*',
         'FILE_SERVER_HOST={ip}'),
        ('/etc/sysconfig/cloudify-mgmtworker',
         'MANAGER_FILE_SERVER_URL="http://.*:53229"',
         'MANAGER_FILE_SERVER_URL="http://{ip}:53229"'),
        ('/etc/sysconfig/cloudify-mgmtworker',
         'MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="http://.*:53229/blueprints"',
         'MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="http://{ip}:53229/blueprints"'),
        ('/etc/sysconfig/cloudify-mgmtworker',
         'MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL="http://.*:53229/deployments"',
         'MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL="http://{ip}:53229/deployments"'),
        ('/etc/sysconfig/cloudify-amqpinflux',
         'AMQP_HOST=.*',
         'AMQP_HOST={ip}'),
        ('/etc/sysconfig/cloudify-amqpinflux',
         'INFLUXDB_HOST=.*',
         'INFLUXDB_HOST={ip}'),
        ('/etc/sysconfig/cloudify-riemann',
         'RABBITMQ_HOST=.*',
         'RABBITMQ_HOST={ip}'),
        ('/etc/sysconfig/cloudify-riemann',
         'REST_HOST=.*',
         'REST_HOST={ip}'),
        ('/opt/mgmtworker/work/broker_config.json',
         '"broker_hostname": ".*"',
         '"broker_hostname": "{ip}"'),
        ('/opt/manager/cloudify-rest.conf',
         "db_address: '.*'",
         "db_address: '{ip}'"),
        ('/opt/manager/cloudify-rest.conf',
         "amqp_address: '.*:5672/'",
         "amqp_address: '{ip}:5672/'"),
        ('/opt/cloudify-ui/backend/gsPresets.json',
         '"host": ".*"',
         '"host": "{ip}"'),
        ('/etc/logstash/conf.d/logstash.conf',
         'host => ".*"',
         'host => "{ip}"')
    )
    for patch in patches:
        path, regex, sub = patch
        sed(path, regex, sub.format(ip=ip))


def restart_services(services):
    for service in services:
        print 'Restarting service: {0}'.format(service)
        os.system('systemctl restart {0}'.format(service))


def main():
    with open(sys.argv[1]) as f:
        data = json.load(f)
    ip = data['ip']
    services = data['services']
    fix_ip_in_files(ip)
    restart_services(services)
    os.system('')

if __name__ == '__main__':
    main()
