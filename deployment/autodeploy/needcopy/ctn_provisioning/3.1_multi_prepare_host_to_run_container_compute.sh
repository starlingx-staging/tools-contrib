#!/bin/sh

source /etc/platform/openrc
NODE=$1

system host-label-assign $NODE  openstack-compute-node=enabled
system host-label-assign $NODE  openvswitch=enabled
system host-label-assign $NODE  sriov=enabled


