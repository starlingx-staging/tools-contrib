#!/bin/sh

source /etc/platform/openrc
set -ex

NOWRAP="--nowrap"

COMPUTES=`system host-list $NOWRAP | grep compute- | cut -d '|' -f 3`

for compute in $COMPUTES; do
	system interface-network-assign $compute mgmt0 cluster-host
done

