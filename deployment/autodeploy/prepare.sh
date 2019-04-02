
user=`whoami`
cat << EOF | sudo tee /etc/sudoers.d/${user}
${user} ALL = (root) NOPASSWD:ALL
EOF

sudo chmod 777 *.sh
sudo chmod 777 needcopy/*.sh
sudo chmod 777 needcopy/*/*.sh
sudo chmod 777 libvirt/*.sh
if [ ! -e "libvirt/vms" ]; then
    mkdir libvirt/vms
fi
sudo apt-get install expect -y

if [ ! -e "needcopy/cirros-0.4.0-x86_64-disk.img" ]; then
    echo "download cirros image"
    wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img -P needcopy
fi


