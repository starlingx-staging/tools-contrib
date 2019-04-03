#!/bin/bash
set -e

xml=$1
name=$2
mem_gb=$3
cpus=$4
disk0_size_gb=$5
disk1_size_gb=$6
iso=$7
imgloc=$8

if [ ! -d "$imgloc" ]; then
    imgloc="/var/lib/libvirt/images"
fi

echo "Createing VM for $name"

sudo virsh destroy $name || true
sudo virsh undefine $name || true
sudo rm -rf $imgloc/$name-0.img
sudo qemu-img create -f qcow2 $imgloc/$name-0.img ${disk0_size_gb}G
sudo rm -rf $imgloc/$name-1.img
sudo qemu-img create -f qcow2 $imgloc/$name-1.img ${disk1_size_gb}G

cp $1.xml vms/$name.xml
sed -i -e "s,NAME,$name," \
       -e "s,ISO,$iso," \
       -e "s,MEM_IN_GIB,$mem_gb," \
       -e "s,CPU_NUM,$cpus," \
       -e "s,DISK0,$imgloc/$name-0.img," \
       -e "s,DISK1,$imgloc/$name-1.img," \
    vms/$name.xml

sudo virsh define vms/$name.xml
echo "KVM: domain $name defined"

