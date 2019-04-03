#!/bin/sh

source /etc/platform/openrc

while true; do
    system host-list | grep 2
    if [ $? -eq 0 ]; then
        echo "The 2nd Node is up."
        break;
    fi;
    sleep 1;
done

system host-update 2 personality=controller

echo "finished"

