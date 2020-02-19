#!/usr/bin/env python

import os
import argparse
import shutil
import time
from datetime import datetime

import ectest.log as LOG
import ectest.cmd as CMD
import ectest.utils as UTILS
import ectest.testnode as NODE

STX_PROVISION_ERROR = "STX_PROVISION_ERROR"

STX_PROVISION_DIR = None
STX_LOG_DIR = None
STX_SLOWDOWN = 1

def set_provision_env(provisiondir, logdir, slowdown):
    global STX_PROVISION_DIR, STX_LOG_DIR
    if not STX_PROVISION_DIR and not STX_LOG_DIR:
        STX_PROVISION_DIR = provisiondir
        STX_LOG_DIR = logdir
        STX_SLOWDOWN = slowdown

def __exit_with_exception():
    raise Exception(STX_PROVISION_ERROR)

def CK_RET(result):
    UTILS.check_ret(result, __exit_with_exception)

def getfile(d, f):
    if d and f:
        return os.path.join(d, f)
    return f

def getlogfile(f):
    return getfile(STX_LOG_DIR, f)

def stx_unlock(node0, node, logfile=None):
    hostname = node
    if isinstance(node, NODE.Node):
        hostname = node.get_hostname()
    cmd = "set -ex; system host-unlock %s" % hostname
    retval, retlog = node0.stx_cmd(cmd, logfile=logfile)
    LOG.print_log(retlog)
    # sleep awhile until the node rebooted
    time.sleep(60 * 5)
    return retval

def exec_provision_on_host(
    node, script,
    logname=None, needsudo=False, args=[]):

    script = getfile(STX_PROVISION_DIR, script)
    cmd = os.path.join("~", script)
    if needsudo:
        cmd = "sudo " + cmd
    if args:
        for a in args:
            # TODO: if space in arguments, need to add "".
            cmd = cmd + " " + str(a)
    if not logname:
        logname = os.path.splitext(os.path.basename(script))[0] + ".log"

    retval, retlog = node.ssh(cmd, logfile=getlogfile(logname), sudo=needsudo)
    LOG.print_log(retlog)
    CK_RET(retval)

def get_system_logs(node):
    syslog_folder = getlogfile("system_logs")
    CMD.shell("mkdir -p %s/" % syslog_folder, silent=True)

    ret, retlog = node.ssh("collect -a", forcesudo=True, silent=True)
    if ret != 0:
        LOG.Warning("collect returned error code: %s" % str(ret))
        LOG.print_warning(retlog)
    node.copy_from_node("/scratch/*.tgz", syslog_folder)

    node.ssh('sudo sm-dump', logfile=getlogfile("sm-dump.log"), sudo=True, silent=True)

    LOG.Info("Please check the full system log under %s." % syslog_folder)

def get_pod_logs(node, logname=None):
    node.ssh("./get_pods_log.sh", silent=True)
    logloc = getlogfile(logname)
    if not logloc:
        logloc = getlogfile("pod_logs")
    node.copy_from_node("~/pod_logs", logloc)

    LOG.Info("Please check the pod logs under %s." % logloc)

def __wait_for_new_host(node0, node, minutes):
    hostname = node.get_hostname()
    nodeid = node.get_nodeid()
    personality = node.get_personality()

    node.power_off()
    node.boot()

    def check():
        retval, retlog = node0.stx_cmd(
            "system host-list | grep %d" % nodeid,
            silent=True)
        return retval == 0
    ret = UTILS.wait_for("New Host %d occur." % nodeid, check,
        slowdown=STX_SLOWDOWN).run(minutes)

    if ret == 0:
        LOG.Info("Found host node (#%d) as %s, set personality as %s." % (
            nodeid, hostname, personality))

        CK_RET(node0.stx_cmd(
            "system host-update %d personality=%s hostname=%s "
            "boot_device=%s rootfs_device=%s "
            "console=tty0" % (
                nodeid, personality, hostname,
                node.get_boot_device(), node.get_rootfs_device() )))
        return True
    else:
        LOG.Error("Failed to found new host node %s." % hostname)
        return False

def try_for_new_host(node0, node):
    tried = 0
    while not __wait_for_new_host(node0, node, 2):
        tried += 1
        if tried >= 5:
            break
        node.reset()

