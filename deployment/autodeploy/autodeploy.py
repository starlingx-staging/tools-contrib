#!/usr/bin/env python

import os
import argparse
import json
import shutil
import time
from datetime import datetime

import sys
if sys.version_info < (3,0):
    print("Sorry, requires Python 3.x.")
    sys.exit(1)

import ectest.log as LOG
import ectest.cmd as CMD
import ectest.utils as UTILS
import ectest.testnode as NODE
import ectest.pxe_install as BM_PXE
import ectest.stx_provision as STX

DEBUG = False

CurrPath = os.path.join(os.path.abspath(os.getcwd()))

dplmnt = None
with open("config.json", "r") as f:
    dplmnt = json.load(f)

##########################
### Config
dplmnt["basedir"] = CurrPath

# controller config
dplmnt["config_complete"] = "/etc/platform/.initial_k8s_config_complete"

#########################
##Structure the Arg Parser
desc = "StarlingX Auto Deployment - 2019.11.1"
parser = argparse.ArgumentParser(description=desc)
# positional arguments
parser.add_argument('iso',
    help="The ISO file to deploy", type=str)
# optional arguments
parser.add_argument('--start',
    help="start from: "
         "1: create vms for deployment; "
         "2: setup controller-0; "
         "3: do ansible and provision controller-0; "
         "4: setup and provision controller-1; "
         "5: setup and provision storage nodes; "
         "6: setup and provision compute nodes; "
         "7: bring up openstack containerized services; "
         "99: only get log.",
    default=1, type=int, choices=[1,2,3,4,5,6,7, 99])
parser.add_argument('--stop',
    help="stop after: same step definition as --start.",
    default=7, type=int, choices=[1,2,3,4,5,6,7])
parser.add_argument('--log',
    help="Get controller/compute system logs.",
    action="store_true")
parser.add_argument('--dpdk',
    help="Set VM with ovs-dpdk enabling", action="store_true")
parser.add_argument('--rt',
    help="Install ISO for Low Latency config (only for AIO simplex/duplex.)", action="store_true")
parser.add_argument('--system_mode',
    help="System Mode: simplex, duplex or multi-node.",
    type=str, choices=['simplex', 'duplex', 'multi', 'multi_aio'])
parser.add_argument('--logbase',
    help="Base Dir for Logs",
    type=str)
parser.add_argument('--helm_charts',
    help="Application helm charts to apply.",
    type=str,
    action='append')
parser.add_argument('--config',
    help="Config json file to overwrite default values.",
    type=str,
    action='append')
parser.add_argument('--additional_yml',
    help="Additional yml file attached to localhost.yml.",
    type=str,
    action='append')

### cmd opetions to choose vm or bm.
parser.add_argument('--method',
    help="Create KVM for deployment test.",
    type=str,
    choices=["kvm", "bm"],
    default="kvm")
### cmd options for vm setup
parser.add_argument('--compute_num',
    help="Number of compute nodes. (controller number is not configurable,"
         "and is determined by system mode.)",
    type=int, choices=[1,2,3,4,5,6])
parser.add_argument('--storage_num',
    help="Number of storage nodes.",
    type=int, choices=[0,2])
parser.add_argument('--virtimg_dir',
    help="Dir to place kvm images for controllers and computes.",
    type=str)
parser.add_argument('--prefix',
    help="Prefix name of the vms",
    type=str)
### cmd options for bm setup
parser.add_argument('--bm_controller0',
    help="Json description for controller0 testnode.", type=str)
parser.add_argument('--bm_controller1',
    help="Json description for controller1 testnode.", type=str)
parser.add_argument('--bm_storages',
    help="Json description for storage testnodes.", type=str,
    action='append')
parser.add_argument('--bm_workers',
    help="Json description for worker testnodes.", type=str,
    action='append')

# debugging feature
parser.add_argument('--slowdown',
    help="wait more time for slow machine.",
    type=int,
    default=1)

args = parser.parse_args()
dplorch = None

def save_config():
    UTILS.save_json_config(
        dplmnt,
        os.path.join(dplmnt['testdir'], 'config.json'))

    if dplorch:
        for n in dplorch['nodes'].keys():
            UTILS.save_json_config(
                dplorch['nodes'][n].get_node_config(),
                os.path.join(dplmnt['testdir'], '%s.json' % n))

