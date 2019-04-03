#!/bin/sh

source /etc/platform/openrc

NOWRAP="--nowrap"

COMPUTES=`system host-list $NOWRAP | grep compute- | cut -d '|' -f 3`

for compute in $COMPUTES; do
  echo "Configuring nova local for: ${compute}"
  set -ex
  ROOT_DISK=$(system host-show ${compute} | grep rootfs | awk '{print $4}')
  ROOT_DISK_UUID=$(system host-disk-list ${compute} --nowrap | awk /${ROOT_DISK}/'{print $2}')
  PARTITION_SIZE=10
  NOVA_PARTITION=$(system host-disk-partition-add -t lvm_phys_vol ${compute} ${ROOT_DISK_UUID} ${PARTITION_SIZE})
  NOVA_PARTITION_UUID=$(echo ${NOVA_PARTITION} | grep -ow "| uuid | [a-z0-9\-]* |" | awk '{print $4}')
  system host-lvg-add ${compute} nova-local
  system host-pv-add ${compute} nova-local ${NOVA_PARTITION_UUID}
  system host-lvg-modify -b image ${compute} nova-local
  set +ex
done

