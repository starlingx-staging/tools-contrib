#!/bin/sh

source /etc/platform/openrc
NODE=$1

set -ex

system host-label-assign $NODE  openstack-compute-node=enabled
system host-label-assign $NODE  openvswitch=enabled
system host-label-assign $NODE  sriov=enabled