def exit_with_failure():
    global dplmnt
    dplmnt['status'] = "Fail"
    dplmnt['endtime'] = datetime.now().strftime('%H:%M:%S')
    LOG.Error("#### ERROR: failed at %s ####" % dplmnt['endtime'])

    if dplorch:
        if dplorch["current_step"] > STEP_CONTROLLER0:
            STX.get_system_logs(node_0)
        save_config()
    exit(1)

def exit_with_success():
    save_config()
    exit(0)

def CK_RET(result, log=None):
    UTILS.check_ret(result, exit_with_failure, log=log)

# check config overwrite
if args.config:
    for c in args.config:
        abs_c = os.path.abspath(c)
        CK_RET(UTILS.check_file_exist(os.path.abspath(c)))
        with open(abs_c, "r") as f:
            overwrite = json.load(f)
            UTILS.update_json_config(dplmnt, overwrite)

# check ISO
dplmnt["iso"] = os.path.abspath(args.iso)
CK_RET(UTILS.check_file_exist(dplmnt["iso"]))
dplmnt["isoname"] = os.path.basename(args.iso)

# check helm_charts
dplmnt["helm_charts_list"] = []
if args.helm_charts:
    for chart in args.helm_charts:
        dplmnt["helm_charts_list"].append(os.path.abspath(chart))
        CK_RET(UTILS.check_file_exist(os.path.abspath(chart)))

# check additional yml files
dplmnt['additional_yml_list'] = []
if args.additional_yml:
    for yml in args.additional_yml:
        dplmnt["additional_yml_list"].append(os.path.abspath(yml))
        CK_RET(UTILS.check_file_exist(os.path.abspath(yml)))

dplmnt["dpdk"] = ''
if args.dpdk:
    dplmnt["dpdk"] = 'ovs-dpdk'

dplmnt['adminpassword'] = dplmnt['ansible_config']['ADMIN_PASSWORD_TO_SET']
dplmnt["password"] = dplmnt["username"]
if args.logbase:
    dplmnt["basedir"] = os.path.abspath(args.logbase)
    if not os.path.exists(dplmnt["basedir"]):
        os.makedirs(dplmnt["basedir"])

## Config testnode type used for the deployment test
dplmnt["method"] = args.method
def iskvm():
    return dplmnt["method"] == "kvm"
def isbm():
    return dplmnt["method"] == "bm"

def normalize_testnodes_config():
    ALL_POSIBLE_SYSTEM_MODE = ["multi", "simplex", "duplex", "multi_aio"]
    if args.system_mode:
        dplmnt["system_mode"] = args.system_mode
    CK_RET(dplmnt["system_mode"] in ALL_POSIBLE_SYSTEM_MODE,
        log="Wrong System Mode.")

    if iskvm():
        if args.compute_num != None:
            dplmnt["compute_num"] = args.compute_num
        if args.storage_num != None:
            dplmnt["storage_num"] = args.storage_num
        if args.virtimg_dir:
            dplmnt['vm_img_location'] = os.path.abspath(args.virtimg_dir)
        CK_RET(os.path.exists(dplmnt["vm_img_location"]),
            log="%s not exist." % dplmnt['vm_img_location'])
        if args.prefix:
            dplmnt['vm_prefix_name'] = args.prefix
    if isbm():
        configfiles = []
        if args.bm_controller0:
            CK_RET(UTILS.check_file_exist(args.bm_controller0), log="bm machine not exist.")
            dplmnt["bm_controller0"] = args.bm_controller0
        if args.bm_controller1:
            CK_RET(UTILS.check_file_exist(args.bm_controller1), log="bm machine not exist.")
            dplmnt["bm_controller1"] = args.bm_controller1
        dplmnt["bm_storage_nodes"] = []
        dplmnt["bm_worker_nodes"] = []
        if args.bm_storages:
            for n in args.bm_storages: CK_RET(UTILS.check_file_exist(n), log="bm machine not exist.")
            dplmnt["bm_storage_nodes"] = args.bm_storages
            dplmnt["storage_num"] = len(dplmnt["bm_storage_nodes"])
        if args.bm_workers:
            for n in args.bm_workers: CK_RET(UTILS.check_file_exist(n), log="bm machine not exist.")
            dplmnt["bm_worker_nodes"] = args.bm_workers
            dplmnt["compute_num"] = len(dplmnt["bm_worker_nodes"])
    ## Normalize Test Config
    if dplmnt["system_mode"] == "duplex":
        dplmnt["controller_num"] = 2
        dplmnt["compute_num"] = 0
        dplmnt["storage_num"] = 0
        if isbm() and not (dplmnt["bm_controller0"] and dplmnt["bm_controller1"]):
            LOG.Error("BM: no bm machine provided.")
            exit_with_failure()
    elif dplmnt["system_mode"] == "simplex":
        dplmnt["controller_num"] = 1
        dplmnt["compute_num"] = 0
        dplmnt["storage_num"] = 0
        if isbm() and not dplmnt["bm_controller0"]:
            LOG.Error("BM: no bm machine provided.")
            exit_with_failure()
    else:
        # For containerized version multi-node, there must have 2 controllers.
        dplmnt["controller_num"] = 2
        if dplmnt['system_mode'] == 'multi_aio':
            dplmnt["storage_num"] = 0
        if iskvm() and dplmnt["compute_num"] < 1: dplmnt["compute_num"] = 1
        if isbm():
            CK_RET(dplmnt["compute_num"] > 0,
                log="BM: no bm machine provided.")

