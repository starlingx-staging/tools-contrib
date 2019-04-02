#!/bin/bash
set -e

name=$1
xml=$2
iso=$3
echo "creating $name with $iso"

sudo virsh destroy $name || true
sudo virsh undefine $name || true
sudo rm -rf /var/lib/libvirt/images/$name-0.img
sudo qemu-img create -f qcow2 /var/lib/libvirt/images/$name-0.img 300G
sudo rm -rf /var/lib/libvirt/images/$name-1.img
sudo qemu-img create -f qcow2 /var/lib/libvirt/images/$name-1.img 250G

cp $xml vms/$name.xml
sed -i -e "s,NAME,$name," \
       -e "s,ISO,$iso," \
       -e "s,DISK0,/var/lib/libvirt/images/$name-0.img," \
       -e "s,DISK1,/var/lib/libvirt/images/$name-1.img," \
    vms/$name.xml
echo "KVM: $name xml ready"
cat vms/$name.xml | grep $name

sudo virsh define vms/$name.xml
echo "KVM: domain $name defined"
sudo virsh start $name

sudo virt-manager
