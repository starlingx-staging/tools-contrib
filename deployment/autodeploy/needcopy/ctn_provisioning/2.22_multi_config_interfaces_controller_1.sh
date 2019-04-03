#!/bin/sh

source /etc/platform/openrc
export COMPUTE='controller-1' 
OAM_IF=ens6
NOWRAP="--nowrap"

echo ">>> Configuring OAM Network"
system host-if-modify -n oam0 -c platform --networks oam ${COMPUTE} $(system host-if-list -a $COMPUTE  $NOWRAP | grep ${OAM_IF} | awk '{ print $2; }')

system host-if-modify ${COMPUTE} mgmt0 --networks cluster-host
