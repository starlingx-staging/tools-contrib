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
MGMT_IF=$2

set -ex

echo "========================================================="

if [ "$SYSMODE" != "simplex" ]; then
	system host-if-modify controller-0 lo -c none
	IFNET_UUIDS=$(system interface-network-list controller-0 | awk '{if ($6 =="lo") print $4;}')
	for UUID in $IFNET_UUIDS; do
	    system interface-network-remove ${UUID}
	done
fi

system host-if-modify controller-0 $OAM_IF -c platform
system interface-network-assign controller-0 $OAM_IF oam

if [ "$SYSMODE" != "simplex" ]; then
	system host-if-modify controller-0 $MGMT_IF -c platform
	system interface-network-assign controller-0 $MGMT_IF mgmt
	system interface-network-assign controller-0 $MGMT_IF cluster-host
fi

echo "========================================================="
if [ "$SYSMODE" == "multi" ]; then
	system host-label-assign controller-0 openstack-control-plane=enabled
else
	system host-label-assign controller-0 openstack-control-plane=enabled
	system host-label-assign controller-0 openstack-compute-node=enabled
	system host-label-assign controller-0 openvswitch=enabled
	system host-label-assign controller-0 sriov=enabled
fi

