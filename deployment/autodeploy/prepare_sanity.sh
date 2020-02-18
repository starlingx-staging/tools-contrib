#!/bin/bash

location=$1

set -x
if [ "$location" == "sh" ]; then
	export http_proxy=10.239.4.80:913
	export https_proxy=10.239.4.80:913
fi
if [ "$location" == "gdc" ]; then
	export http_proxy=10.19.8.225:911
	export https_proxy=10.19.8.225:912
fi
set +x

sudo -H -E pip2 install ConfigParser

if [ ! -e "needcopy/CentOS-7-x86_64-GenericCloud.qcow2" ]; then
    echo "download CentOS image"
    wget http://10.219.128.66/sanity-images/CentOS-7-x86_64-GenericCloud.qcow2 -P needcopy
fi

if [ ! -e "needcopy/cirros-0.4.0-x86_64-disk.img" ]; then
    echo "download cirros image"
    wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img -P needcopy
fi
