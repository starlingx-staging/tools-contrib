#!/bin/sh

source /etc/platform/openrc

NOWRAP="--nowrap"

COMPUTES=`system host-list $NOWRAP | grep compute- | cut -d '|' -f 3`

for compute in $COMPUTES; do
	system host-if-modify $compute mgmt0 --networks cluster-host
done

