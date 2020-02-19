#!/bin/sh


source /etc/platform/openrc
set -ex
COMPUTE=$1

echo ">>> Getting root disk info"
ROOT_DISK=$(system host-show ${COMPUTE} | grep rootfs | awk '{print $4}')
ROOT_DISK_UUID=$(system host-disk-list ${COMPUTE} --nowrap | grep ${ROOT_DISK} | awk '{print $2}')
echo "Root disk: $ROOT_DISK, UUID: $ROOT_DISK_UUID"

echo ">>>> Configuring nova-local"
NOVA_SIZE=100
NOVA_PARTITION=$(system host-disk-partition-add -t lvm_phys_vol ${COMPUTE} ${ROOT_DISK_UUID} ${NOVA_SIZE})
NOVA_PARTITION_UUID=$(echo ${NOVA_PARTITION} | grep -ow "| uuid | [a-z0-9\-]* |" | awk '{print $4}')
system host-lvg-add ${COMPUTE} nova-local
system host-pv-add ${COMPUTE} nova-local ${NOVA_PARTITION_UUID}
sleep 2

if [ "$COMPUTE" == "controller-0" ]; then
echo ">>> For Controller0: Wait for partition $NOVA_PARTITION_UUID to be ready."
while true; do
	if system host-disk-partition-list $COMPUTE --nowrap | grep $NOVA_PARTITION_UUID | grep Ready ; then
		break
	fi
	sleep 1
done
fi

system host-pv-list ${COMPUTE} 

