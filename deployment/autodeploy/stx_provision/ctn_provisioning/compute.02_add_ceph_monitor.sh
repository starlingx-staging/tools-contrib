#!/bin/sh

source /etc/platform/openrc
set -ex

system ceph-mon-add compute-0
system ceph-mon-list


