import os
import shutil
import re
import logging


def LogError(cmd):
    print "ERROR: %s" % cmd
    logging.error(cmd)

def find_words_noempty(line, splitkey):
    return [n.strip() for n in re.split("["+splitkey+"]", line.strip()) if n.strip()]

def find_words(line, splitkey):
    return [n.strip() for n in re.split("["+splitkey+"]", line.strip()) if n]

def get_lines(logfile, keyword):
    if keyword == None or len(keyword) <= 0:
        return None
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    validlines = []
    with open(logfile, "r") as f:
        for line in f:
            if line.find(keyword) > 0:
                validlines.append(line)
    return validlines

def get_hosts_added(logfile):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    hosts = []
    validlines = []
    with open(logfile, "r") as f:
        host = {}
        for line in f:
            words = find_words_noempty(line, "|")
            if len(words) == 0:
                continue
            if words[0] == "hostname":
                host["hostname"] = words[1]
            elif words[0] == "mgmt_ip":
                host["ip"] = words[1]
                hosts.append(host)
                host = {}
    return hosts

def get_host_list(logfile, personality="all"):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    lines = None
    if personality == 'controller':
        lines = get_lines(logfile, "controller-")
    elif personality == 'compute':
        lines = get_lines(logfile, "compute-")
    elif personality == 'all':
        lines = get_lines(logfile, "controller-") + get_lines(logfile, "compute-")
    else:
        return None

    hosts = []
    for line in lines:
        words = find_words_noempty(line, "|")
        if words: hosts.append(words[0])
    return hosts


def get_host_list_status(logfile, hostname):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    lines = get_lines(logfile, hostname)
    host_status = {}
    if lines:
        title_words = find_words(get_lines(logfile, "hostname")[0], "|")
        words = find_words(lines[0], "|")
        for i in range(len(words)):
            host_status[title_words[i]] = words[i]
        return host_status
    return None


def get_wrong_nova_services(logfile):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    wrong_services = {"disabled" : [], "forced-down": []}
    with open(logfile, "r") as f:
        for line in f:
            words = find_words(line, "|")
            if len(words) == 9 and words[0] != 'Id':
                if words[4] == "disabled":
                    wrong_services['disabled'].append(words[0])
                if words[8] == "True":
                    wrong_services['forced-down'].append(words[0])
    return wrong_services

def is_sm_dump_all_enabled(logfile):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return False

    with open(logfile, "r") as f:
        for line in f:
            if line.find("disable") > 0:
                return False
            if line.find("initial") > 0:
                return False
            if line.find("enabling") > 0:
                return False
            if line.find("go-active") > 0:
                return False

    return True


##################################
# Parse the following log and return the dict for vmname.
#[wrsroot@controller-0 ~(keystone_admin)]$ openstack server list
#+--------------------------------------+------+--------+-------------------+--------+----------+
#| ID                                   | Name | Status | Networks          | Image  | Flavor   |
#+--------------------------------------+------+--------+-------------------+--------+----------+
#| 8c624a63-79e3-493e-bbf3-82e2eda07ddc | vm1  | BUILD  | net=192.168.100.3 | cirros | m1.tinny |
#+--------------------------------------+------+--------+-------------------+--------+----------+
def get_allvms(logfile):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    vms = []
    with open(logfile, "r") as f:
        for line in f:
            if line.startswith("|"):
                words = find_words(line, "|")
                if words and words[0] != "ID" and len(words) == 6:
                    vm = {
                        "ID" : words[0],
                        "Name" : words[1],
                        "Status" : words[2],
                        "Networks" : words[3].split("=")[1] if words[3] and words[3].startswith("net=") else "",
                        "Image" : words[4],
                        "Flavor" : words[5],
                    }
                    vms.append(vm)
    return vms

def get_vm_structure(logfile, vmname):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None

    lines = get_lines(logfile, vmname)
    if lines:
        words = find_words(lines[0], "|")
        if len(words) == 6:
            return {
                "ID" : words[0],
                "Name" : words[1],
                "Status" : words[2],
                "Networks" : words[3].split("=")[1] if words[3] and words[3].startswith("net=") else "",
                "Image" : words[4],
                "Flavor" : words[5],
            }
    return None


##################################
# Container Related

def get_application_status(logfile, appname):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None
    lines = get_lines(logfile, appname)
    if lines:
        words = find_words_noempty(lines[0], "|")
        if words and len(words) > 4:
            return words[3].lower()
    return "unknown"

def get_ceph_monitor_status(logfile, hostname):
    if not os.path.exists(logfile):
        LogError("ERROR: file not found: %s" % logfile)
        return None
    lines = get_lines(logfile, hostname)
    if lines:
        words = find_words_noempty(lines[0], "|")
        if words and len(words) > 4:
            return words[3].lower()
    return "unknown"

