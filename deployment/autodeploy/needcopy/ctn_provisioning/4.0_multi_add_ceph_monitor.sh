#!/bin/sh

source /etc/platform/openrc

system ceph-mon-add compute-0
system ceph-mon-list


