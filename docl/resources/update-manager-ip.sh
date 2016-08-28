#! /bin/bash -e

ip=$1
services="$2"

fix()
{
    local path="$1"
    local pattern="$2"
    sed -i -e "s|${pattern}|" "${path}"
}

echo "Patching services related files with container ip address ${ip}"

fix /etc/sysconfig/cloudify-mgmtworker      "REST_HOST=.*|REST_HOST=${ip}"
fix /etc/sysconfig/cloudify-mgmtworker      "FILE_SERVER_HOST=.*|FILE_SERVER_HOST=${ip}"
fix /etc/sysconfig/cloudify-mgmtworker      "MANAGER_FILE_SERVER_URL="'"'"http://.*:53229"'"'"|MANAGER_FILE_SERVER_URL="'"'"http://${ip}:53229"'"'""
fix /etc/sysconfig/cloudify-mgmtworker      "MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="'"'"http://.*:53229/blueprints"'"'"|MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="'"'"http://${ip}:53229/blueprints"'"'""
fix /etc/sysconfig/cloudify-mgmtworker      "MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL="'"'"http://.*:53229/deployments"'"'"|MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL="'"'"http://${ip}:53229/deployments"'"'""
fix /etc/sysconfig/cloudify-amqpinflux      "AMQP_HOST=.*|AMQP_HOST=${ip}"
fix /etc/sysconfig/cloudify-amqpinflux      "INFLUXDB_HOST=.*|INFLUXDB_HOST=${ip}"
fix /etc/sysconfig/cloudify-riemann         "RABBITMQ_HOST=.*|RABBITMQ_HOST=${ip}"
fix /etc/sysconfig/cloudify-riemann         "REST_HOST=.*|REST_HOST=${ip}"
fix /opt/mgmtworker/work/broker_config.json ""'"'"broker_hostname"'"'": "'"'".*"'"'"|"'"'"broker_hostname"'"'": "'"'"${ip}"'"'""
fix /opt/manager/cloudify-rest.conf         "db_address: '.*'|db_address: '${ip}'"
fix /opt/manager/cloudify-rest.conf         "amqp_address: '.*:5672/'|amqp_address: '${ip}:5672/'"
fix /opt/cloudify-ui/backend/gsPresets.json ""'"'"host"'"'": "'"'".*"'"'"|"'"'"host"'"'": "'"'"${ip}"'"'""

for service in ${services};
do
    echo "Restarting service: ${service}"
    systemctl restart "${service}"
done

echo "Updating provider context with broker_ip: ${ip}"
/opt/mgmtworker/env/bin/python /root/update_provider_context.py ${ip}