def wait_for_host_node_status(node0, nodename, minutes, status_list=["online", "available"]):
    statusstring = "|".join(status_list)
    cmd = "system host-list | grep %s | grep -E \"%s\"" % (nodename, statusstring)
    def check():
        retval, retlog = node0.stx_cmd(cmd, silent=True)
        if retval != 0:
            retval, retlog = node0.stx_cmd(cmd, silent=True)
        return 0 == retval
    return UTILS.wait_for(
        "Host %s until %s" % (nodename, statusstring), check,
        slowdown=STX_SLOWDOWN).run(minutes)

def wait_for_host_node_online(node0, nodename, minutes):
    return wait_for_host_node_status(
        node0, nodename, minutes, status_list=["online", "available"])

def wait_for_host_node_enabled(node0, nodename, minutes):
    return wait_for_host_node_status(
        node0, nodename, minutes, status_list=["enabled"])

def wait_for_host_node_available(node0, nodename, minutes):
    return wait_for_host_node_status(
        node0, nodename, minutes, status_list=["available"])

def wait_for_ceph_monitor_from_sysinv(node0, hostname, minutes):
    def check():
        ret, log = node0.stx_cmd("system ceph-mon-list | grep %s | grep configured" % hostname, silent=True)
        return 0 == ret
    ret = UTILS.wait_for("Check ceph monitor from sysinv, %s" % hostname, check,
        slowdown=STX_SLOWDOWN).run(minutes)
    if ret == -1:
        LOG.Warning("%s ceph monitor not available." % hostname)
    return ret

def get_ctn_related_status(node, logfile=None, withceph=False):
    cmds = []
    cmds.append("system host-list")
    if withceph == True:
        cmds.append("ceph -s")
    cmds.append("export KUBECONFIG=\"/etc/kubernetes/admin.conf\"")
    cmds.append("kubectl -n kube-system get po")
    cmds.append("sudo docker ps")

    retval, retlog = node.stx_cmd(";".join(cmds),
          logfile=getlogfile(logfile))
    if retval == 0:
        LOG.print_log(retlog)
    else:
        LOG.print_error(retlog)

################################################
## StarlingX Provisioning
def stx_controller_copy_scripts(node, scripts):
    CK_RET(node.copy_to_node(scripts, "~/"))
    CK_RET(node.ssh('sudo chmod +x *.sh; sudo chmod +x */*.sh', sudo=True, silent=True))

def stx_get_mgmt_ip(node0, node):
    retval, retlog = node0.stx_cmd(
        "system host-show %s" % node.get_hostname())
    LOG.print_log(retlog)

    if retval == 0:
        for l in retlog:
            if l.find("mgmt_ip") >= 0:
                mgmt_ip = l.split()[3]
                node.set_mgmt_ip(mgmt_ip)
                return True

    LOG.Error("MGMT ip not found for %s." % node0.get_hostname())
    return False

def stx_ansible(node, localhost_config):
    LOG.Info("# Config Controller with config file %s" % localhost_config)
    CK_RET(node.copy_to_node(localhost_config, "~/"))

    # Using ansible
    cmd = []
    cmd.append("export PATH=/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin")
    cmd.append("export HOSTNAME=localhost")
    cmd.append("BOOTSTRAP_YML=`find /usr/share/ansible/stx-ansible/playbooks -name bootstrap.yml`")
    cmd.append("ansible-playbook "
        "$BOOTSTRAP_YML "
        "-e \"ansible_become_pass=%s\""
        % node.get_password())

    retval, retlog = node.ssh(";".join(cmd),
        logfile=getlogfile("controller-0.00_ansible.log"))
    LOG.print_log(retlog)

    if retval == 0:
        for l in retlog:
            if l.find("failed=") >= 0:
                import re
                failed = re.compile(".*failed=(\d*)").match(l).group(1)
                if failed != "0":
                    LOG.Error("##### ERROR: ansible doesn't return good result.")
                    return -1
    else:
        LOG.Error("##### ERROR: ansible script exited abnormally.")
        return -1

    return 0

