#!/bin/sh

source /etc/platform/openrc
set -ex

system host-list
ceph -s
ceph osd tree
system service-list | grep ceph
system service-list | grep plugin

echo "finished"
