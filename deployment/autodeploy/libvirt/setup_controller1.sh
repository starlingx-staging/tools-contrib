#!/bin/bash
set -e

name=$1
if [ $# != 1 ] ; then 
echo "USAGE: $0 <controller1 name>" 
echo " e.g.: $0 r5-multi-controller-1" 
exit 1; 
fi 
echo "KVM: createing $name"

sudo virsh destroy $name || true
sudo virsh undefine $name || true
sudo rm -rf /var/lib/libvirt/images/$name-0.img
sudo qemu-img create -f qcow2 /var/lib/libvirt/images/$name-0.img 300G
sudo rm -rf /var/lib/libvirt/images/$name-1.img
sudo qemu-img create -f qcow2 /var/lib/libvirt/images/$name-1.img 250G

cp controller1.xml vms/$name.xml
sed -i -e "s,NAME,$name," \
       -e "s,DISK0,/var/lib/libvirt/images/$name-0.img," \
       -e "s,DISK1,/var/lib/libvirt/images/$name-1.img," \
    vms/$name.xml
echo "KVM: $name xml ready"
cat vms/$name.xml | grep $name

sudo virsh define vms/$name.xml
echo "KVM: domain $name defined"
