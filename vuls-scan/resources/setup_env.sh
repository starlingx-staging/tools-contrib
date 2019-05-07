#!/bin/bash
set -x
GOROOT=/usr/local/go
GOPATH=/home/wrsroot/go
_PATH=$PATH:$GOROOT/bin:$GOPATH/bin
#SETUP PROXY/ uncomment if you are behind a proxy
#echo "export http_proxy=$H_PROXY" >> /home/wrsroot/.bashrc
#echo "export https_proxy=$HS_PROXY" >> /home/wrsroot/.bashrc
#sudo echo "proxy=$H_PROXY" >>/etc/yum.conf
#SETUP GO ENV
echo "export GOROOT=$GOROOT" >> /home/wrsroot/.bashrc
echo "export GOPATH=$GOPATH" >> /home/wrsroot/.bashrc
echo "export PATH=$_PATH" >> /home/wrsroot/.bashrc
#setup DNS/ uncomment if your vm needs has DNS problems
#cat resolv.conf >>/etc/resolv.conf
