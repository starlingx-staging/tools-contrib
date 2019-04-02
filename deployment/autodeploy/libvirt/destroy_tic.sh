#!/bin/bash

name=$1


sudo virsh destroy $name || true
sudo virsh undefine $name || true
sudo rm -rf /var/lib/libvirt/images/$name-0.img
sudo rm -rf /var/lib/libvirt/images/$name-1.img