def stx_provision_controller(node0, node, system_mode, ntp_server=None, dpdk=False):
    hostname = node.get_hostname()
    # Setup NTP servers
    if node.is_controller0() and ntp_server:
        node0.stx_cmd("set +ex; system ntp-modify ntpservers=%s" % ntp_server,
            logfile=getlogfile("%s.01_0_setup_ntp_servers.log" % hostname))

    exec_provision_on_host(node0, '%s.01_initialize.sh' % hostname,
        args=[node.get_oam_name(), node.get_mgmt_name()])

    if system_mode != 'multi':
        # simplex or duplex
        # Config data interfaces
        data_nics = node.get_nics_by_type(NODE.NIC_TYPE_DATA)
        nics = [net['name'] for net in data_nics]
        exec_provision_on_host(node0, 'config_data_interface.sh',
            logname="%s.02_config_data_interface.log" % hostname,
            args=[hostname, len(data_nics) if len(data_nics) <= 2 else 2] + nics)

        # Setup partitions
        exec_provision_on_host(node0, 'setup_partition.sh',
            logname="%s.03_setup_partition.log" % hostname,
            args=[hostname])

        # Setup Ceph
        exec_provision_on_host(node0, 'config_ceph.sh',
            logname="%s.04_config_ceph.log" % hostname,
            args=[hostname])

    #############
    # enable dpdk
    if node.is_controller0() and dpdk == 'ovs-dpdk':
        CK_RET(node0.stx_cmd('set +ex; system modify --vswitch_type ovs-dpdk',
                logfile=getlogfile("%s.05_dpdk_enable.log" % hostname)))

    time.sleep(10)
    get_ctn_related_status(node0,
        logfile=getlogfile("%s.08_stx_status_before_unlock.log" % hostname))
    CK_RET(stx_unlock(node0, node,
        logfile=getlogfile("%s.09_unlock.log" % hostname)))
    node.wait_for_node()
    wait_for_host_node_enabled(node0, hostname, 30)
    get_ctn_related_status(node0,
        logfile=getlogfile("%s.10_stx_status_after_unlock.log" % hostname))

    if node.is_controller0() and isinstance(node, NODE.Node_BM):
        # for bare metal controller-0, update the pxe boot ks config.
        exec_provision_on_host(node0, 'controller-0.update_pxeserver.sh', needsudo=True)

def stx_provision_storage(node0, hostlist):
    for host in hostlist:
        stx_wait_for_platform_integ_app(node0,
            acceptable_status=[APP_UPLOAD_SUCCESS, APP_APPLY_SUCCESS])
        exec_provision_on_host(node0,
            'storage.01_provision.sh',
            args=[host],
            logname="storage.01_provision_%s.log" % host)

        stx_wait_for_platform_integ_app(node0,
            acceptable_status=[APP_UPLOAD_SUCCESS, APP_APPLY_SUCCESS],
            exception_on_error=False)
        CK_RET(stx_unlock(node0, host,
            logfile=getlogfile("storage.02_unlock_%s.log" % host)))

def stx_after_provision_storage(node0):
    exec_provision_on_host(node0, 'storage.03_check_storage_status.sh')

def stx_provision_compute(node0, hostdict, dedicated_storage=False):
    for node in hostdict.keys():
        exec_provision_on_host(node0,
            'compute.01_prepare_host_to_run_container.sh',
            args=[node],
            logname="compute.01_prepare_host_to_run_container_%s.log" % node)

    if not dedicated_storage:
        # Add the third Ceph monitor to a compute node
        wait_for_ceph_monitor_from_sysinv(node0, NODE.HOSTNAME_CONTROLLER0, 20)
        wait_for_ceph_monitor_from_sysinv(node0, NODE.HOSTNAME_CONTROLLER1, 20)

        exec_provision_on_host(node0, 'compute.02_add_ceph_monitor.sh')

        CK_RET(wait_for_ceph_monitor_from_sysinv(node0, "compute-0", 60))

    # Create the volume group for nova
    exec_provision_on_host(node0, 'compute.03_create_volumn_group_for_nova.sh')

    # Configure data interfaces for computes
    for n in hostdict.keys():
        node = hostdict[n]

        data_nics = node.get_nics_by_type(NODE.NIC_TYPE_DATA)
        nics = [net['name'] for net in data_nics]
        exec_provision_on_host(node0, 'config_data_interface.sh',
            logname="compute.04_config_data_interface_for_%s.log" % node.get_hostname(),
            args=[node.get_hostname(), len(data_nics) if len(data_nics) <= 2 else 2] + nics)

    # Setup the cluster-host interfaces on the computes to the management network
    exec_provision_on_host(node0, 'compute.05_config_cluster_interfaces.sh')

    cmds = []
    for node in hostdict.keys():
        stx_wait_for_platform_integ_app(node0,
            acceptable_status=[APP_UPLOAD_SUCCESS, APP_APPLY_SUCCESS],
            exception_on_error=False)
        CK_RET(stx_unlock(node0, node,
            logfile=getlogfile("compute.06_unlock_%s.log" % node)))

