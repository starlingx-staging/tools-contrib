#!/bin/sh

source /etc/platform/openrc
export COMPUTE=controller-1

echo ">>> Getting root disk info"
ROOT_DISK=$(system host-show ${COMPUTE} | grep rootfs | awk '{print $4}')
ROOT_DISK_UUID=$(system host-disk-list ${COMPUTE} --nowrap | grep ${ROOT_DISK} | awk '{print $2}')
echo "Root disk: $ROOT_DISK, UUID: $ROOT_DISK_UUID"

echo ">>>> Configuring nova-local"
NOVA_SIZE=34
NOVA_PARTITION=$(system host-disk-partition-add -t lvm_phys_vol ${COMPUTE} ${ROOT_DISK_UUID} ${NOVA_SIZE})
NOVA_PARTITION_UUID=$(echo ${NOVA_PARTITION} | grep -ow "| uuid | [a-z0-9\-]* |" | awk '{print $4}')
system host-lvg-add ${COMPUTE} nova-local
system host-pv-add ${COMPUTE} nova-local ${NOVA_PARTITION_UUID}

echo ">>>> Extending cgts-vg"
PARTITION_SIZE=6
CGTS_PARTITION=$(system host-disk-partition-add -t lvm_phys_vol ${COMPUTE} ${ROOT_DISK_UUID} ${PARTITION_SIZE})
CGTS_PARTITION_UUID=$(echo ${CGTS_PARTITION} | grep -ow "| uuid | [a-z0-9\-]* |" | awk '{print $4}')
system host-pv-add ${COMPUTE} cgts-vg ${CGTS_PARTITION_UUID}


