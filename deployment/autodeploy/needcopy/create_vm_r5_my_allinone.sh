source /etc/nova/openrc

system host-list --nowrap &> /dev/null && NOWRAP="--nowrap"
CONTROLLER=`system host-list $NOWRAP | grep controller-0 | cut -d '|' -f 3`
# for each compute node, we should run the followings
for compute in $CONTROLLER; do
    openstack aggregate add host local_storage_lvm_hosts ${compute}
    openstack aggregate add host local_storage_image_hosts ${compute}
done

test -f cirros-0.4.0-x86_64-disk.img 
openstack flavor create --public m1.tinny --id 1 --ram 512 --vcpus 1 --disk 4
openstack image show cirros || openstack image create cirros --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2

openstack network show net || openstack network create net
openstack subnet show subnet || openstack subnet create --network net --subnet-range 192.168.100.0/24 subnet

for i in {0..1}; do
    openstack server show vm$i || openstack server create --flavor m1.tinny --image cirros --nic net-id=net vm$i
done

openstack server list