normalize_testnodes_config()

###################
# Sub Functions   #
###################

def RUN_STEP(num_of_step):
    if args.start <= num_of_step and args.stop >= num_of_step:
        LOG.Info("#######################")
        LOG.Time("# Step %d Started." % num_of_step)
        dplorch["current_step"] = num_of_step
        return True
    LOG.Info("#######################")
    LOG.Time("# Step %d Skipped." % num_of_step)
    return False

def FINISH_STEP(num_of_step):
    LOG.Time("Step %d Finished" % num_of_step)
    if args.stop <= num_of_step:
        LOG.Info("#################################")
        LOG.Info("Test Finished!!!")
        dplmnt['status'] = "Finished"
        dplmnt['endtime'] = datetime.now().strftime('%H:%M:%S')
        LOG.Time("<<<Deployment Finished>>>")
        if args.log and num_of_step > STEP_CONTROLLER0:
            STX.get_system_logs(node_0)
        exit_with_success()

def logfile(name):
    return os.path.join(dplmnt["testdir"], name)

def cmdhost(cmd, cwd=None, logfile=None, silent=False):
    retval, result = CMD.shell(cmd, cwd=cwd, logfile=logfile, silent=silent, DEBUG=DEBUG)
    if not silent:
        LOG.Info("Finished \"%s\"\n" % cmd, silent=silent)
        LOG.Info("\n".join(result))

    return retval

##########################################
# Manage nodes for hosts

dplorch = {}
dplorch["nodes"] = {}
dplorch["floating_ip_oam"] = None
dplorch["current_step"] = 1

STEP_ENV_CREATE = 1
STEP_CONTROLLER0_INSTALL = 2
STEP_CONTROLLER0 = 3
STEP_CONTROLLER1 = 4
STEP_STORAGE = 5
STEP_COMPUTE = 6
STEP_APP_APPLY = 7

def get_node_step(node):
    hostname = node.get_hostname()
    personality = node.get_personality()
    if hostname == NODE.HOSTNAME_CONTROLLER0:
        return STEP_CONTROLLER0
    elif hostname == NODE.HOSTNAME_CONTROLLER1:
        return STEP_CONTROLLER1
    elif personality == NODE.PERSONALITY_STORAGE:
        return STEP_STORAGE
    elif personality == NODE.PERSONALITY_COMPUTE:
        return STEP_COMPUTE
    else:
        LOG.Error("No valid test step for the node %s." % hostname)
        return -1

def add_node(name, id, configfile=None, vmprefix=None, ip_oam=None):
    global dplmnt
    node = None
    if iskvm():
        if not configfile:
            configfile = os.path.join(CurrPath,
                "testnode_config",
                "testnode",
                "vm_template.json")
        vmname = vmprefix + "_" + name

        node = NODE.Node_KVM(
            configfile,
            vmname, name, id, ip_oam,
            user=dplmnt["username"],
            password=dplmnt['password'],
            slowdown=args.slowdown)
        node.set_floating_ip(
            dplmnt['ansible_config']['CONTROLLER_FLOATING_TO_SET'])
    elif isbm():
        node = NODE.Node_BM(
            configfile,
            name, id,
            user=dplmnt["username"],
            password=dplmnt['password'],
            slowdown=args.slowdown)
        node.set_floating_ip(dplmnt['ansible_config']['CONTROLLER_FLOATING_TO_SET'])
        if name == NODE.HOSTNAME_CONTROLLER0:
            node.set_oam_ip(dplmnt['ansible_config']['CONTROLLER0_OAM_TO_SET'])
        elif name == NODE.HOSTNAME_CONTROLLER1:
            node.set_oam_ip(dplmnt['ansible_config']['CONTROLLER1_OAM_TO_SET'])

    if dplmnt['system_mode'] == "simplex":
        node.set_floating_ip(node.get_oam_ip())

    dplorch["nodes"][name] = node

