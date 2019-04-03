#!/bin/sh

source /etc/platform/openrc

echo ">>> Get disk & tier info"
HOST="controller-1"
DISKS=$(system host-disk-list ${HOST})
TIERS=$(system storage-tier-list ceph_cluster)
echo "Disks:"
echo "$DISKS"
echo "Tiers:"
echo "$TIERS"

echo ">>> Add OSDs to primary tier"
system host-stor-add ${HOST} $(echo "$DISKS" | grep /dev/sdb | awk '{print $2}') --tier-uuid $(echo "$TIERS" | grep storage | awk '{print $2}')

echo ">>> system host-stor-list ${HOST}"
system host-stor-list ${HOST}
echo ">>> ceph osd tree"
ceph osd tree

