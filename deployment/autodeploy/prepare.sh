#!/bin/bash

user=`whoami`
cat << EOF | sudo tee /etc/sudoers.d/${user}
${user} ALL = (root) NOPASSWD:ALL
EOF

sudo sysctl net.ipv6.conf.all.disable_ipv6
sudo ufw disable
sudo sysctl -w net.ipv4.ip_forward=1

sudo chmod 777 *.sh
sudo chmod 777 stx_provision/*.sh
sudo chmod 777 stx_provision/*/*.sh
sudo chmod 777 libvirt/*.sh
if [ ! -e "libvirt/vms" ]; then
    mkdir libvirt/vms
fi
sudo apt-get install expect -y

if [ ! -e "stx_provision/cirros-0.4.0-x86_64-disk.img" ]; then
    echo "download cirros image"
    wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img -P stx_provision
fi

sudo apt install net-tools -y

