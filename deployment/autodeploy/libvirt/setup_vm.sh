#!/bin/bash
set -e

if [ "$#" == "9" ]; then
	xml=$1
	name=$2
	mem_gb=$3
	cpus=$4
	disk0_size_gb=$5
	disk1_size_gb=$6
	disk2_size_gb=$7
	iso=$8
	imgloc=$9
else
	exit 1
fi


if [ ! -d "$imgloc" ]; then
    imgloc="/var/lib/libvirt/images"
fi

echo "Createing VM for $name"

set +e
sudo virsh list --all | grep $name
found_vm="$?"
sudo virsh list --all | grep $name | grep running
found_vm_running="$?"
set -e

## Delete the vm and disks if found existing instance.
if [ "$found_vm" == "0" ]; then
	if [ "$found_vm_running" == "0" ]; then
		sudo virsh destroy $name || true
	fi
	sudo virsh undefine $name || true
	sudo rm -rf $imgloc/$name-0.img
	sudo rm -rf $imgloc/$name-1.img
	# 3 disks
	if [ "$#" == "9" ]; then
		sudo rm -rf $imgloc/$name-2.img
	fi
fi

## Create disk images.
sudo qemu-img create -f qcow2 $imgloc/$name-0.img ${disk0_size_gb}G
sudo qemu-img create -f qcow2 $imgloc/$name-1.img ${disk1_size_gb}G
# 3 disks
if [ "$#" == "9" ]; then
	sudo qemu-img create -f qcow2 $imgloc/$name-2.img ${disk2_size_gb}G
fi

## modify domain description xml and define vms accordingly.
cp $1.xml vms/$name.xml
sed -i -e "s,NAME,$name," \
       -e "s,ISO,$iso," \
       -e "s,MEM_IN_GIB,$mem_gb," \
       -e "s,CPU_NUM,$cpus," \
       -e "s,DISK0,$imgloc/$name-0.img," \
       -e "s,DISK1,$imgloc/$name-1.img," \
       -e "s,DISK2,$imgloc/$name-2.img," \
    vms/$name.xml

sudo virsh define vms/$name.xml
echo "KVM: domain $name defined"