def get_node_by_step(step):
    node_list = []
    for node in dplorch["nodes"].keys():
        if get_node_step(dplorch["nodes"][node]) == step:
            node_list.append(node)
    node_list.sort()
    return node_list
def get_controllers():
    return get_node_by_step(STEP_CONTROLLER0) + get_node_by_step(STEP_CONTROLLER1)
def get_floating_ip():
    return dplorch["floating_ip_oam"]
###################
# Main Logic      #
###################

##########################
dplmnt['name'] = "DeploymentTest-%s" % datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
dplmnt["testdir"] = os.path.join(dplmnt["basedir"], dplmnt['name'])
dplmnt['starttime'] = datetime.now().strftime('%H:%M:%S')
dplmnt['startdate'] = datetime.now().strftime('%Y-%m-%d')
dplmnt['log'] = os.path.join(dplmnt["testdir"], "test.log")

os.makedirs(dplmnt["testdir"])
dplmnt['status'] = "InProcess"
dplmnt['endtime'] = ""

LOG.Start(dplmnt['log'])

##########################
# get controller/compute nodes information from the config file.
#

vm_prefix = "%s_%s_%s" % (dplmnt['vm_prefix_name'],
    dplmnt['vm_bridge']['virbr1'],
    dplmnt['system_mode'])
controller_start_id = 1
storage_start_id = dplmnt['controller_num'] + 1
compute_start_id = dplmnt['controller_num'] + dplmnt['storage_num'] + 1
for i in range(dplmnt['controller_num']):
    configfile = None
    if isbm():
        configfile = dplmnt["bm_controller0"] if i == 0 else dplmnt["bm_controller1"]
    add_node(
        "controller-" + str(i), i + controller_start_id,
        configfile=configfile,
        vmprefix=vm_prefix,
        ip_oam=dplmnt['ansible_config']["CONTROLLER" + str(i) + "_OAM_TO_SET"])
for i in range(dplmnt['storage_num']):
    configfile = None
    if isbm():
        configfile = dplmnt["bm_storage_nodes"][i]
    add_node(
        "storage-" + str(i), i + storage_start_id,
        configfile=configfile,
        vmprefix=vm_prefix)
for i in range(dplmnt['compute_num']):
    configfile = None
    if isbm():
        configfile = dplmnt["bm_worker_nodes"][i]
    add_node("compute-" + str(i), i + compute_start_id,
        configfile=configfile,
        vmprefix=vm_prefix)

for node in dplorch["nodes"].keys():
    dplorch["nodes"][node].check_nic_available(dplmnt['system_mode'])

dplorch["floating_ip_oam"] = dplmnt['ansible_config']['CONTROLLER_FLOATING_TO_SET']
node_0 = dplorch["nodes"][get_node_by_step(STEP_CONTROLLER0)[0]]
def node_n(name):
    return dplorch["nodes"][name]

################################################
## Generate Config/Provisioning Scripts

def generate_ansible_config():
    # generate ansible config file according to the settings
    config_file = os.path.join(dplmnt["testdir"], "localhost.yml")

    def add_config(target, config_name):
        folder = "ansibleconfig"
        suffix = ".yml"
        src = os.path.join(CurrPath, folder, config_name + suffix)
        ret = cmdhost("cat %s >> %s" % (src, target), silent=True)
        if ret != 0:
            LOG.Error("Failed to add ansible config %s to %s" % (src, target))
            exit(-1)

    add_config(config_file,
        "simplex" if dplmnt["system_mode"] == "simplex" else "duplex")

    if dplmnt["dns_server"].startswith('y'):
        add_config(config_file, "dns_server")
    if dplmnt["docker_registry"].startswith('y'):
        add_config(config_file, "docker_registry")
    if dplmnt["docker_proxy"].startswith('y'):
        add_config(config_file, "docker_proxy")

    if dplmnt['additional_yml_list']:
        for yml in dplmnt['additional_yml_list']:
            cmdhost("cat %s >> %s" % (yml, config_file), silent=True)

    for key in dplmnt['ansible_config']:
        cmdhost("sed -i 's/%s/%s/g' %s"
            % (key, dplmnt['ansible_config'][key].replace(".", "\.").replace("/", "\/"),
                config_file), silent=True)

    return config_file