def stx_after_provision_compute(node0, ceph_osd_configed=False):
    if not ceph_osd_configed:
        for ctlname in [NODE.HOSTNAME_CONTROLLER0, NODE.HOSTNAME_CONTROLLER1]:
            exec_provision_on_host(node0,
                'config_ceph.sh',
                args=[ctlname],
                logname="compute.07_config_ceph_%s.log" % ctlname)

APP_NONE = None
APP_UPLOADING = "uploading"
APP_UPLOAD_SUCCESS = "uploaded"
APP_UPLOAD_FAILED = "upload-failed"
APP_APPLYING = "applying"
APP_APPLY_SUCCESS = "applied"
APP_APPLY_FAILED = "apply-failed"
APP_REMOVING = "removing"
APP_REMOVE_FAILED = "remove-failed"
APP_DELETING = "deleting"
APP_DELETE_FAILED = "delete-failed"

APP_OP_UPLOAD = "application-upload"
APP_OP_DELETE = "application-delete"
APP_OP_APPLY = "application-apply"
APP_OP_REMOVE = "application-remove"
APP_OP_LIST = "application-list"

def __stx_app_stat(node0, appname):
    cmd = "system application-list --nowrap " \
          "| grep %s " % appname
    retval, statli = node0.stx_cmd(cmd, silent=True)
    if retval == 0:
        for l in statli:
            if l.find(appname) >= 0 and l.find("|") >= 0:
                return l.split("|")[-3].strip(), l.split("|")[-2].strip()

    return None, None

def __stx_app_op(node0, op, helm_charts=None, appname=None, silent=False):
    retval = 0
    if helm_charts or appname:
        cmd = "set -ex; system %s %s" % (op, helm_charts if helm_charts else appname)
        retval, retlog = node0.stx_cmd(cmd, silent=silent)
    elif op == APP_OP_LIST:
        retval, retlog = node0.stx_cmd("system %s" % op, silent=silent)
    else:
        LOG.Error("No valid helm charts or app name provided, or unsupported operation.")
        return -1, None

    if retval:
        LOG.print_error(retlog)
    else:
        LOG.print_log(retlog)
    return retval, retlog

def wait_for_app_status_finish(node0, appname, minutes, current_stat):

    def exit_if_true():
        stat, progress = __stx_app_stat(node0, appname)
        LOG.Info("current status: %s, %s" % (stat, progress))
        if stat == None or stat == current_stat:
            # app not found or app status no change, keep waiting
            return False
        else:
            # status changed, exit the wait loop
            return True

    ret = UTILS.wait_for("app %s to finish \"%s\"" % (appname, current_stat),
        exit_if_true, interval=60, slowdown=STX_SLOWDOWN).run(minutes)

    if ret == -1:
        LOG.Error("Wait for %s %s timed out." % (appname, current_stat))

    return __stx_app_stat(node0, appname)[0]

