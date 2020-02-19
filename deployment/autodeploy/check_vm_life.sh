#!/bin/bash

#set -x
lifetime=$1

VMS=`sudo virsh list --all | grep -v running | awk '{print $2}' | grep -v "Name" | grep "controller-0"`
NOT_OLDER_THAN=`date -d "-$lifetime day" +%s`

for vm in $VMS; do
	ISO=`sudo virsh dumpxml $vm | grep "\.iso" | awk -F "'" '{print $2}'`
	if [ -e $ISO ]; then
		AGE=`date -r $ISO +%s`
		if [ "$AGE" -lt "$NOT_OLDER_THAN" ]; then
			echo "$vm is too old"
			VM_GROUP=`echo $vm | awk -F "-" '{print $1}'`
			echo "$VM_GROUP will be deleted"
			python2 cleanupdeploy.py --vmname $VM_GROUP --delete_all
		fi
	fi

done