def copy_provision_script_to_node(node):
    if iskvm() and isinstance(node, NODE.Node_KVM):
        CK_RET(node.kvm_update_netmap())
        CK_RET(node.kvm_update_nicname())

    script_folder = os.path.join(dplmnt["testdir"], 'needcopy')
    if not os.path.exists(script_folder):
        UTILS.copy_folder(os.path.join(CurrPath, "stx_provision"), script_folder)

    CK_RET(node.copy_to_node(script_folder + "/*", "~/"))
    CK_RET(node.ssh("sudo chmod +x *.sh; sudo chmod +x */*.sh", sudo=True))


LOG.Info("##########################")
LOG.Info("# Start to deploy %s" % dplmnt["iso"])
LOG.Info("#     helm charts %s" % dplmnt["helm_charts_list"])
LOG.Info("# start from Step %s" % args.start)
LOG.Info("# stop after Step %s" % args.stop)
LOG.Info("# docker proxy %s" % dplmnt["docker_proxy"])
LOG.Time("<<<Deployment Started>>>")
LOG.Info("# Deployment method: %s with %s" % (dplmnt["system_mode"],
    dplmnt["method"]))
## Test Nodes
LOG.Info("# Num of Controllers: %d" % dplmnt['controller_num'])
for n in get_controllers():
    node = dplorch["nodes"][n]
    LOG.Info("#   %s @ %s" % (node.get_hostname(), node.get_oam_ip()))
if dplmnt['system_mode'] != "simplex":
    LOG.Info("#   Floating IP @ %s" % get_floating_ip())
LOG.Info("# Num of Storage Nodes: %d" % dplmnt['storage_num'])
for n in get_node_by_step(STEP_STORAGE):
    node = dplorch["nodes"][n]
    LOG.Info("#   %s" % node.get_hostname())
LOG.Info("# Num of Compute Nodets: %d" % dplmnt['compute_num'])
for n in get_node_by_step(STEP_COMPUTE):
    node = dplorch["nodes"][n]
    LOG.Info("#   %s" % node.get_hostname())
## Other Config
LOG.Info("# System wrsroot password: %s" % dplmnt["password"])
LOG.Info("# Openstack root user: %s" % dplmnt["openstack_root"])
LOG.Info("# Openstack admin password: %s" % dplmnt['adminpassword'])
if dplmnt["dpdk"]:
    LOG.Info("# ovs type: %s" % dplmnt['dpdk'])
LOG.Info("#")
LOG.Info("#")

########################################
# Deployment Step STEP_ENV_CREATE:
#   create libvirt virtual machines to do the deployment.
#########################################

