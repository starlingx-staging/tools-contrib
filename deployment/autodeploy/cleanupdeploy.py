#!/usr/bin/env python

import os
import argparse
import shutil
from subprocess import *

import ectest.log as LOG

DEBUG = True

CurrPath = os.path.join(os.path.abspath(os.getcwd()))

#########################
##Structure the Arg Parser
desc = "StarlingX Auto Deployment - Cleanup"
parser = argparse.ArgumentParser(description=desc, version='%(prog)s 1.0')
parser.add_argument('virtimg_dir',
    help="Dir to place kvm images for controllers and computes.",
    type=str)
parser.add_argument('--vmname',
    help="Delete a specific vm.",
    type=str)
parser.add_argument('--method',
    help="Create KVM or VirtualBox for deployment test.",
    type=str,
    choices=["kvm"], # removed "vbox" because vbox is not available now.
    default="kvm")

args = parser.parse_args()

def iskvm():
    return args.method == "kvm"
def isvbox():
    return args.method == "vbox"
if isvbox():
    LOG.Info("!!! WARNING !!!: vbox is not tested in this version of script.")


def cmdhost(cmd, cwd=None, logfile=None, silent=False):
    realcmd = cmd
    result = ""
    retval = 0

    if cwd != None:
        os.chdir(cwd)
    try:
        result = check_output(realcmd, shell = True).splitlines()
    except CalledProcessError as ecp:
        LOG.Error("ERROR: failed to run \"%s\": returned %s %s" % (cmd, ecp.returncode, ecp.output))
        retval = ecp.returncode
    except Exception, error:
        LOG.Error("ERROR: failed to run \"%s\": %s" % (cmd, error))
        LOG.Error("")
        retval = -1

    LOG.Info("Finished \"%s\": %s" % (cmd, result), silent=silent)
    LOG.Info("", silent=silent)
    return retval, result

if iskvm():
    vmlist = []
    if args.vmname:
        vmlist.append(args.vmname)
    else:
        cmd = "sudo virsh list | grep running | awk '{print $2}'"
        retval, vmlist = cmdhost(cmd)

    for r in vmlist:
        LOG.Info("===========================")
        LOG.Info("Destroying : %s" % r)
        cmds = []
        cmds.append("sudo virsh destroy %s || true" % r)
        # cmds.append("sudo virsh undefine %s || true" % r)
        # cmds.append("sudo rm -rf %s/%s-0.img || true" % (args.virtimg_dir, r))
        # cmds.append("sudo rm -rf %s/%s-1.img || true" % (args.virtimg_dir, r))
        rv, rs = cmdhost(";".join(cmds))
        LOG.Info("Return Value: %s" % str(rv))
        for rl in rs:
            LOG.Info(rl)


