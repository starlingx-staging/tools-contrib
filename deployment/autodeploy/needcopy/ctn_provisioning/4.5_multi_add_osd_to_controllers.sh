#!/bin/sh

source /etc/platform/openrc

HOST=$1
DISKS=$(system host-disk-list ${HOST})
TIERS=$(system storage-tier-list ceph_cluster)
OSDs="/dev/sdb"
for OSD in $OSDs; do
    system host-stor-add ${HOST} $(echo "$DISKS" | grep /dev/sdb | awk '{print $2}') --tier-uuid $(echo "$TIERS" | grep storage | awk '{print $2}')
done