if RUN_STEP(STEP_ENV_CREATE):
    ##########################
    # deployment preparation
    cmdhost("./prepare.sh")

    #########################################
    # prepare the iso file:
    #   modify to run the installation automatically
    newiso = os.path.join(dplmnt["testdir"], dplmnt["isoname"])

    build_iso_cmds = []
    build_iso_cmds.append(
        "sed -e 's/CONTROLLER0_OAM_TO_SET/%s/' controller0_network.txt "
        " > test_controller0_network.txt" % node_0.get_oam_ip())
    build_iso_cmds.append(
        "sed -i 's/GATEWAY_TO_SET/%s/' test_controller0_network.txt "
        % dplmnt['ansible_config']['GATEWAY_TO_SET'].replace(".", "\."))
    build_iso_cmds.append(
        "sed -i 's/OAM_NIC_TO_SET/%s/' test_controller0_network.txt "
        % node_0.get_oam_name())

    install_mode = 0
    if dplmnt["system_mode"] != "multi":
        if args.rt:
            install_mode = 4
        else:
            install_mode = 2
    build_iso_cmds.append("./rebuild_iso.sh %d %s %s %s" % (
        install_mode,
        dplmnt["iso"],
        newiso,
        dplmnt["testdir"]))

    cmdhost(";".join(build_iso_cmds))

    if iskvm():

        def get_ipv4_range(ipv4, length):
            iprange = ""
            words = ipv4.split(".")
            for i in range(min(length, 4)):
                iprange += words[i] + "."
            return iprange

        #########################################
        # create vms for deployment
        kvmfolder = os.path.join(dplmnt["testdir"], "kvm")
        UTILS.copy_folder("libvirt", kvmfolder)

        kvm_cmds = []
        kvm_cmds.append("cd %s" % kvmfolder)
        nc = dplmnt['vm_bridge']
        kvm_cmds.append("sed -i 's/virbr1/%s/g' *.sh *.xml" % nc['virbr1'])
        kvm_cmds.append("sed -i 's/virbr2/%s/g' *.sh *.xml" % nc['virbr2'])
        kvm_cmds.append("sed -i 's/virbr3/%s/g' *.sh *.xml" % nc['virbr3'])
        kvm_cmds.append("sed -i 's/virbr4/%s/g' *.sh *.xml" % nc['virbr4'])
        mgmt_range = get_ipv4_range(dplmnt["ansible_config"]["MGMT_SUBNET_TO_SET"], 3)
        kvm_cmds.append("sed -i 's/192\.178\.204\./%s/g' *.sh" % mgmt_range.replace(".", "\."))
        oam_range = get_ipv4_range(dplmnt["ansible_config"]["OAM_SUBNET_TO_SET"], 3)
        kvm_cmds.append("sed -i 's/10\.10\.10\./%s/g' *.sh" % oam_range.replace(".", "\."))
        kvm_cmds.append("mkdir vms")
        kvm_cmds.append("./setup_if.sh")

        for n in dplorch["nodes"].keys():
            node = dplorch["nodes"][n]
            personality = node.get_personality()
            template = "ctn_" + personality
            if personality == "controller":
                template = template + str(node.get_nodeid() - 1)
            config = personality + "_config"
            iso = "noiso"
            if node.get_nodeid() == 1:
                iso = newiso

            cmd = "./setup_vm.sh %s %s %s %s %s %s %s %s %s" % (
                  template,
                  node.get_name(),
                  dplmnt[config]['mem_gib'],
                  dplmnt[config]['cpus'],
                  dplmnt[config]['disk1_gib'],
                  dplmnt[config]['disk2_gib'],
                  dplmnt[config]['disk3_gib'],
                  iso,
                  dplmnt['vm_img_location'])
            kvm_cmds.append(cmd)

        cmdhost("; ".join(kvm_cmds), logfile=logfile("1.1_create_kvms.log"))

    elif isbm():
        pxe_config = os.path.join(CurrPath,
            "testnode_config",
            "pxe_server.json")

        install_mode = BM_PXE.MODE_UEFI_STD
        if dplmnt["system_mode"] != "multi":
            if args.rt:
                install_mode = BM_PXE.MODE_UEFI_AIO_LL
            else:
                install_mode = BM_PXE.MODE_UEFI_AIO

        pxe_agent = BM_PXE.PxeAgent(
            pxe_server_config_json=pxe_config,
            iso=newiso,
            default_install=install_mode)
        pxe_agent.mount_iso()

        pxe_agent.prepare_for_node(node_0)
        # pxe_agent.check_pxe_services()
        dplorch['pxe_agent'] = pxe_agent

    else:
        LOG.Error("===== ERROR: Non-supported method to deploy (only kvm supported).")
        exit_with_failure()

FINISH_STEP(STEP_ENV_CREATE)

########################################
# Deployment Step STEP_CONTROLLER0_INSTALL:
#   Install controller-0
#########################################

if RUN_STEP(STEP_CONTROLLER0_INSTALL):

    for node in dplorch["nodes"].keys():
        if node_n(node).is_power_on():
            node_n(node).power_off()
    time.sleep(5)

    CK_RET(node_0.boot())

    node_0.add_route_for_oam(dplmnt['ansible_config']['GATEWAY_TO_SET'])
    CK_RET(node_0.wait_for_node())
    node_0.cleanup_network_env(dplmnt['ansible_config']['GATEWAY_TO_SET'])
    node_0.set_status(NODE.NODE_INSTALLED)

FINISH_STEP(STEP_CONTROLLER0_INSTALL)

########################################
# Deployment Step for Test Nodes:
#   Install, provision, check status for:
#      - controller-0 (only provisioning)
#      - controller-1
#      - storage nodes
#      - compute nodes
#########################################
STX.set_provision_env(
    dplmnt["provision_script"],
    dplmnt["testdir"],
    args.slowdown)

