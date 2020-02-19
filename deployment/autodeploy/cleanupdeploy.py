#!/usr/bin/env python

import os
import argparse
import shutil
from subprocess import *

import ectest.log as LOG
import ectest.cmd as CMD

CurrPath = os.path.join(os.path.abspath(os.getcwd()))

#########################
##Structure the Arg Parser
desc = "EC Auto Deployment - Cleanup"
parser = argparse.ArgumentParser(description=desc)
parser.add_argument('--vmname',
    help="Delete a specific vm.",
    type=str)
parser.add_argument('--delete_all',
    help="Undefine the vms and delete the disk images.",
    action="store_true")

parser.add_argument('--brname',
    help="OAM bridge name.",
    type=str,
    default='virbr1')

args = parser.parse_args()

def is_on_the_bridge(domID, brname):
    rv, brlist =  CMD.shell("sudo virsh domiflist %s | grep bridge | awk '{print $3;}'" % domID)
    if brname in brlist:
        return True
    return False

vmlist = []
vmlist_d = []
if args.vmname:
    cmd = "sudo virsh list --all | grep %s | awk '{print $2}'" % args.vmname
    retval, vmlist = CMD.shell(cmd)
else:
    cmd = "sudo virsh list --all | grep running | awk '{print $2}'"
    retval, vmlist = CMD.shell(cmd)
    cmd = "sudo virsh list --all | grep -v running | grep -v Name | awk '{print $2}'"
    retval, vmlist_d = CMD.shell(cmd)
    while '' in vmlist_d:
        vmlist_d.remove('')

for r in vmlist:
    if is_on_the_bridge(r, args.brname):
        LOG.Info("===========================")
        LOG.Info("Destroying : %s" % r)
        cmds = []
        # Only destroy the vms here
        cmds.append("sudo virsh destroy %s || true" % r)
        rv, rs = CMD.shell(";".join(cmds))
        LOG.Info("Return Value: %s" % str(rv))
        for rl in rs:
            LOG.Info(rl)

if args.delete_all:
    LOG.Info("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    LOG.Info("Vms will be perminantly deleted.")
    for r in vmlist + vmlist_d:
        if is_on_the_bridge(r, args.brname):
            LOG.Info("===========================")
            LOG.Info("Deleting : %s" % r)
            cmd = "sudo virsh dumpxml %s | grep \"source file\" | grep -v \"iso\" | awk -F \"'\" '{print $2;}'" % r
            retval, imglist = CMD.shell(cmd)
            cmds = []
            cmds.append("sudo virsh undefine %s || true" % r)
            for f in imglist:
                cmds.append("sudo rm -rf %s || true" % f)
            rv, rs = CMD.shell(";".join(cmds))
            LOG.Info("Return Value: %s" % str(rv))
            for rl in rs:
                LOG.Info(rl)


