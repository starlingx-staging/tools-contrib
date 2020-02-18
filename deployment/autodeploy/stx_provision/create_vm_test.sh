#!/bin/sh

set -x

export OS_CLOUD=openstack_helm

openstack flavor create --public m1.tinny --id 1 --ram 512 --vcpus 1 --disk 4
openstack image show cirros || openstack image create cirros --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2

NETWORK=`openstack network list | grep public | awk -F "|" '{print $3}' | tr -d '[ ]'`

for i in {0..1}; do
    openstack server show vm$i || openstack server create --flavor m1.tinny --image cirros --nic net-id=$NETWORK vm$i
done

openstack server list
