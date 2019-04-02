#!/bin/sh

source /etc/platform/openrc
export COMPUTE='controller-1' 
PHYSNET0='physnet0' 
PHYSNET1='physnet1' 
OAM_IF=ens6
DATA0IF=eth1000 
DATA1IF=eth1001 
NOWRAP="--nowrap"

echo ">>> Configuring OAM Network"
system host-if-modify -n oam0 -c platform --networks oam ${COMPUTE} $(system host-if-list -a $COMPUTE  $NOWRAP | grep ${OAM_IF} | awk '{ print $2; }')

echo ">>> Configuring Cluster Host Interface"
system host-if-modify $COMPUTE mgmt0 --networks cluster-host

echo ">>> Configuring Data Networks"
SPL=/tmp/tmp-system-port-list  
SPIL=/tmp/tmp-system-host-if-list  
system host-port-list ${COMPUTE} $NOWRAP > ${SPL}  
system host-if-list -a ${COMPUTE} $NOWRAP > ${SPIL}  
DATA0PCIADDR=$(cat $SPL | grep $DATA0IF |awk '{print $8}')  
DATA1PCIADDR=$(cat $SPL | grep $DATA1IF |awk '{print $8}')  
DATA0PORTUUID=$(cat $SPL | grep ${DATA0PCIADDR} | awk '{print $2}')  
DATA1PORTUUID=$(cat $SPL | grep ${DATA1PCIADDR} | awk '{print $2}')  
DATA0PORTNAME=$(cat $SPL | grep ${DATA0PCIADDR} | awk '{print $4}')  
DATA1PORTNAME=$(cat  $SPL | grep ${DATA1PCIADDR} | awk '{print $4}')  
DATA0IFUUID=$(cat $SPIL | awk -v DATA0PORTNAME=$DATA0PORTNAME '($12 ~ DATA0PORTNAME) {print $2}')  
DATA1IFUUID=$(cat $SPIL | awk -v DATA1PORTNAME=$DATA1PORTNAME '($12 ~ DATA1PORTNAME) {print $2}')  
system host-if-modify -m 1500 -n data0 -p ${PHYSNET0} -c data ${COMPUTE} ${DATA0IFUUID}  
system host-if-modify -m 1500 -n data1 -p ${PHYSNET1} -c data ${COMPUTE} ${DATA1IFUUID}

