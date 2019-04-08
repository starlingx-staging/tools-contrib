#!/bin/bash
set -x
. ./.bashrc
# Download and unpack go
wget https://dl.google.com/go/go1.10.1.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.10.1.linux-amd64.tar.gz
mkdir $HOME/go
# Deploy go-cve-dictionary
sudo mkdir /var/log/vuls
sudo chown -R wrsroot:wrs /var/log/vuls
sudo chmod 700 /var/log/vuls
mkdir -p $GOPATH/src/github.com/kotakanbe
cd $GOPATH/src/github.com/kotakanbe
git clone https://github.com/kotakanbe/go-cve-dictionary.git
cd go-cve-dictionary
make install
# Then Fetch vulnerability data from NVD
cd $HOME
for i in `seq 2002 $(date +"%Y")`
do
  go-cve-dictionary fetchnvd -years $i
done
# Deploy goval-dictionary
cd $GOPATH/src/github.com/kotakanbe
git clone https://github.com/kotakanbe/goval-dictionary.git
cd goval-dictionary
make install
# fetch OVAL data of Red Hat since the server to be scanned is CentOS
cd $HOME
goval-dictionary fetch-redhat 7
# Deploy gost
sudo mkdir /var/log/gost
sudo chown -R wrsroot:wrs /var/log/gost
sudo chmod 700 /var/log/gost
mkdir -p $GOPATH/src/github.com/knqyf263
cd $GOPATH/src/github.com/knqyf263
git clone https://github.com/knqyf263/gost.git
cd gost
make install
# fetch security tracker for RedHat since the server to be scanned is CentOS
cd $HOME
gost fetch redhat --after 2016-01-01
# Deploy go-exploitdb
sudo mkdir /var/log/go-exploitdb
sudo chown -R wrsroot:wrs /var/log/go-exploitdb
sudo chmod 700 /var/log/go-exploitdb
mkdir -p $GOPATH/src/github.com/mozqnet
cd $GOPATH/src/github.com/mozqnet
git clone https://github.com/mozqnet/go-exploitdb.git
cd go-exploitdb
make install
# fetch exploit-db information
cd $HOME
# uncomment proxy if required
go-exploitdb fetch exploitdb #--http-proxy $https_proxy
# Deploy Vuls
mkdir -p $GOPATH/src/github.com/future-architect
cd $GOPATH/src/github.com/future-architect
git clone https://github.com/future-architect/vuls.git
cd vuls
make install
