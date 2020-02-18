#!/bin/sh

source /etc/platform/openrc
set -ex

NODE=$1
DATA_NIC_NUM=$2
DATA0IF=$3
DATA1IF=$4

if [ -z $DATA_NIC_NUM ]; then DATA_NIC_NUM=1; fi
echo "DATA Interface num: $DATA_NIC_NUM"

PHYSNET0='physnet0'
PHYSNET1='physnet1'
NOWRAP="--nowrap"

echo ">>> Configuring Data Networks for $NODE"
SPL=/tmp/tmp-system-port-list
SPIL=/tmp/tmp-system-host-if-list
system host-port-list ${NODE} $NOWRAP > ${SPL}
system host-if-list -a ${NODE} $NOWRAP > ${SPIL}

if [ "$DATA_NIC_NUM" -gt "0" ]; then
	DATA0PCIADDR=$(cat $SPL | grep $DATA0IF |awk '{print $8}')
	DATA0PORTUUID=$(cat $SPL | grep ${DATA0PCIADDR} | awk '{print $2}')
	DATA0PORTNAME=$(cat $SPL | grep ${DATA0PCIADDR} | awk '{print $4}')
	DATA0IFUUID=$(cat $SPIL | awk -v DATA0PORTNAME=$DATA0PORTNAME '($12 ~ DATA0PORTNAME) {print $2}')

	if ! system datanetwork-list | grep ${PHYSNET0} ; then system datanetwork-add ${PHYSNET0} vlan; fi
	system host-if-modify -m 1500 -n data0 -c data ${NODE} ${DATA0IFUUID}
	system interface-datanetwork-assign ${NODE} ${DATA0IFUUID} ${PHYSNET0}
fi

if [ "$DATA_NIC_NUM" -gt "1" ]; then
	DATA1PCIADDR=$(cat $SPL | grep $DATA1IF |awk '{print $8}')
	DATA1PORTUUID=$(cat $SPL | grep ${DATA1PCIADDR} | awk '{print $2}')
	DATA1PORTNAME=$(cat  $SPL | grep ${DATA1PCIADDR} | awk '{print $4}')
	DATA1IFUUID=$(cat $SPIL | awk -v DATA1PORTNAME=$DATA1PORTNAME '($12 ~ DATA1PORTNAME) {print $2}')

	if ! system datanetwork-list | grep ${PHYSNET1} ; then system datanetwork-add ${PHYSNET1} vlan; fi
	system host-if-modify -m 1500 -n data1 -c data ${NODE} ${DATA1IFUUID}
	system interface-datanetwork-assign ${NODE} ${DATA1IFUUID} ${PHYSNET1}
fi

