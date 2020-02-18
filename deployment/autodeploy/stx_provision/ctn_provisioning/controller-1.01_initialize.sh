#!/bin/sh

source /etc/platform/openrc

if grep "simplex" /etc/platform/platform.conf; then
  SYSMODE="simplex"
else
  if grep "All-in-one" /etc/platform/platform.conf; then
    SYSMODE="duplex"
  else
    SYSMODE="multi"
  fi
fi

OAM_IF=$1

set -ex

echo "========================================================="
COMPUTE="controller-1"
NOWRAP="--nowrap"

echo ">>> Configuring OAM Network"
system host-if-modify -n oam0 -c platform ${COMPUTE} $(system host-if-list -a $COMPUTE  $NOWRAP | grep ${OAM_IF} | awk '{ print $2; }')
system interface-network-assign ${COMPUTE} oam0 oam
echo ">>> Configuring MGMT Network"
system interface-network-assign ${COMPUTE} mgmt0 cluster-host

echo "========================================================="
if [ "$SYSMODE" == "multi" ]; then
	system host-label-assign controller-1 openstack-control-plane=enabled
else
	system host-label-assign controller-1 openstack-control-plane=enabled
	system host-label-assign controller-1 openstack-compute-node=enabled
	system host-label-assign controller-1 openvswitch=enabled
	system host-label-assign controller-1 sriov=enabled
fi