for step in [STEP_CONTROLLER0, STEP_CONTROLLER1, STEP_STORAGE, STEP_COMPUTE]:
    # Get node list for the step
    node_list = get_node_by_step(step)

    if RUN_STEP(step) and node_list:
        # Start up Nodes, Installation and Ansible
        if step == STEP_CONTROLLER0:
            CK_RET(node_0.wait_for_node())
            CK_RET(STX.stx_ansible(
                node_0, generate_ansible_config()))
        else:
            for n in node_list:
                # Close pxe service on host to avoid inturruption of node installation
                # if isbm():
                #     BM_PXE.PxeAgent.close_pxe_services()
                CK_RET(STX.try_for_new_host(node_0, node_n(n)))

            for n in node_list:
                CK_RET(STX.wait_for_host_node_online(
                    node_0, n, 30))
                #CK_RET(node_n(n).wait_for_node())
                STX.stx_get_mgmt_ip(node_0, node_n(n))
                node_n(n).set_status(NODE.NODE_INSTALLED)

        # Provisioning
        if step == STEP_CONTROLLER0:
            node_0.sudo_nopasswd()
            copy_provision_script_to_node(node_0)
            STX.stx_provision_controller(
                node_0,
                node_0,
                dplmnt['system_mode'],
                dplmnt["ntp_server"],
                dplmnt["dpdk"])
        if step == STEP_CONTROLLER1:
            STX.stx_provision_controller(
                node_0,
                node_n(node_list[0]),
                dplmnt['system_mode'])
        elif step == STEP_STORAGE:
            STX.stx_provision_storage(node_0, node_list)
        elif step == STEP_COMPUTE:
            node_dict = {}
            for n in node_list:
                node_dict[n] = node_n(n)
            STX.stx_provision_compute(node_0, node_dict,
                dplmnt['storage_num'] > 0 or dplmnt['system_mode'] == 'multi_aio')

    # Do before step finish, even if the step is skipped
    if node_list:
        for n in node_list:
            if step in [STEP_CONTROLLER0, STEP_CONTROLLER1]:
                CK_RET(node_n(n).wait_for_node())
            CK_RET(STX.wait_for_host_node_enabled(
                node_0, n, 30))
            node_n(n).set_status(NODE.NODE_UNLOCKED)

        if step == STEP_CONTROLLER1:
            copy_provision_script_to_node(node_n(node_list[0]))
        elif step == STEP_STORAGE:
            STX.stx_after_provision_storage(node_0)
        elif step == STEP_COMPUTE:
            STX.stx_after_provision_compute(node_0,
                dplmnt['storage_num'] > 0 or dplmnt['system_mode'] == 'multi_aio')

    FINISH_STEP(step)

#########################################
# Deployment Step STEP_APP_APPLY:
#   Bring up containerized services
#   Provider/tenant networking setup
#########################################

if RUN_STEP(STEP_APP_APPLY):

    CK_RET(STX.wait_for_host_node_available(
        node_0, NODE.HOSTNAME_CONTROLLER0, 30))

    # Issue: platform-integ-apps is found at "uploaded" status but not "applied" yet.
    STX.stx_wait_for_platform_integ_app(node_0)

    if dplmnt["system_mode"] == 'simplex':
        CK_RET(node_0.ssh("ceph osd pool ls | xargs -i ceph osd pool set {} size 1",
            logfile=logfile("openstack.00_simplex_set_ceph_pool_replication.log")))

    if dplmnt['helm_charts_list']:
        for charts in dplmnt['helm_charts_list']:
            charts_filename = os.path.basename(charts)
            test_charts = os.path.join(dplmnt['testdir'], charts_filename)
            UTILS.copy_file_newname(charts, test_charts)

            appname = STX.stx_apply_application(node_0, helm_charts=test_charts)

            if appname == "stx-openstack":
                node1 = None if dplmnt['system_mode'] == "simplex" \
                             else dplorch["nodes"][get_node_by_step(STEP_CONTROLLER1)[0]]
                STX.stx_openstack_provision(
                    node_0,
                    dplmnt["openstack_root"],
                    dplmnt["adminpassword"],
                    node1=node1)

    STX.get_pod_logs(node_0, logname="pod_logs_success")
    LOG.Info("# Controller0: Finished to bring up containerized services")

FINISH_STEP(STEP_APP_APPLY)

#########################################
# Deployment Finished
#########################################


