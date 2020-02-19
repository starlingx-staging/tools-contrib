#!/bin/sh

source /etc/platform/openrc

set -ex
HOST=$1

system host-disk-list ${HOST}
system storage-tier-list ceph_cluster

ROOTFS=`system host-show ${HOST} | grep rootfs | awk '{print $4}'`
TIER_UID=`system storage-tier-list ceph_cluster | grep storage | awk '{print $2}'`
ALL_HDD=`system host-disk-list ${HOST} --nowrap | grep "/dev" | grep -v ${ROOTFS} | awk '{print $2;}'`
for hdd in $ALL_HDD; do
    if [ "$HOST" == "controller-0" ]; then
        system host-stor-add ${HOST} ${hdd}
    else
        system host-stor-add ${HOST} ${hdd} --tier-uuid ${TIER_UID}
    fi
    break
done

system host-stor-list ${HOST}

