#!/bin/sh

source /etc/platform/openrc
set -ex

hostname=$1

system host-disk-list $hostname

ROOTFS=`system host-show ${hostname} | grep rootfs | awk '{print $4}'`
ALL_HDD=`system host-disk-list ${hostname} --nowrap | grep "/dev" | grep -v $ROOTFS | awk '{print $2;}'`
for hdd in $ALL_HDD; do
	system host-stor-add ${hostname} ${hdd}
done

system interface-network-assign ${hostname} mgmt0 cluster-host
