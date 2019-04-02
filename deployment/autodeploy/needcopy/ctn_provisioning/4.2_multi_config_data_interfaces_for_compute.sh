#!/bin/sh

source /etc/platform/openrc

DATA0IF=eth1000
DATA1IF=eth1001
PHYSNET0='physnet0'
PHYSNET1='physnet1'
SPL=/tmp/tmp-system-port-list
SPIL=/tmp/tmp-system-host-if-list

# configure the datanetworks in sysinv, prior to referencing it in the 'system host-if-modify command'.
system datanetwork-add ${PHYSNET0} vlan
system datanetwork-add ${PHYSNET1} vlan


NOWRAP="--nowrap"
COMPUTES=`system host-list $NOWRAP | grep compute- | cut -d '|' -f 3`

for compute in $COMPUTES; do
  echo "Configuring interface for: $compute"
  set -ex
  system host-port-list ${compute} $NOWRAP > ${SPL}
  system host-if-list -a ${compute} $NOWRAP > ${SPIL}
  DATA0PCIADDR=$(cat $SPL | grep $DATA0IF |awk '{print $8}')
  DATA1PCIADDR=$(cat $SPL | grep $DATA1IF |awk '{print $8}')
  DATA0PORTUUID=$(cat $SPL | grep ${DATA0PCIADDR} | awk '{print $2}')
  DATA1PORTUUID=$(cat $SPL | grep ${DATA1PCIADDR} | awk '{print $2}')
  DATA0PORTNAME=$(cat $SPL | grep ${DATA0PCIADDR} | awk '{print $4}')
  DATA1PORTNAME=$(cat  $SPL | grep ${DATA1PCIADDR} | awk '{print $4}')
  DATA0IFUUID=$(cat $SPIL | awk -v DATA0PORTNAME=$DATA0PORTNAME '($12 ~ DATA0PORTNAME) {print $2}')
  DATA1IFUUID=$(cat $SPIL | awk -v DATA1PORTNAME=$DATA1PORTNAME '($12 ~ DATA1PORTNAME) {print $2}')
  system host-if-modify -m 1500 -n data0 -d ${PHYSNET0} -c data ${compute} ${DATA0IFUUID}
  system host-if-modify -m 1500 -n data1 -d ${PHYSNET1} -c data ${compute} ${DATA1IFUUID}
  set +ex
done

