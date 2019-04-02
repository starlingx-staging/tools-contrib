#!/bin/sh

OPENSTACK_ROOT=$1

export OS_CLOUD=$OPENSTACK_ROOT

#Providernetworking setup (pre-Stein)
PHYSNET0='physnet0'
PHYSNET1='physnet1'
neutron providernet-create ${PHYSNET0} --type vlan
neutron providernet-create ${PHYSNET1} --type vlan

neutron providernet-range-create ${PHYSNET0} --name ${PHYSNET0}-a --range 400-499
neutron providernet-range-create ${PHYSNET0} --name ${PHYSNET0}-b --range 10-10 --shared
neutron providernet-range-create ${PHYSNET1} --name ${PHYSNET1}-a --range 500-599



