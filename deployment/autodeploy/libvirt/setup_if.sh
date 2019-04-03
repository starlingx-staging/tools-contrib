#!/bin/bash
set -e

for i in {1..4}; do
    sudo ifconfig stxbr$i down || true
    sudo brctl delbr stxbr$i || true

    sudo ifconfig virbr$i down || true
    sudo brctl delbr virbr$i || true
    sudo brctl addbr virbr$i
done
sudo ifconfig virbr1 10.10.10.1/24 up
sudo ifconfig virbr2 192.168.204.1/24 up
sudo ifconfig virbr3 up
sudo ifconfig virbr4 up
sudo iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -j MASQUERADE

