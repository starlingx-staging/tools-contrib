#!/usr/bin/env python

import os
import ConfigParser
import argparse
import shutil
import time
from datetime import datetime
from subprocess import *

from openstack_logcheck import *
import ectest.log as LOG

DEBUG = True

CurrPath = os.path.join(os.path.abspath(os.getcwd()))

dplmnt = {}
##########################
### Config
dplmnt["config"] = "container.conf"
dplmnt["controller_floating_ip"] = "10.10.10.2"
dplmnt["controller0_ip"] = "10.10.10.3"
dplmnt["controller1_ip"] = "10.10.10.4"
dplmnt["username"] = "wrsroot"
dplmnt["openstack_root"] = "openstack_helm"
dplmnt["adminpassword"] = "Local.123"
dplmnt["password"] = "Local.123"  ## if autoiso, just use wrsroot as password
dplmnt["basedir"] = CurrPath

# controller config
dplmnt["config_complete"] = "/etc/platform/.initial_config_complete"

#########################
##Structure the Arg Parser
desc = "StarlingX Auto Deployment - Containerized"
parser = argparse.ArgumentParser(description=desc, version='%(prog)s 1.01')
# positional arguments
parser.add_argument('iso',
    help="The ISO file to deploy", type=str)
parser.add_argument('helm_charts',
    help="The helm charts for stx-openstack application",
    type=str)
# optional arguments
parser.add_argument('--start',
    help="start point: "
         "1: create vbox and do config_controller; "
         "2: setup and provision controllers; "
         "3: setup compute nodes; "
         "4: provision compute nodes; "
         "5: bring up openstack containerized services; "
         "6: all deployment finished (run with --log to get system logs only)",
    default=1, type=int, choices=[1,2,3,4,5,6])
parser.add_argument('--log', help="Get controller/compute system logs.",
    action="store_true")
parser.add_argument('--numa',
    help="Set VM with numa enabling", action="store_true")
parser.add_argument('--method',
    help="Create KVM or VirtualBox for deployment test.",
    type=str,
    choices=["kvm"], # removed "vbox" because vbox is not available now.
    default="kvm")
parser.add_argument('--autoiso', help="Modify ISO file for auto install.",
    action="store_true")
# only a debug feature.
parser.add_argument('--debugcode',
    help="Give you the chance to modify code after Controller0 install finished.",
    action="store_true",
    default=False)
# features for automation (higher priority than config file)
parser.add_argument('--system_mode',
    help="System Mode: simplex, duplex or multi-node.",
    type=str, choices=['simplex', 'duplex', 'multi'])
parser.add_argument('--compute_num',
    help="Number of compute nodes. (controller number is not configurable,"
         "and is determined by system mode.)",
    type=int, choices=[1,2,3,4])
parser.add_argument('--logbase',
    help="Base Dir for Logs",
    type=str)
parser.add_argument('--virtimg_dir',
    help="Dir to place kvm images for controllers and computes.",
    type=str)
parser.add_argument('--prefix',
    help="Prefix name of the vms",
    type=str)

args = parser.parse_args()

if args.autoiso:
    dplmnt["password"] = "wrsroot"

dplmnt["iso"] = os.path.abspath(args.iso)
dplmnt["isoname"] = os.path.basename(args.iso)
dplmnt["helm_charts"] = os.path.abspath(args.helm_charts)

if args.system_mode:
    dplmnt["system_mode"] = args.system_mode
if args.compute_num:
    dplmnt["compute_num"] = args.compute_num
if args.logbase:
    dplmnt["basedir"] = os.path.abspath(args.logbase)
    if not os.path.exists(dplmnt["basedir"]):
        os.makedirs(dplmnt["basedir"])
if args.virtimg_dir:
    dplmnt['vm_img_location'] = os.path.abspath(args.virtimg_dir)
    if not os.path.exists(dplmnt["vm_img_location"]):
        # Must provide a location to place vm images
        LOG.Error("VM Image Folder: %s not existing!" % dplmnt['vm_img_location'])
        exit(1)
if args.prefix:
    dplmnt['vm_prefix_name'] = args.prefix

if args.numa:
    dplmnt["numa"] = '-numa'
else:
    dplmnt["numa"] = ''

## Config Virtual Machine used for the deployment test
#     - Qemu/KVM
#     - Vbox
dplmnt["method"] = args.method
def iskvm():
    return dplmnt["method"] == "kvm"
def isvbox():
    return dplmnt["method"] == "vbox"
if isvbox():
    LOG.Info("!!! WARNING !!!: vbox is not tested in this version of script.")

###################
# Sub Functions   #
###################

# Tester Friendly
def wait_minutes(mins):
    ONE_MINUTE = 60
    for i in range(mins):
        left = (mins - i) * ONE_MINUTE
        print("Waiting ... %s seconds left\r" % str(left))
        if not DEBUG:
            time.sleep(ONE_MINUTE)

# Test Exiting
def exit_with_failure():
    log_failure()
    exit(1)

def exit_with_success():
    exit(0)

# Running Linux CMD
expect_script = "expect_script.sh"
temp_testscript = "test.sh"
temp_testresult = "testresult"

def cmdhost(cmd, cwd=None, logfile=None, silent=False):
    realcmd = cmd
    LOG.Info("Start to run \"%s\"" % cmd, silent=silent)
    if DEBUG:
        realcmd = "echo \"%s\"" % cmd
    result = ""
    retval = 0

    if cwd != None:
        os.chdir(cwd)
    try:
        result = check_output(realcmd, shell = True).splitlines()
    except CalledProcessError as ecp:
        LOG.Error("ERROR: failed to run \"%s\": returned %s %s" % (cmd, ecp.returncode, ecp.output))
        retval = ecp.returncode
    except Exception as error:
        LOG.Error("ERROR: failed to run \"%s\": %s" % (cmd, error))
        LOG.Error("")
        retval = -1

    # Remove license headers in the log.
    has_license_header = False
    for r in result:
        if r.lower().find("this is a private computer system") >= 0:
            has_license_header = True
            break
    if has_license_header:
        start_id = 0
        for r in result:
            start_id += 1
            if r.lower().find(" password:") >= 0:
                break
        result = result[start_id-1:]
        result = "\n====== Log on the node: ======\n%s\n" % "\n".join(result)
    else:
        result = "\n====== Log on host: ======\n%s\n" % "\n".join(result)

    if logfile != None:
        with open(logfile, "w") as f:
            f.write(result)
    if cwd != None:
        os.chdir(CurrPath)

    LOG.Info("Finished \"%s\": %s" % (cmd, result), silent=silent)
    LOG.Info("", silent=silent)
    return retval