def stx_apply_application(node0, helm_charts):
    LOG.Info("Applying application with helm charts %s." % helm_charts)

    # copy the helm_charts to test folder and upload it to the target.
    charts_filename = os.path.basename(helm_charts)
    appname = os.path.splitext(charts_filename)[0]

    node0.copy_to_node(helm_charts, "~/")

    failures = 0
    appstat = __stx_app_stat(node0, appname)[0]

    def handle_failure(failures):
        failures += 1
        get_pod_logs(node0, logname="pod_logs_failed_%d" % failures)
        return failures

    while appstat != APP_APPLY_SUCCESS:

        LOG.Info("App %s current status: %s" % (appname, appstat))
        if appstat == APP_NONE:
            retval, retlog = __stx_app_op(
                node0, APP_OP_UPLOAD, helm_charts=charts_filename)
            real_app_name = None
            for l in retlog:
                if l.find(" name ") >= 0:
                    real_app_name = l.split("|")[2].strip()
            if not real_app_name:
                __exit_with_exception()
            LOG.Info("App Real Name: %s" % real_app_name)
            appname = real_app_name
            appstat = wait_for_app_status_finish(node0, appname, 20, APP_UPLOADING)

        elif appstat == APP_UPLOAD_SUCCESS:
            retval, retlog = __stx_app_op(
                node0, APP_OP_APPLY, appname=appname)
            appstat = wait_for_app_status_finish(node0, appname, 120, APP_APPLYING)

        elif appstat == APP_UPLOAD_FAILED:
            failures = handle_failure(failures)

            retval, retlog = __stx_app_op(
                node0, APP_OP_DELETE, appname=appname)
            appstat = wait_for_app_status_finish(node0, appname, 20, APP_DELETING)

        elif appstat == APP_APPLY_SUCCESS:
            # should not run here
            break

        elif appstat == APP_APPLY_FAILED:
            failures = handle_failure(failures)

            retval, retlog = __stx_app_op(
                node0, APP_OP_REMOVE, appname=appname)
            appstat = wait_for_app_status_finish(node0, appname, 30, APP_REMOVING)

        elif appstat == APP_REMOVE_FAILED:
            failures = handle_failure(failures)

            retval, retlog = __stx_app_op(
                node0, APP_OP_REMOVE, appname=appname)
            appstat = wait_for_app_status_finish(node0, appname, 30, APP_REMOVING)

        elif appstat == APP_DELETE_FAILED:
            # Fatal
            LOG.Error("Failed to delete app %s after %d failures" % (appname, failures))
            __exit_with_exception()

        elif appstat in [APP_UPLOADING, APP_APPLYING, APP_REMOVING, APP_DELETING]:
            failures = handle_failure(failures)

            appstat = wait_for_app_status_finish(node0, appname, 20, appstat)

        else:
            # Fatal
            LOG.Error("Unknown application status %s" % appstat)
            __exit_with_exception()

        if failures >= 5:
            # Fatal
            LOG.Error("Application %s apply failed!" % app_name)
            __exit_with_exception()

    return appname

def stx_wait_for_platform_integ_app(node0, acceptable_status=[APP_APPLY_SUCCESS], exception_on_error=True):
    appname = "platform-integ-apps"
    stat = __stx_app_stat(node0, appname)[0]

    while stat not in acceptable_status:
        if stat in [APP_UPLOADING, APP_APPLYING]:
            stat = wait_for_app_status_finish(node0, appname, 20, stat)

        elif stat in [APP_UPLOAD_FAILED, APP_APPLY_FAILED]:
            LOG.Error("%s failed to be applied, exit with error." % appname)
            if exception_on_error:
                __exit_with_exception()
            else:
                break

        else:
            time.sleep(10)
            stat = __stx_app_stat(node0, appname)[0]

    __stx_app_op(node0, APP_OP_LIST)

def stx_openstack_provision(node0, openstack_root, admin_passwd, node1=None):
    # Verify cluster endpoints
    exec_provision_on_host(node0,
        'openstack.01_verify_cluster_endpoints.sh',
        needsudo=True,
        logname="openstack.01_verify_cluster_endpoints_controller0.log",
        args=[openstack_root, admin_passwd])

    if node1:
        exec_provision_on_host(node1,
            'openstack.01_verify_cluster_endpoints.sh',
            needsudo=True,
            logname="openstack.01_verify_cluster_endpoints_controller1.log",
            args=[openstack_root, admin_passwd])

    # Config provider networking for Stein
    exec_provision_on_host(node0, 'openstack.02_provider_networking_stein.sh',
        needsudo=True, args=[openstack_root])

    # Config tanent networking
    exec_provision_on_host(node0, 'openstack.03_tanent_networking.sh',
        needsudo=True, args=[openstack_root])


