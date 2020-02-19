#!/bin/sh
set -ex

OPENSTACK_ROOT=$1
PASSWORD=$2

mkdir -p /etc/openstack
tee /etc/openstack/clouds.yaml << EOF
clouds:
  $OPENSTACK_ROOT:
    region_name: RegionOne
    identity_api_version: 3
    auth:
      username: 'admin'
      password: '$PASSWORD'
      project_name: 'admin'
      project_domain_name: 'default'
      user_domain_name: 'default'
      auth_url: 'http://keystone.openstack.svc.cluster.local/v3'
EOF

export OS_CLOUD=$OPENSTACK_ROOT
openstack endpoint list


