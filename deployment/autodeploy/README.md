
Auto-deploy script
===

## Get Your System Prepared

This script is tested on
* Ubuntu 16.04/18.04/18.10
* Python 2.7
* Libvirt

Install libvirt.

To install libvirt, go into folder libvirt/install/, and run install_packages.sh.

## Quick Start for Containerized Deployment

1. Modify container.conf for the system mode and vm settings.
2. Check k8s.conf and proxy.conf under controllerconfig folder, to see if DNS, registry, and docker proxy settings are ok.
3. Download the ISO for deployment and run the following cmd:
   ```
   $ python autodeploy_ctn.py test.iso helm_charts.tgz --autoiso
   ```
4. If need email notification, please check mailconfig.ini for email address to receive the notification mail, and run the following cmd:
   ```
   $ python autodeploy_ctn.py test.iso helm_charts.tgz --autoiso --email
   ```
NOTE: Detailed settings and command flags please see below.

## Config Files

* container.conf
Containerized deployment configs.
Set the following configs before running the autodeploy_ctn.py tool:
  ```
  # system mode, you can set as simplex|duplex|multi
  TIC_SYSTEM_MODE=simplex

  # number of controller nodes
  TIC_CONTROLLER_NUM=1

  # number of compute nodes
  TIC_COMPUTE_NUM=1

  # the prefix name of the vms to be created for deployment
  VM_PREFIX_NAME=ctn-

  # Location to place vm images
  VM_IMG_LOCATION=/Your/Location/For/VMImages

  # ip addresses for controller0 and controller1
  TIC_CONTROLLER0_IP=10.10.10.3
  TIC_CONTROLLER1_IP=10.10.10.4

  ## Controller Config
  #vcpu #
  TIC_CONTROLLER_CPUS=6
  #memory size, in GiB
  TIC_CONTROLLER_MEM=24
  #disk1 size, in GiB
  TIC_CONTROLLER_DISK1=300
  #disk2 size, in GiB
  TIC_CONTROLLER_DISK2=30

  ## Compute Config
  #vcpu #
  TIC_COMPUTE_CPUS=4
  #memory size, in GiB
  TIC_COMPUTE_MEM=16
  #disk1 size, in GiB
  TIC_COMPUTE_DISK1=300
  #disk2 size, in GiB
  TIC_COMPUTE_DISK2=100

  # Containerization Config
  # NTP server address
  NTP_SERVERS="0.pool.ntp.org,1.pool.ntp.org"
  # whether use docker proxy (docker proxy is set in controllerconfig/proxy.conf)
  DOCKER_PROXY=n

  ```
For containerized deployment, the tool will copy controllerconfig/k8s.conf and controllerconfig/proxy.conf to the test controller config file, you can modify the DNS, registry, and docker proxy settings in those 2 files.


### 

## Command Line

You can check supported cmd line with -h flag, the most useful flags are listed below.

   ```
   positional arguments:
     iso                   The ISO file to deploy
     helm_charts           The helm charts for stx-openstack application

   optional arguments:
     --start {1,2,3,4,5,6,99}
               start point:
               1: create vbox;
               2: after config_controller;
               3: after controller unlocked;
               4: after compute nodes up;
               5: bring up containerized services;
               6: all deployment finished (run with --log to get system logs only);
               99: check NIC name.
     --autoiso             Modify ISO file for auto install and config_controller.
   ```
