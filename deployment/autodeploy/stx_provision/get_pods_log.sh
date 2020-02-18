#!/bin/bash

rm -rf ~/pod_logs
mkdir ~/pod_logs
cd ~/pod_logs

export KUBECONFIG="/etc/kubernetes/admin.conf"

set -x

PODS=`kubectl -n openstack get po | grep -v NAME | awk '{print $1}'`
kubectl -n openstack get po -o wide > OS_ALL_PODS.log
for POD in $PODS; do
	STATUS=`kubectl -n openstack get po | grep $POD | awk -F"[ \t]+" '{print $3}'`
	kubectl -n openstack logs $POD > OS_$POD\_$STATUS.log
done

SYS_PODS=`kubectl -n kube-system get po | grep -v NAME | awk '{print $1}'`
kubectl -n kube-system get po -o wide > SYS_ALL_PODS.log
for POD in $SYS_PODS; do
	STATUS=`kubectl -n kube-system get po | grep $POD | awk -F"[ \t]+" '{print $3}'`
	kubectl -n kube-system logs $POD > SYS_$POD\_$STATUS.log
done