def cmdexpect(cmd, logfile=None, silent=False):
    LOG.Info("CMD with expect: \"%s\"" % cmd, silent=silent)
    with open(temp_testscript, 'w') as wd:
        wd.write("%s\n" % cmd)
        wd.write("echo $? > %s\n" % temp_testresult)
    cmdhost("chmod +x %s" % temp_testscript, silent=True)
    expcmd = "./%s %s" % (expect_script, dplmnt["password"])
    retval = cmdhost(expcmd, logfile=logfile, silent=silent)
    if 0 == retval:
        if DEBUG:
            return 0
        with open(temp_testresult, 'r') as f:
            result = f.readline()
            LOG.Info("CMD finished with return code: %s" % result, silent=silent)
            if result:
                return int(result)
            else:
                return -1
    else:
        return retval

def cmdssh(cmd, user, ip, logfile=None, silent=False, noflag=False):
    LOG.Info("Start to run CMD \"%s\" via %s@%s" % (cmd, user, ip), silent=silent)
    sshcmd = 'ssh -t %s@%s \'%s\'' % (user, ip, cmd)
    if noflag:
        sshcmd = 'ssh %s@%s \'%s\'' % (user, ip, cmd)
    return cmdexpect(sshcmd, logfile, silent=silent)

def cmdssh_ctrl0(cmd, logfile=None, silent=False, noflag=False):
    return cmdssh(cmd,
        dplmnt["username"],
        dplmnt["controller0_ip"],
        logfile=logfile, silent=silent, noflag=noflag)

def cmdos(cmd, user, ip, logfile=None, silent=False, noflag=False):
    openstack_cmd = 'source /etc/platform/openrc; %s' % cmd
    return cmdssh(openstack_cmd, user, ip, logfile, silent=silent)

def cmdos_ctrl0(cmd, logfile=None, silent=False, noflag=False):
    return cmdos(cmd,
        dplmnt["username"],
        dplmnt["controller0_ip"],
        logfile=logfile, silent=silent, noflag=noflag)

def cmdos_ctrlfloat(cmd, logfile=None, silent=False, noflag=False):
    return cmdos(cmd,
        dplmnt["username"],
        dplmnt["controller_floating_ip"],
        logfile=logfile, silent=silent, noflag=noflag)

def exec_script_on_host(host, script, logname=None):
    hostip = host + "_ip"
    words = script.strip().split()
    script_file = words[0]
    if words[0] == "sudo":
        script_file = words[1]
    if not os.path.exists(os.path.join("needcopy", script_file)):
        LOG.Error("Script Not Existing!! %s" % script_file)
        exit_with_failure()
    if not logname:
        logname = os.path.splitext(os.path.basename(script_file))[0] + ".log"
    check_return(cmdssh(script,
        dplmnt["username"],
        dplmnt[hostip],
        logfile=logfile(logname)))
    LOG.Info("# %s: Finished to run \'%s\'" % (host, script))

def get_system_logs():
    cmdssh("rm ~/system_logs -rf; mkdir ~/system_logs",
           dplmnt["username"],
           dplmnt["controller0_ip"],
           silent=True)

    sshcmds = []
    sshcmds.append("cd ~/system_logs")
    sshcmds.append("sudo tar -zcf controller_logs.tgz /var/log")
    cmdssh("; ".join(sshcmds),
           dplmnt["username"],
           dplmnt["controller0_ip"],
           silent=True,
           logfile=logfile("get_system_log.log"))

    if dplmnt["host_list"]:
        for node in dplmnt["host_list"]:
            if 0 != cmdssh_ctrl0("ping %s -c 1" % node["ip"], silent=True):
                LOG.Warning("Host %s cannot be reached, no system log fetched." % node['ip'])
                continue

            cmdssh_ctrl0('scp -r ~/get_system_log.sh %s:~/' % node["ip"], silent=True)
            cmdssh_ctrl0("./expect_run_sudoscript.sh %s %s %s;" % (dplmnt["password"], node["ip"], "get_system_log.sh"),
                logfile=logfile("4.2_ovs_agent_on_compute.log"), silent=True)
            cmdssh_ctrl0('scp -r %s:~/system_logs/compute_logs.tgz ~/system_logs/%s_logs.tgz' % (node["ip"], node["hostname"])
                , silent=True)
    cmdexpect('scp -r %s@%s:~/system_logs %s' % (dplmnt["username"], dplmnt["controller0_ip"], dplmnt["testdir"]), silent=True)
    cmdssh_ctrl0('sudo sm-dump', logfile=logfile("sm-dump.log"))
    LOG.Info("Please check the full system log under %s." % dplmnt["testdir"])

# Check result
def log_failure():
    global dplmnt
    dplmnt['status'] = "Fail"
    dplmnt['endtime'] = datetime.now().strftime('%H:%M:%S')
    LOG.Error("#### ERROR: failed at %s ####" % dplmnt['endtime'])

def check_return(result):
    if result:
        get_system_logs()
        exit_with_failure()

def logfile(name):
    return os.path.join(dplmnt["testdir"], name)

# system level functions
def copy_folder(src, dst):
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

def copy_file(srcfile, dstfolder):
    filename = os.path.basename(srcfile)
    dstfile = os.path.join(dstfolder, filename)
    if os.path.exists(srcfile):
        if not os.path.exists(dstfolder):
            os.makedirs(dstfolder)
        elif os.path.exists(dstfile):
            os.remove(dstfile)
        shutil.copy2(srcfile, dstfile)

def copy_file_newname(srcfile, dstfile):
    filename = os.path.basename(srcfile)
    dstfolder = os.path.dirname(dstfile)
    if os.path.exists(srcfile):
        if not os.path.exists(dstfolder):
            os.makedirs(dstfolder)
        elif os.path.exists(dstfile):
            os.remove(dstfile)
        shutil.copy2(srcfile, dstfile)

#############
# KVM/Vbox related
def get_virt_MAC(vm_name, bridge_name):
    cmdhost("sudo virsh domiflist %s" % vm_name, logfile=logfile("tmp.log"))
    try:
        MAC = find_words_noempty(
            get_lines(logfile("tmp.log"), bridge_name)[0], " ")[4]
    except Exception:
        return None
    return MAC

def start_vm(name):
    if isvbox():
        cmdhost("VBoxManage startvm %s --type headless" % name)
    elif iskvm():
        cmdhost("sudo virsh start %s" % name)


##############
# hosts
def get_nicname(mac, ip):
    logfilename="%s_nic_name.log" % ip
    cmdssh("grep %s /etc/udev/rules.d/70-persistent-net.rules" % mac,
           dplmnt["username"],
           ip,
           logfile=logfile(logfilename))

    nicname=""
    reg=re.compile('.*NAME="(?P<nic_name>[^"]*)"',re.M)
    with open(logfile(logfilename), 'r') as cfg:
        for line in cfg:
            regMatch  = reg.match(line)
            if regMatch:
                nicname = regMatch.group('nic_name')
    return nicname

