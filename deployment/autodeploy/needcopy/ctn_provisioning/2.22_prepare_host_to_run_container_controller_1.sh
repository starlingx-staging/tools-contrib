#!/bin/sh

source /etc/platform/openrc

system host-label-assign controller-1 openstack-control-plane=enabled
system host-label-assign controller-1 openstack-compute-node=enabled
system host-label-assign controller-1 openvswitch=enabled
system host-label-assign controller-1 sriov=enabled

