#!/bin/bash

for i in {1..4}; do
	if ifconfig -a | grep stxbr$i | grep -v "stxbr$i-nic"; then
	    sudo ifconfig stxbr$i down || true
	    sudo brctl delbr stxbr$i || true
	fi
done

for br in virbr1 virbr2 virbr3 virbr4; do
    sudo ifconfig $br down || true
    sudo brctl delbr $br || true
    sudo brctl addbr $br
done
sudo ifconfig virbr1 10.10.10.1/24 up
sudo ifconfig virbr2 192.178.204.1/24 up
sudo ifconfig virbr3 up
sudo ifconfig virbr4 up

if ! sudo iptables -t nat -L | grep -q 10.10.10.0/24; then
    sudo iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -j MASQUERADE
    sudo iptables -I FORWARD -s 10.10.10.0/24 -j ACCEPT
    sudo iptables -I FORWARD -d 10.10.10.0/24  -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
fi