def wait_for_node(minutes, node_ip):
    if DEBUG: return 0
    for i in range (minutes * 6):
        if 0 == cmdhost("ping %s -c 1" % node_ip, silent=True):
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_controller0_service(minutes):
    if DEBUG: return 0
    for i in range (minutes * 6):
        if 0 == cmdssh_ctrl0("sudo sm-dump",
                   silent=True,
                   logfile=logfile("tmp.log")) and is_sm_dump_all_enabled(logfile("tmp.log")):
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_host_node(ip, minutes):
    if DEBUG: return 0
    for i in range (minutes * 6):
        if 0 == cmdssh_ctrl0("ping %s -c 1" % ip, silent=True):
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_host_node_online(hostname, minutes):
    if DEBUG: return 0
    for i in range(minutes * 6):
        check_return(cmdos_ctrlfloat('system host-list', logfile=logfile("tmp.log"), silent=True))
        host_status = get_host_list_status(logfile("tmp.log"), hostname)
        if "availability" in host_status and (host_status["availability"] == "online" or host_status["availability"] == "available"):
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_host_node_available(hostname, minutes):
    if DEBUG: return 0
    for i in range(minutes * 6):
        check_return(cmdos_ctrlfloat('system host-list', logfile=logfile("tmp.log"), silent=True))
        host_status = get_host_list_status(logfile("tmp.log"), hostname)
        if "availability" in host_status and host_status["availability"] == "available":
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_host_node_lock_unlock(hostname, status, minutes):
    if DEBUG: return 0
    for i in range(minutes * 6):
        check_return(cmdos_ctrlfloat('system host-list', logfile=logfile("tmp.log"), silent=True))
        host_status = get_host_list_status(logfile("tmp.log"), hostname)
        if "administrative" in host_status and (host_status["administrative"] == status):
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_controller_active(hostname, minutes):
    if DEBUG: return 0
    for i in range(minutes * 6):
        cmdos_ctrlfloat('system host-show %s' % hostname,
            logfile=logfile("tmp.log"), silent=True)
        if get_lines(logfile("tmp.log"), "Controller-Active"):
            return 0
        time.sleep(10)
    exit_with_failure()

def wait_for_vm_alive(vmname, minutes):
    if DEBUG: return 0
    for i in range (minutes * 6):
        if 0 != cmdos_ctrl0("openstack server list", logfile=logfile("tmp.log"), silent=True):
            LOG.Error("ERROR: failed to get status of %s" % vmname)
            return 1
        dplmnt["vms"][vmname] = get_vm_structure(logfile("tmp.log"), vmname)
        if dplmnt["vms"][vmname]["Status"] == "ACTIVE":
            return 0
        if dplmnt["vms"][vmname]["Status"] == "ERROR":
            LOG.Error("ERROR: vm %s status error." % vmname)
            return 1
        time.sleep(10)
    exit_with_failure()

def wait_for_ctn_app_status(appname, minutes, expected):
    if DEBUG: return 0
    for i in range (minutes * 6):
        if 0 != cmdos_ctrl0("system application-list | grep %s" % appname,
                            logfile=logfile("tmp.log")):
            LOG.Error("ERROR: failed to get status of application-list")
            return "failed"

        status = get_application_status(logfile("tmp.log"), appname)
        if status != expected:
            return status

        time.sleep(10)

    exit_with_failure()

def wait_for_compute_ceph_monitor(minutes):
    if DEBUG: return 0
    for i in range (minutes * 6):
        if 0 != cmdos_ctrlfloat("system ceph-mon-list", logfile=logfile("tmp.log"), silent=True):
            LOG.Error("ERROR: failed to get status of ceph monitors")
            return 1

        if "configured" == get_ceph_monitor_status(logfile("tmp.log"), "compute-0"):
            return 0

        time.sleep(10)

    exit_with_failure()


#############
def get_ctn_related_status(hostname, hostip, logfile=None, withceph=False):
    cmds = []
    cmds.append("system host-list")
    if dplmnt['system_mode'] != "multi" or withceph == True:
        cmds.append("ceph -s")
    #cmds.append("kubectl -n kube-system get po")
    cmds.append("sudo docker ps -a")
    cmdos(";".join(cmds),
          dplmnt["username"],
          hostip,
          logfile=logfile)

