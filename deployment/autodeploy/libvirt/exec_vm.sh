#!/bin/bash
set -e

name=$1
sudo virsh start $name
#sudo virt-manager

