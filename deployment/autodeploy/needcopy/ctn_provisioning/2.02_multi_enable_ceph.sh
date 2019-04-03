#!/bin/sh
source /etc/platform/openrc
system storage-backend-add ceph --confirmed

while [ $(system storage-backend-list | awk '/ceph-store/{print $8}') != 'configured' ]; do
	echo 'Waiting for ceph.';
	sleep 5;
done
system storage-backend-list
