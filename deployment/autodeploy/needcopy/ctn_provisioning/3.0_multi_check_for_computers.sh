#!/bin/sh

source /etc/platform/openrc

hostid=$1
nodeid=$2

while true; do
    system host-list | grep $nodeid
    if [ $? -eq 0 ]; then
	    echo "The Compute Node is up."
        break;
    fi;
    sleep 1;
done

system host-update $nodeid personality=worker hostname=compute-$hostid

echo "finished"