def check_ceph(hostname, hostip):
    if 0 != cmdos("ceph -s",
                  dplmnt["username"],
                  hostip,
                  logfile=logfile("tmp.log")):
        LOG.Error("ERROR: failed to get ceph status on hostname.")
        return -1

    lines = get_lines(logfile("tmp.log"), "health")
    for line in lines:
        words = line.strip().split()
        if len(words) >= 2:
            if words[1].startswith("HEALTH_OK"): return 0
            if words[1].startswith("HEALTH_ERR"): return -1
            if words[1].startswith("HEALTH_WARN"): return 1
    return -1


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
# Note: If running with KVM, we only use the names from the config file,
#   the system configs follow the libvirt/*.xml.
#
dplmnt['controller_config'] = {}
dplmnt['compute_config'] = {}
with open(dplmnt["config"], 'r') as cfg:
    for line in cfg:
        if line.startswith("TIC_SYSTEM_MODE="):
            if "system_mode" not in dplmnt.keys():
                dplmnt["system_mode"] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER_NUM="):
            dplmnt['controller_num'] = int(line.split("=")[1].strip())
        if line.startswith("TIC_COMPUTE_NUM="):
            if "compute_num" not in dplmnt.keys():
                dplmnt['compute_num'] = int(line.split("=")[1].strip())
        if line.startswith("VM_PREFIX_NAME="):
            if 'vm_prefix_name' not in dplmnt.keys():
                dplmnt['vm_prefix_name'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER_CPUS"):
            dplmnt['controller_config']['cpus'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER_MEM"):
            dplmnt['controller_config']['mem_gib'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER_DISK1"):
            dplmnt['controller_config']['disk1_gib'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER_DISK2"):
            dplmnt['controller_config']['disk2_gib'] = line.split("=")[1].strip()
        if line.startswith("TIC_COMPUTE_CPUS"):
            dplmnt['compute_config']['cpus'] = line.split("=")[1].strip()
        if line.startswith("TIC_COMPUTE_MEM"):
            dplmnt['compute_config']['mem_gib'] = line.split("=")[1].strip()
        if line.startswith("TIC_COMPUTE_DISK1"):
            dplmnt['compute_config']['disk1_gib'] = line.split("=")[1].strip()
        if line.startswith("TIC_COMPUTE_DISK2"):
            dplmnt['compute_config']['disk2_gib'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER_FLOATING"):
            dplmnt['controller_floating_ip'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER0_IP"):
            dplmnt['controller0_ip'] = line.split("=")[1].strip()
        if line.startswith("TIC_CONTROLLER1_IP"):
            dplmnt['controller1_ip'] = line.split("=")[1].strip()
        if line.startswith("NTP_SERVERS"):
            dplmnt['ntp_servers'] = line.split("=")[1].strip()
        if line.startswith("DOCKER_PROXY"):
            dplmnt['docker_proxy'] = line.split("=")[1].strip().lower()
        if line.startswith("HELM_CHARTS"):
            if "helm_charts" not in dplmnt.keys():
                dplmnt['helm_charts'] = os.path.abspath(line.split("=")[1].strip())
        if line.startswith("VM_IMG_LOCATION"):
            if "vm_img_location" not in dplmnt.keys():
                dplmnt['vm_img_location'] = os.path.abspath(line.split("=")[1].strip())

if dplmnt["system_mode"] not in ("multi", "simplex", "duplex"):
    LOG.Error("##### Error: system mode wrong")
    exit_with_failure()

if "helm_charts" not in dplmnt.keys() or not os.path.exists(dplmnt['helm_charts']):
    LOG.Error("##### Error: helm charts not found.")
    exit_with_failure()

if dplmnt["system_mode"] == "duplex":
    dplmnt["controller_num"] = 2
    dplmnt["compute_num"] = 0
elif dplmnt["system_mode"] == "simplex":
    dplmnt["controller_num"] = 1
    dplmnt["compute_num"] = 0
else:
    # For containerized version multi-node, there must have 2 controllers.
    dplmnt["controller_num"] = 2
    if dplmnt["compute_num"] < 1: dplmnt["compute_num"] = 1

dplmnt['controller_list'] = []
for i in range(dplmnt['controller_num']):
    dplmnt['controller_list'].append("%s_%s-controller-%d" % (
                                     dplmnt['vm_prefix_name'],
                                     dplmnt['system_mode'],
                                     i))

dplmnt['hostname_list'] = []
dplmnt['hostname_list'].append('controller-0')
if dplmnt['controller_num'] == 2:
    dplmnt["hostname_list"].append('controller-1')
dplmnt['computename_list'] = []
for i in range(dplmnt['compute_num']):
    dplmnt['computename_list'].append("%s_%s-compute-%d" % (
                                      dplmnt['vm_prefix_name'],
                                      dplmnt['system_mode'],
                                      i))
    dplmnt["hostname_list"].append('compute-%d' % i)

dplmnt["host_list"] = []

dplmnt['cc_config'] = None
def generate_controller_config():
    # generate config_controller config file according to the settings
    src_config_file = os.path.join(
        CurrPath,
        "controllerconfig",
        "%s.conf" % dplmnt["system_mode"])
    config_file = os.path.join(dplmnt["testdir"], "cc.conf")
    copy_file_newname(src_config_file, config_file)

    cmds = []
    config_k8s = os.path.join(
        CurrPath,
        "controllerconfig",
        "k8s.conf")
    cmds.append("cat %s >> %s" % (config_k8s, config_file))
    if dplmnt["docker_proxy"].startswith('y'):
        config_proxy = os.path.join(
            CurrPath,
            "controllerconfig",
            "proxy.conf")
        cmds.append("cat %s >> %s" % (config_proxy, config_file))
    cmds.append("sed -i 's/%s/%s/g' %s"
        % ("RELEASE_VERSION_TO_SET", dplmnt['release_version'], config_file))
    cmds.append("sed -i 's/%s/%s/g' %s"
        % ("ADMIN_PASSWORD_TO_SET", dplmnt['adminpassword'], config_file))

    # Modify OAM IPs
    cmds.append("sed -i 's/%s/%s/g' %s"
        % ("CONTROLLER_FLOATING_TO_SET", dplmnt['controller_floating_ip'], config_file))
    cmds.append("sed -i 's/%s/%s/g' %s"
        % ("CONTROLLER0_OAM_TO_SET", dplmnt['controller0_ip'], config_file))
    cmds.append("sed -i 's/%s/%s/g' %s"
        % ("CONTROLLER1_OAM_TO_SET", dplmnt['controller1_ip'], config_file))
    cmdhost(";".join(cmds))

    dplmnt['cc_config'] = config_file

dplmnt['nic_namemap'] = {
    'virbr1': 'ens6',
    'virbr2': 'ens7',
    'virbr3': 'eth1000',
    'virbr4': 'eth1001'
}

def get_nic_namemap():
    # Run this function after Controller0 up and configured.
    # TODO: check if controller0 is under right status.
    for br in dplmnt['nic_namemap'].keys():
        MAC = get_virt_MAC(dplmnt['controller_list'][0], br)
        NIC_name = get_nicname(MAC, dplmnt["controller0_ip"])
        if NIC_name:
            dplmnt['nic_namemap'][br] = NIC_name
    LOG.Info("NIC Name Map: %s" % str(dplmnt['nic_namemap']))

def generate_provision_script():
    get_nic_namemap()

    script_folder = os.path.join(dplmnt["testdir"], 'needcopy')
    copy_folder("needcopy", script_folder)

    cmds = []
    cmds.append("sed -i 's/%s/%s/g' %s/ctn_provisioning/*"
        % ("ens6", dplmnt['nic_namemap']['virbr1'], script_folder))
    cmds.append("sed -i 's/%s/%s/g' %s/ctn_provisioning/*"
        % ("eth1000", dplmnt['nic_namemap']['virbr3'], script_folder))
    cmds.append("sed -i 's/%s/%s/g' %s/ctn_provisioning/*"
        % ("eth1001", dplmnt['nic_namemap']['virbr4'], script_folder))
    cmdhost(";".join(cmds))

    return script_folder

LOG.Info("##########################")
LOG.Info("# Start to deploy %s" % dplmnt["iso"])
LOG.Info("#     helm charts %s" % dplmnt["helm_charts"])
LOG.Info("# start from Step %s" % args.start)
LOG.Time("<<<Deployment Started>>>")
LOG.Info("# Deployment method: %s with %s" % (dplmnt["system_mode"], dplmnt["method"]))
LOG.Info("# Num of Controllers: %d" % dplmnt["controller_num"])
for i in range(dplmnt['controller_num']):
    LOG.Info("#   %s @ %s"
        % (dplmnt['controller_list'][i], [dplmnt["controller0_ip"], dplmnt["controller1_ip"]][i]))
if dplmnt['system_mode'] != "simplex":
    LOG.Info("#   Floating IP @ %s" % dplmnt["controller_floating_ip"])
LOG.Info("# Num of Computers: %d" % dplmnt["compute_num"])
for c in dplmnt['computename_list']:
    LOG.Info("#   %s" % c)
LOG.Info("# System wrsroot password: %s" % dplmnt["password"])
LOG.Info("# Openstack root user: %s" % dplmnt["openstack_root"])
LOG.Info("# Openstack admin password: %s" % dplmnt['adminpassword'])
LOG.Info("#")
LOG.Info("#")
LOG.Info(str(dplmnt), silent=True)


########################################
# Check for preparation:
cmdhost("./prepare.sh")

###########################################
# Remove the old known host.
cmdhost('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s' % dplmnt["controller_floating_ip"])
cmdhost('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s' % dplmnt["controller0_ip"])
cmdhost('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s' % dplmnt["controller1_ip"])

########################################
# Deployment Step 1:
#   1. create vbox/libvirt virtual machines to do the deployment.
#   2. install the iso to controller0
#   3. config_controller
#########################################

if args.start <= 1:
    ##########################
    # deployment preparation
    LOG.Info("#######################")
    LOG.Info("# Step 1 Started.")

    #########################################
    # prepare the iso file:
    #   modify to run the installation automatically
    newiso = os.path.join(dplmnt["testdir"], dplmnt["isoname"])
    if args.autoiso:
        kvm_cmds = []
        kvm_cmds.append("sed -e 's/INIT_IP_TO_SET/%s/' controller0_network.txt "
                            " > test_controller0_network.txt" % dplmnt['controller0_ip'])
        if dplmnt["system_mode"] != "multi":
            kvm_cmds.append("sed -e 's/default 0/ default 3/' rebuild_iso.sh "
                            " > rebuild_iso_allinone.sh")
            kvm_cmds.append("chmod a+x rebuild_iso_allinone.sh")
            kvm_cmds.append("./rebuild_iso_allinone.sh %s %s" % (dplmnt["iso"], newiso))
            kvm_cmds.append("rm -f rebuild_iso_allinone.sh");
        else:
            kvm_cmds.append("./rebuild_iso.sh %s %s" % (dplmnt["iso"], newiso))
        cmdhost(";".join(kvm_cmds))

        # Get real release version from the iso
        if DEBUG:
            dplmnt["release_version"] = "19.01"
        else:
            version = None
            version_lines = get_lines("./isolinux/upgrades/version", "ERSION")
            if version_lines:
                words = version_lines[0].split("=")
                if len(words) >= 2:
                    version = words[1].strip()
            if version:
                dplmnt["release_version"] = version
            else:
                LOG.Error("====== ERROR: Rlease version not found in the given ISO file.")
                exit_with_failure()

        generate_controller_config()

    else:
        newiso = dplmnt["iso"]


    #########################################
    # create vms for deployment
    if isvbox():
        # Not tested in this version of script.
        pass

    elif iskvm():
        LOG.Info("running with kvm")
        LOG.Info("May need to type the Host Password:", silent=True)
        kvm_cmds = []
        kvm_cmds.append("cd libvirt")
        if not os.path.exists("libvirt/vms"):
            kvm_cmds.append("mkdir vms")
        kvm_cmds.append("./setup_if.sh")

        # Controller0
        cmd = "./setup_vm.sh %s %s %s %s %s %s %s %s" % (
              "ctn_controller0",
              dplmnt['controller_list'][0],
              dplmnt['controller_config']['mem_gib'],
              dplmnt['controller_config']['cpus'],
              dplmnt['controller_config']['disk1_gib'],
              dplmnt['controller_config']['disk2_gib'],
              newiso,
              dplmnt['vm_img_location'])
        kvm_cmds.append(cmd)

        # Controller1 (no iso)
        if dplmnt["controller_num"] == 2:
            cmd = "./setup_vm.sh %s %s %s %s %s %s %s %s" % (
                  "ctn_controller1",
                  dplmnt['controller_list'][1],
                  dplmnt['controller_config']['mem_gib'],
                  dplmnt['controller_config']['cpus'],
                  dplmnt['controller_config']['disk1_gib'],
                  dplmnt['controller_config']['disk2_gib'],
                  "noiso",
                  dplmnt['vm_img_location'])
            kvm_cmds.append(cmd)

        # Computers
        for i in range(dplmnt['compute_num']):
            cmd = "./setup_vm.sh %s %s %s %s %s %s %s %s" % (
                  "ctn_compute",
                  dplmnt['computename_list'][i],
                  dplmnt['compute_config']['mem_gib'],
                  dplmnt['compute_config']['cpus'],
                  dplmnt['compute_config']['disk1_gib'],
                  dplmnt['compute_config']['disk2_gib'],
                  "noiso",
                  dplmnt['vm_img_location'])
            kvm_cmds.append(cmd)

        kvm_cmds.append("./exec_vm.sh %s" % dplmnt['controller_list'][0])
        kvm_cmds.append("sudo virt-manager")

        cmdhost("; ".join(kvm_cmds), logfile=logfile("1.1_create_kvms.log"))

    else:
        LOG.Error("===== ERROR: Non-supported method to deploy (only vbox or kvm supported).")
        exit_with_failure()

    ###########################################
    ## Wait until iso installation finished and config_controller finished
    if not args.autoiso:
        while True:
            LOG.Info("Waiting for manual steps finished .......")
            LOG.Info("Step 1: Wait until iso installation finished.")
            LOG.Info("Step 2: Logging with wrsroot and change the password as \"%s\"" % dplmnt["password"])
            LOG.Info("Step 3: Run \"sudo config_controller \" on controller")
            LOG.Info("Step 4: Wait until config_controller finished")
            manualsteps = raw_input("All these steps successfully finished? (yes|no)")
            if manualsteps == "no":
                exit_with_failure()
            elif manualsteps == "yes":
                LOG.Time('Manual Steps Finished')
                break
    else:
        # Wait for controller0 installation
        wait_minutes(10)
        wait_for_node(15, dplmnt["controller0_ip"])
        LOG.Info("# Finished ISO installation.")

        check_return(cmdexpect('scp -r %s %s@%s:~/'
                                % (dplmnt['cc_config'],
                                   dplmnt["username"],
                                   dplmnt["controller0_ip"])))

        # TODO: get NIC name and put the name into config file for LOGICAL_INTERFACE_1.
        LOG.Info("# Run config_controller with config file %s" % dplmnt['cc_config'])

        ## DEBUG USAGE: modify code before config_controller.
        while args.debugcode:
            LOG.Info("Waiting for code modification .......")
            manualsteps = raw_input("finished? (yes|no)")
            if manualsteps == "yes":
                LOG.Time('Code modified')
                break

        # To run config_controller on host at background, use nohup and re-direct the output.
        # ssh -t flag will impact the result, so use noflag.
        cmdssh_ctrl0("nohup sudo config_controller"
               " --config-file ~/%s"
               " --allow-ssh"
               " > ~/cc.log 2>&1 & " % os.path.basename(dplmnt['cc_config']),
               logfile=logfile("1.2_config_controller_cmd.log"),
               noflag=True)

        wait_minutes(1)

        cmdexpect('scp -r %s@%s:%s %s'
            % (dplmnt["username"], dplmnt["controller0_ip"], "/tmp/cgcs_config",
                logfile("1.2_controller_config.txt")))
        cmdexpect('scp -r %s@%s:%s %s'
            % (dplmnt["username"], dplmnt["controller0_ip"], "/tmp/config/cgcs_config",
                logfile("1.2_controller_config_config.txt")))

        lose_temper = 50
        for i in range(lose_temper):
            wait_minutes(1)
            wait_for_node(15, dplmnt["controller0_ip"])

            ret = cmdssh_ctrl0("ls %s" % dplmnt["config_complete"], silent=True)
            if ret == 0:
                cmdssh_ctrl0("cat ~/cc.log", logfile("tmp.log"), silent=True)
                if get_lines(logfile("tmp.log"), "onfiguration was applied"):
                    break
            else:
                cmdssh_ctrl0("cat ~/cc.log", logfile("tmp.log"), silent=True)
                if get_lines(logfile("tmp.log"), "Failed") or i == lose_temper:
                    LOG.Error("##### ERROR: config_controller doesnt return good result.")
                    cmdssh_ctrl0('cat ~/cc.log',
                        logfile("1.3_config_controller_failed.log"))
                    get_system_logs()
                    exit_with_failure()
        # Config Controller completed.
        cmdssh_ctrl0('cat ~/cc.log', logfile("1.3_config_controller_succeeded.log"))

else:
    LOG.Info("#######################")
    LOG.Info("# Step 1 Skipped by user.")
    wait_for_node(15, dplmnt["controller0_ip"])
    check_return(cmdssh_ctrl0("ls %s" % dplmnt["config_complete"], silent=True))

###########################################
# Copy provisioning scripts
script_folder = generate_provision_script()
check_return(cmdexpect('scp -r %s/* %s@%s:~/'
    % (script_folder, dplmnt["username"], dplmnt["controller0_ip"])))

check_return(cmdssh_ctrl0('sudo chmod +x *.sh; sudo chmod +x */*.sh', silent=True))
LOG.Time("Step 1 Finished")

# Run script to add wrsroot to no-password group
cmdssh_ctrl0("sudo ./sudo_nopwd.sh")

#########################################
# Deployment Step 2:
#   1. provisioning controller0.
#   2. unlock controller0.
#   3. if needed, setup controller1.
#########################################

if args.start <= 2:
    ###########################################
    # provision controller-0
    LOG.Info("#######################")
    LOG.Info("# Step 2 Started.")

    # Setup NTP servers
    if 'ntp_servers' in dplmnt.keys() and dplmnt['ntp_servers']:
        cmds = []
        cmds.append("system ntp-modify ntpservers=%s" % dplmnt['ntp_servers'])
        check_return(cmdos_ctrl0(";".join(cmds),
                                 logfile=logfile("2.00_setup_ntp_servers.log")))
        LOG.Info("# Controller0: Finished to setup ntp servers.")

    ###########################################
    # provision controller0

    if dplmnt['system_mode'] == 'multi':
        # Prepare host to run container
        exec_script_on_host("controller0",
            './ctn_provisioning/2.01_multi_prepare_host_to_run_container.sh')

        # Setup Ceph
        exec_script_on_host("controller0",
            './ctn_provisioning/2.02_multi_enable_ceph.sh')

        wait_minutes(1)
        get_ctn_related_status(dplmnt['controller_list'][0],
                               dplmnt["controller0_ip"],
                               logfile=logfile("2.03_multi_controller0_status_before_unlock.log"))
    else: # simplex or duplex
        # Config data interfaces
        exec_script_on_host("controller0",
            './ctn_provisioning/2.01_config_data_interfaces.sh')

        # Prepare host to run container
        exec_script_on_host("controller0",
            './ctn_provisioning/2.02_prepare_host_to_run_container.sh')

        # Setup partitions
        exec_script_on_host("controller0",
            './ctn_provisioning/2.03_setup_partitions.sh')

        # Setup Ceph
        exec_script_on_host("controller0",
            './ctn_provisioning/2.04_config_ceph.sh')
        if dplmnt["system_mode"] == 'simplex':
            exec_script_on_host("controller0",
                './ctn_provisioning/2.04-1_aio_sx_only_ceph_pool_replication.sh')

        wait_minutes(1)
        get_ctn_related_status(dplmnt['controller_list'][0],
                               dplmnt["controller0_ip"],
                               logfile=logfile("2.05_controller0_status_before_unlock.log"))

    ###########################################
    # unlock controller0 and wait until controller0 back again.
    check_return(cmdos_ctrl0('system host-unlock controller-0',
                             logfile=logfile("2.10_unlock_controller0.log")))
    wait_minutes(5)
    wait_for_node(15, dplmnt["controller0_ip"])

    wait_minutes(10)
    cmdhost('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s' % dplmnt["controller0_ip"])
    get_ctn_related_status(dplmnt['controller_list'][0],
                           dplmnt["controller0_ip"],
                           logfile=logfile("2.10-1_controller0_status_after_unlock.log"))
    LOG.Info("# Controller0: Finished to unlock.")

    if dplmnt["controller_num"] == 2:
        LOG.Info("# Controller1: start to config Controller1.")
        start_vm(dplmnt['controller_list'][1])
        wait_minutes(1)

        # Detect Controller1 on Controller0 and update its personality
        exec_script_on_host("controller0",
            './ctn_provisioning/2.20_check_for_controller_1.sh')

        controller1_name = dplmnt['controller_list'][1]

        # Wait for controller1 to be installed
        wait_minutes(10)
        wait_for_host_node_online("controller-1", 15)

        if dplmnt['system_mode'] == 'multi':
            # Config data interfaces for Controller1
            exec_script_on_host("controller0",
                './ctn_provisioning/2.21_multi_prepare_host_to_run_container_controller_1.sh')

            # Prepare host to run container for Controller1
            exec_script_on_host("controller0",
                './ctn_provisioning/2.22_multi_config_interfaces_controller_1.sh')

            get_ctn_related_status(dplmnt['controller_list'][0],
                                   dplmnt["controller0_ip"],
                                   logfile=logfile("2.23_multi_host_status_before_unlock_controller_1.log"))
        else: # duplex
            # Config data interfaces for Controller1
            exec_script_on_host("controller0",
                './ctn_provisioning/2.21_config_data_interface_controller_1.sh')

            # Prepare host to run container for Controller1
            exec_script_on_host("controller0",
                './ctn_provisioning/2.22_prepare_host_to_run_container_controller_1.sh')

            # Setup partitions for Controller1
            exec_script_on_host("controller0",
                './ctn_provisioning/2.23_setup_partitions_controller_1.sh')

            # Config Ceph for Controller1
            exec_script_on_host("controller0",
                './ctn_provisioning/2.24_config_ceph_controller_1.sh')

            get_ctn_related_status(dplmnt['controller_list'][0],
                                   dplmnt["controller0_ip"],
                                   logfile=logfile("2.25_host_status_before_unlock_controller_1.log"))

        ###########################################
        # unlock controller1 and wait until controller1 back again.
        check_return(cmdos_ctrl0('system host-unlock controller-1',
                            logfile=logfile("2.30_unlock_controller1.log")))
        wait_minutes(5)
        wait_for_node(15, dplmnt["controller1_ip"])

        wait_minutes(5)
        check_return(cmdexpect('scp -r %s/* %s@%s:~/'
            % (script_folder, dplmnt["username"], dplmnt["controller1_ip"])))

        get_ctn_related_status(dplmnt['controller_list'][0],
                            dplmnt["controller0_ip"],
                            logfile=logfile("2.31_host_status_after_unlock_controller_1.log"))
        LOG.Info("# Controller0: Finished to unlock Controller1.")

else:
    LOG.Info("#######################")
    LOG.Info("# Step 2 Skipped by user.")

LOG.Time("Step 2 Finished")

#########################################
# Deployment Step 3:
#   1. add compute nodes as hosts.
#   2. install the compute nodes.
#########################################

if args.start <= 3 and dplmnt["compute_num"] > 0:
    ###########################################
    # Add compute nodes as hosts
    LOG.Info("#######################")
    LOG.Info("# Step 3 Started.")

    ###########################################
    # launch the virtual machines of compute nodes,
    #  so that the controller will install the compute nodes via pxe.
    for vm in dplmnt["computename_list"]:
        start_vm(vm)
        wait_minutes(1)

    # Detect Computers and update its personality
    for computeid in range(dplmnt['compute_num']):
        node_id = computeid + 1 + dplmnt['controller_num']
        exec_script_on_host("controller0",
            './ctn_provisioning/3.0_multi_check_for_computers.sh %d %d' % (computeid, node_id),
            logname="3.0_multi_check_for_computers%d.log" % computeid)
    LOG.Info("# Controller0: Finished to modify Computer personality.")

    # Prepare hosts to run container
    check_return(cmdos_ctrl0('system host-list', logfile=logfile("3.0-1_host_list.log")))
    # get host list and add labels
    cmds = []
    for node in get_host_list(logfile("3.0-1_host_list.log"), "compute"):
        exec_script_on_host("controller0",
            './ctn_provisioning/3.1_multi_prepare_host_to_run_container_compute.sh %s' % node,
            logname="3.1_multi_prepare_host_to_run_container_%s.log" % node)
        cmds.append("system host-show %s" % node)
    check_return(cmdos_ctrl0(";".join(cmds), logfile=logfile("3.0-2_host_show.log")))
    # Get IPs of the compute nodes
    dplmnt["host_list"] = get_hosts_added(logfile("3.0-2_host_show.log"))
    LOG.Info("# Controller0: Finished to add labels for %s" % str(dplmnt["host_list"]))

    ###########################################
    ## Wait until the compute nodes up
    wait_minutes(10)
    # 1st chance
    for node in dplmnt["host_list"]:
        node["status"] = wait_for_host_node(node["ip"], 10)
    # 2nd chance
    for node in dplmnt["host_list"]:
        if node["status"] != 0:
            node["status"] = wait_for_host_node(node["ip"], 1)
            if node["status"] != 0:
                LOG.Error("ERROR: compute node cannot boot up.")
                exit_with_failure()

elif dplmnt["compute_num"] > 0:
    ###########################################
    # if the compute nodes installation step is skipped, need to get the compute ip with host-show.
    LOG.Info("#######################")
    LOG.Info("# Step 3 Skipped by user.")

    # Get IPs of the compute nodes
    check_return(cmdos_ctrlfloat('system host-list', logfile=logfile("3.0-1_host_list.log")))
    # get host list
    cmds = []
    for node in get_host_list(logfile("3.0-1_host_list.log"), "compute"):
        cmds.append("system host-show %s" % node)
    check_return(cmdos_ctrlfloat(";".join(cmds), logfile=logfile("3.0-2_host_show.log")))
    # get ips
    dplmnt["host_list"] = get_hosts_added(logfile("3.0-2_host_show.log"))
    LOG.Info("# Controller0: Finished to add labels for %s" % str(dplmnt["host_list"]))

else:
    LOG.Info("#######################")
    LOG.Info("# Step 3 Skipped because no computer node is needed.")

if dplmnt["compute_num"] > 0:
    get_ctn_related_status(dplmnt['controller_list'][0],
                           dplmnt["controller_floating_ip"],
                           logfile=logfile("3.9_host_status.log"))

LOG.Time("Step 3 Finished")

#########################################
# Deployment Step 4:
#   1. provision the compute nodes
#########################################

if args.start <= 4 and dplmnt["compute_num"] > 0:

    ###########################################
    # wait until the compute nodes online.
    LOG.Info("#######################")
    LOG.Info("# Step 4 Started.")

    for node in dplmnt["host_list"]:
        if wait_for_host_node_online(node['hostname'], 15) == 1:
            LOG.Error("ERROR: compute node %s offline." % node["hostname"])

    # Add the third Ceph monitor to a compute node
    exec_script_on_host("controller0",
        './ctn_provisioning/4.0_multi_add_ceph_monitor.sh')
    wait_for_compute_ceph_monitor(15)

    # Create the volume group for nova
    exec_script_on_host("controller0",
        './ctn_provisioning/4.1_multi_create_volumn_group_for_nova.sh')

    # Configure data interfaces for computes
    exec_script_on_host("controller0",
        './ctn_provisioning/4.2_multi_config_data_interfaces_for_compute.sh')

    # Setup the cluster-host interfaces on the computes to the management network
    exec_script_on_host("controller0",
        './ctn_provisioning/4.3_multi_config_cluster_interfaces_for_compute.sh')

    cmds = []
    for node in dplmnt["host_list"]:
        cmds.append("system host-unlock %s" % node['hostname'])
    check_return(cmdos_ctrl0(";".join(cmds),
                             logfile=logfile("4.4_unlock_computenodes.log")))
    wait_minutes(5)

    ###########################################
    ## Wait until the compute or controller-1 nodes up
    # 1st chance
    for node in dplmnt["host_list"]:
        node["status"] = wait_for_host_node(node["ip"], 10)
    # 2nd chance
    for node in dplmnt["host_list"]:
        if node["status"] != 0:
            node["status"] = wait_for_host_node(node["ip"], 1)
            if node["status"] != 0:
                LOG.Error("ERROR: host node cannot boot up.")
                exit_with_failure()
    # wait until the host nodes online.
    for node in dplmnt["host_list"]:
        if wait_for_host_node_online(node['hostname'], 5) == 1:
            LOG.Error("ERROR: host node %s offline." % node["hostname"])

    #############################################
    ## Add Ceph OSD to controllers
    LOG.Info("## Start to Add Ceph OSD to controllers")

    def add_ceph_osd(act_ctl, stb_ctl, log_head):
        check_return(cmdos_ctrlfloat('system host-lock %s' % stb_ctl,
                        logfile=logfile("%s_0_host-lock_%s.log" % (log_head, stb_ctl))))
        wait_for_host_node_lock_unlock(stb_ctl, "locked", 5)
        LOG.Info("# %s: Finished to Lock %s" % (act_ctl, stb_ctl))

        exec_script_on_host("controller_floating",
            './ctn_provisioning/4.5_multi_add_osd_to_controllers.sh %s' % stb_ctl,
            logname="%s_1_add_osd_to_%s.log" % (log_head, stb_ctl))
        LOG.Info("# %s: Finished to add osd to %s" % (act_ctl, stb_ctl))

        check_return(cmdos_ctrlfloat('system host-unlock %s' % stb_ctl,
                        logfile=logfile("%s_2_host-unlock_%s.log" % (log_head, stb_ctl))))
        wait_minutes(15)
        wait_for_host_node_available(stb_ctl, 5)
        LOG.Info("# %s: Finished to UnLock %s" % (act_ctl, stb_ctl))

        # Switch active controller to controller-1
        check_return(cmdos_ctrlfloat('system host-swact %s' % act_ctl,
                        logfile=logfile("%s_3_host-swact_%s.log" % (log_head, act_ctl))))
        LOG.Info("# %s: Finished to swact %s" % (act_ctl, act_ctl))
        cmdhost('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s' % dplmnt["controller_floating_ip"])

        wait_minutes(1)
        wait_for_controller_active(stb_ctl, 2)
        LOG.Info("# %s: Now Active Controller should be %s" % (stb_ctl, stb_ctl))

    add_ceph_osd("controller-0", "controller-1", "4.5-1")
    add_ceph_osd("controller-1", "controller-0", "4.5-2")

elif dplmnt["compute_num"] > 0:
    ###########################################
    # if the compute nodes installation step is skipped, need to get the compute ip with host-show.
    LOG.Info("#######################")
    LOG.Info("# Step 4 Skipped by user.")

else:
    LOG.Info("#######################")
    LOG.Info("# Step 4 Skipped because no computer node is needed.")


if dplmnt["compute_num"] > 0:
    get_ctn_related_status(dplmnt['controller_list'][0],
                           dplmnt["controller_floating_ip"],
                           logfile=logfile("4.9_host_status.log"),
                           withceph=True)

LOG.Time("Step 4 Finished")

#########################################
# Deployment Step 5:
#   1. Bring up containerized services
#   2. Provider/tenant networking setup
#########################################

if args.start <= 5:
    LOG.Info("#######################")
    LOG.Info("# Step 5 Started.")

    helm_charts = os.path.join(dplmnt['testdir'], "helm_charts_for_test.tgz")
    copy_file_newname(dplmnt['helm_charts'], helm_charts)
    check_return(cmdexpect('scp -r %s %s@%s:~/' % (helm_charts, dplmnt["username"], dplmnt["controller0_ip"])))

    def check_next_status(next_status, expected_status):
        if DEBUG: return
        if next_status != expected_status:
            LOG.Error("##### ERROR: Wrong status %s" % next_status)
            get_system_logs()
            exit_with_failure()

    app_name = "stx-openstack"
    check_return(cmdos_ctrl0("system application-upload %s %s" % (app_name, os.path.basename(helm_charts)),
                            logfile=logfile("5.0-1_application_upload.log")))
    next_status = wait_for_ctn_app_status(app_name, 20, "uploading")
    LOG.Info("# Finished to upload application %s, current status %s." % (app_name, next_status))
    check_next_status(next_status, "uploaded")

    check_return(cmdos_ctrl0("system application-list",
                            logfile=logfile("5.0-2_application_list.log")))

    check_return(cmdos_ctrl0("system application-apply %s" % app_name,
                            logfile=logfile("5.0-3_application_apply.log")))
    next_status = wait_for_ctn_app_status(app_name, 120, "applying")
    LOG.Info("# Finished to apply application %s, current status %s." % (app_name, next_status))
    check_next_status(next_status, "applied")

    LOG.Info("# Controller0: Finished to bring up containerized services")

    if dplmnt["system_mode"] == 'simplex':
        check_return(cmdssh_ctrl0("ceph osd pool ls | xargs -i ceph osd pool set {} size 1",
                            logfile=logfile("5.0-4_simplex_set_ceph_pool_replication.log")))

    # Verify cluster endpoints
    exec_script_on_host("controller0",
        'sudo ./ctn_provisioning/5.1_verify_cluster_endpoints.sh %s %s'
            % (dplmnt["openstack_root"], dplmnt["adminpassword"]))

    # Config provider networking for Stein
    exec_script_on_host("controller0",
        'sudo ./ctn_provisioning/5.2_provider_networking_stein.sh %s' % dplmnt["openstack_root"])

    # Config tanent networking
    exec_script_on_host("controller0",
        'sudo ./ctn_provisioning/5.3_tanent_networking.sh %s' % dplmnt["openstack_root"])

else:
    LOG.Info("#######################")
    LOG.Info("# Step 5 Skipped by user.")

LOG.Time("Step 5 Finished")

#########################################
# Deployment Finished
#########################################

if args.log:
    get_system_logs()

#############
## If you can run here, that means all the test passed...

LOG.Info("#################################")
LOG.Info("#################################")
LOG.Info("Test Pass!!!")
dplmnt['status'] = "Pass"
dplmnt['endtime'] = datetime.now().strftime('%H:%M:%S')
LOG.Time("<<<Deployment Finished>>>")
exit_with_success()



