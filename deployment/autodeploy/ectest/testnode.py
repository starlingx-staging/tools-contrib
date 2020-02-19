"""
Test Node: ipmitool wrapper to control StarlingX test nodes.

Config Files:
    Located in testnode_config folder.
    testnode_config
      |- pxe_server.json  # config file for pxe server
      |- bm
      |   |- ws_123.json
      |- vm_template.json

"""

import json
import os
import re
import shutil
import time

try:
    import ectest.log as LOG
    import ectest.cmd as CMD
    import ectest.utils as UTILS
except:
    import log as LOG
    import cmd as CMD
    import utils as UTILS

DEFAULT_USER = "sysadmin"

PERSONALITY_CONTROLLER = "controller"
PERSONALITY_STORAGE = "storage"
PERSONALITY_COMPUTE = "worker"
PERSONALITY_UNKNOWN = "unknown"

HOSTNAME_CONTROLLER0 = "controller-0"
HOSTNAME_CONTROLLER1 = "controller-1"

NODE_EMPTY = "EMPTY"
NODE_INSTALLED = "INSTALLED"
NODE_UNLOCKED = "UNLOCKED"
NODE_ERROR = "ERROR"

NIC_TYPE_NONE = ""
NIC_TYPE_OAM = "oam"
NIC_TYPE_MGMT = "mgmt"
NIC_TYPE_DATA = "data"
VALID_NIC_TYPES = [
    NIC_TYPE_NONE,
    NIC_TYPE_OAM,
    NIC_TYPE_MGMT,
    NIC_TYPE_DATA
]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Node Controller")
    parser.add_argument('vmname',
        help="VM name", type=str)
    parser.add_argument('node_config',
        help="Test Node Config.", type=str)

    args = parser.parse_args()
    node = Node_KVM(
        args.node_config,
        args.vmname,
        HOSTNAME_CONTROLLER0, 1, "10.10.10.3")
    ret = node.create_secure_path()
    LOG.Info("== Create Secure Path: ret %s" % ret)
    ret, log = node.ssh("ls")
    LOG.Info("== SSH CMD: ret %s" % ret)
    LOG.print_log(log)
    print(node.get_oam_ip())
    print(node.get_nic(name="eth1001"))
    print(node.get_nic(bridge="virbr3"))
    print(node.is_power_on())


class Node(object):
    """
    Test Node
    """
    CONFIG = None
    User = None
    Password = None

    SecurePath = False
    SudoNoPwd = False
    FirstLogin = True

    Status = NODE_EMPTY

    def __init__(self,
        config_json,
        hostname,
        nodeid,
        user="sysadmin", password="sysadmin", slowdown=1):

        self.CONFIG = UTILS.load_json_config(config_json)
        self.slowdown = slowdown
        self.User = user
        self.Password = password

        self.CONFIG["hostname"] = hostname
        if hostname.find("controller") >= 0:
            self.CONFIG["personality"] = PERSONALITY_CONTROLLER
        elif hostname.find("compute") >= 0:
            self.CONFIG["personality"] = PERSONALITY_COMPUTE
        elif hostname.find("storage") >= 0:
            self.CONFIG["personality"] = PERSONALITY_STORAGE
        else:
            self.CONFIG["personality"] = PERSONALITY_UNKNOWN
        self.CONFIG["nodeid"] = nodeid

    def Info(self, log):
        LOG.Info("%s: %s" % (self.name, log))
    def Error(self, log):
        LOG.Error("%s: %s" % (self.name, log))
    def toString(self):
        self.Info("==== Host Name: %s ====" % self.get_hostname())
        self.Info(json.dumps(self.CONFIG, indent=2))

    ### Operations Over OS ###

    def create_secure_path(self):
        self.Info("Start to create secure ssh path.")
        oam_ip = self.get_oam_ip()
        if oam_ip:
            retval, retlog = UTILS.create_secure_path(
                oam_ip,
                self.User, password=self.Password)
            if retval == 0:
                self.Info("Secure SSH path created.")
                self.SecurePath = True
                # self.sudo_nopasswd()

                floating_ip = self.get_floating_ip()
                if floating_ip:
                    UTILS.add_sshkey_config(floating_ip, self.User)
                return True
            else:
                LOG.print_error(retlog)

        self.Error("Failed to generate secure ssh path.")
        self.Status = NODE_ERROR
        self.SecurePath = False

        return False

    def copy_to_node(self, src, dst):
        if self.get_oam_ip():
            if self.SecurePath:
                retval, retlog = UTILS.scp_to_server(
                    src, dst, self.get_oam_ip(), self.User)
            else:
                retval, retlog = UTILS.scp_to_server(
                    src, dst, self.get_oam_ip(), self.User,
                    password=self.Password)
            if retval == 0:
                return True
            else:
                LOG.print_error(retlog)
        self.Error("Failed to copy %s to node." % src)
        return False

    def copy_from_node(self, src, dst):
        if self.get_oam_ip():
            if self.SecurePath:
                retval, retlog = UTILS.scp_from_server(
                    src, dst, self.get_oam_ip(), self.User)
            else:
                retval, retlog = UTILS.scp_from_server(
                    src, dst, self.get_oam_ip(), self.User,
                    password=self.Password)
            if retval == 0:
                return True
            else:
                LOG.print_error(retlog)
        self.Error("Failed to copy %s from node." % src)
        return False

    def sudo_nopasswd(self):
        ## TODO
        sudo_script = "~/sudo_nopwd.sh"
        cmds = []
        cmds.append("echo \"cat << EOF | sudo tee /etc/sudoers.d/%s\" > %s" % (self.User, sudo_script))
        cmds.append("echo \"%s ALL = (root) NOPASSWD:ALL\" >> %s" % (self.User, sudo_script))
        cmds.append("echo \"EOF\" >> %s" % (sudo_script))
        cmds.append("chmod +x %s" % (sudo_script))
        retval, retlog = self.ssh(";".join(cmds))

        retval, retlog = self.ssh(sudo_script, sudo=True)
        LOG.print_log(retlog)
        if retval == 0:
            self.SudoNoPwd = True

    def __ssh(self, ip, cmd, silent=False, sudo=False, forcesudo=False, logfile=None):
        pwd = None
        if not self.SecurePath or (sudo and not self.SudoNoPwd) or forcesudo:
            pwd = self.Password

        return UTILS.secure_ssh(
            cmd, ip, self.User, password=pwd,
            silent=silent, logfile=logfile)

    def ssh(self, cmd, silent=False, sudo=False, forcesudo=False, logfile=None):
        if self.get_oam_ip():
            return self.__ssh(self.get_oam_ip(),
                cmd,
                silent=silent, sudo=sudo, forcesudo=forcesudo, logfile=logfile)

        self.Error("No OAM IP.")
        return -1, []

    def ssh_floating(self, cmd, silent=False, sudo=False, logfile=None):
        if self.get_floating_ip():
            return self.__ssh(self.get_floating_ip(),
                cmd,
                silent=silent, sudo=sudo, logfile=logfile)

        self.Error("No Floating IP.")
        return -1, []

    def stx_cmd(self, cmd, silent=False, logfile=None):
        stx_cmd = 'source /etc/platform/openrc; %s' % cmd
        return self.ssh(stx_cmd, silent=silent, logfile=logfile)

    def stx_cmd_floating(self, cmd, silent=False, logfile=None):
        stx_cmd = 'source /etc/platform/openrc; %s' % cmd
        return self.ssh_floating(stx_cmd, silent=silent, logfile=logfile)

    def os_cmd(self, cmd, openstack_root, silent=False, logfile=None):
        os_cmd = 'export OS_CLOUD=%s; %s' % (openstack_root, cmd)
        return self.ssh(os_cmd, silent=silent, logfile=logfile)

    def check_ping(self):
        if self.get_oam_ip():
            pingcmd = "ping %s -c 1 >/dev/null 2>&1" % self.get_oam_ip()
            return 0 == CMD.shell(pingcmd, silent=True)[0]
        return False

    def wait_for_sshd(self, minutes=30):
        self.remove_from_knownhosts()

        def check():
            retval, retlog = self.ssh("ls", silent=True)
            return retval == 0
        ret = UTILS.wait_for("SSHD on %s" % self.name, check,
            slowdown=self.slowdown).run(minutes)

        if ret == 0:
            self.Info("ssh connected.")
            if not self.SecurePath:
                self.create_secure_path()
                self.ssh("sudo sed -i 's/TMOUT=900/TMOUT=0/g' /etc/profile.d/custom.sh",
                    silent=True, sudo=True)
            return True

        self.Error("Failed to wait for sshd up.")
        return False

    def wait_for_node(self, minutes=30):
        if self.get_oam_ip():
            pingcmd = "ping %s -c 1 >/dev/null 2>&1" % self.get_oam_ip()
            def check():
                return 0 == CMD.shell(pingcmd, silent=True)[0]
            ret = UTILS.wait_for(self.name, check, slowdown=self.slowdown).run(minutes)
            if ret == 0:
                ret = self.wait_for_sshd(minutes)
                if ret:
                    return True

            self.Error("Failed to wait for node up.")
            return False
        else:
            self.Error("No OAM IP.")
            return False

    def add_route_for_oam(self, oam_gate_way):
        oam_ip = self.get_oam_ip()
        oam_bridge = self.get_oam_bridge()
        if oam_ip and oam_bridge:
            LOG.Info("Add route for oam %s via %s on dev %s" % (
                oam_ip, oam_gate_way, oam_bridge))
            ret, log = CMD.shell("sudo ip route add %s via %s dev %s" % (
                oam_ip, oam_gate_way, oam_bridge))
            if ret:
                LOG.print_error(log)

    def cleanup_network_env(self, oam_gate_way):
        default_nic = None
        for n in self.CONFIG['network'].keys():
            if n == 'default':
                default_nic = self.CONFIG['network'][n]
                continue
            nic = self.CONFIG['network'][n]
            if 'brname' in nic and nic['brname']:
                ret, log = CMD.shell("sudo ip addr | grep %s | grep %s" % (oam_gate_way, nic['brname']),
                    silent=True)
                if ret == 0:
                    LOG.Info("Delete %s on %s." % (oam_gate_way, nic['brname']))
                    ret, log = CMD.shell("sudo ip addr del %s dev %s" % (oam_gate_way, nic['brname']))

        def default_route_on_nic(nicname):
            ret, log = self.ssh('sudo route | grep default | grep %s' % nicname,
                sudo=True, silent=True)
            if ret == 0:
                LOG.Info("Already has default route on %s" % nicname)
            return ret == 0
        for n in self.CONFIG['network'].keys():
            if n == 'default':
                continue
            nic = self.CONFIG['network'][n]
            if default_route_on_nic(nic['name']):
                LOG.Info("Delete default route on %s." % nic['name'])
                self.ssh('sudo route del default', sudo=True)

        if default_nic and not default_route_on_nic(default_nic['name']):
            LOG.Info("Add default route %s on %s" % (oam_gate_way, default_nic['name']))
            self.ssh('sudo route add default gw %s %s' % (oam_gate_way, default_nic['name']), sudo=True)

    def remove_from_knownhosts(self):
        oam_ip = self.get_oam_ip()
        floating_ip = self.get_floating_ip()
        cmd = []
        if oam_ip:
            cmd.append('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s >/dev/null 2>&1' % oam_ip)
        if floating_ip:
            cmd.append('ssh-keygen -f "$HOME/.ssh/known_hosts" -R %s >/dev/null 2>&1' % floating_ip)
        retval, retlog = CMD.shell(';'.join(cmd), silent=True)
        if retlog:
            LOG.print_log(retlog)

    ### Node Config ###
    def is_controller0(self):
        return self.CONFIG['hostname'] == HOSTNAME_CONTROLLER0
    def get_node_config(self):
        return self.CONFIG
    def get_name(self):
        return self.name
    def get_hostname(self):
        return self.CONFIG["hostname"]
    def get_personality(self):
        return self.CONFIG["personality"]
    def get_nodeid(self):
        return self.CONFIG["nodeid"]
    def get_status(self):
        return self.Status
    def get_password(self):
        return self.Password

    def set_status(self, status):
        self.Status = status

    # hard disk
    def get_boot_device(self):
        if "boot_device" in self.CONFIG:
            return self.CONFIG["boot_device"]
        else:
            return "sda"
    def get_rootfs_device(self):
        if "rootfs_device" in self.CONFIG:
            return self.CONFIG["rootfs_device"]
        else:
            return "sda"

    # network
    def check_nic_available(self, system_mode):
        # Check OAM Network
        if not self.get_nics_by_type(NIC_TYPE_OAM) \
            and self.get_personality() == PERSONALITY_CONTROLLER:
            self.Error("No available network for OAM for controllers.")
            return False

        # Check MGMT Network (only duplex and multi)
        if system_mode != "simplex":
            if not self.get_nics_by_type(NIC_TYPE_MGMT):
                self.Error("No available network for MGMT.")
                return False

        # Check Data Network
        data_nics = self.get_nics_by_type(NIC_TYPE_DATA)
        if not data_nics:
            data_nics = self.get_free_nics()
            if data_nics:
                for n in data_nics:
                    n["type"] = NIC_TYPE_DATA
            else:
                self.Error("No available network for DATA.")
                return False
        return True

    def get_floating_ip(self):
        return self.CONFIG["floating_ip"]
    def get_oam_ip(self):
        if "default" in self.CONFIG["network"]:
            return self.CONFIG["network"]["default"]["ip"]
        self.Error("No default oam network.")
        return None
    def get_oam_name(self):
        if "default" in self.CONFIG["network"]:
            return self.CONFIG["network"]["default"]["name"]
        self.Error("No default oam network.")
        return None
    def get_oam_bridge(self):
        if "default" in self.CONFIG["network"]:
            if "brname" in self.CONFIG["network"]["default"].keys():
                return self.CONFIG["network"]["default"]["brname"]
            else:
                self.Error("No Bridge set for OAM network.")
                return None
        self.Error("No default oam network.")
        return None
    def get_mgmt_ip(self):
        for nic in self.CONFIG["network"].keys():
            if self.CONFIG["network"][nic]["type"] == NIC_TYPE_MGMT:
                return self.CONFIG["network"][nic]["ip"]
        self.Error("No management network.")
        return None
    def get_mgmt_name(self):
        for nic in self.CONFIG["network"].keys():
            if self.CONFIG["network"][nic]["type"] == NIC_TYPE_MGMT:
                return self.CONFIG["network"][nic]["name"]
        self.Error("No management network.")
        return None
    def get_nic(self, mac=None, name=None, bridge=None, type=None):
        for nic in self.CONFIG["network"].keys():
            network = self.CONFIG["network"][nic]
            if network["mac"] == mac or network["name"] == name:
                return network
            if "brname" in network and network["brname"] == bridge:
                return network
        if mac:
            self.Error("NIC for MAC %s not found." % mac)
        elif name:
            self.Error("NIC for name %s not found." % name)
        elif bridge:
            self.Error("NIC on bridge %s not found." % bridge)
        else:
            self.Error("Neither MAC nor NIC name nor bridge name is given.")
        return None
    def get_nics_by_type(self, nictype):
        nics = []
        for nic in self.CONFIG["network"].keys():
            network = self.CONFIG["network"][nic]
            if network["type"] == nictype:
                nics.append(network)
        if not nics:
            self.Error("No network of type %s found." % nictype)
        return nics
    def get_nic_name(self, mac):
        nic = self.get_nic(mac=mac)
        if nic:
            return nic["name"]
        return None
    def get_free_nics(self):
        free_nics = []
        for nic in self.CONFIG["network"].keys():
            if self.CONFIG["network"][nic]["type"] == NIC_TYPE_NONE:
                free_nics.append(self.CONFIG["network"][nic])
        if not free_nics:
            self.Error("No free NIC found.")
        return free_nics
    def get_mac(self, name=None, bridge=None):
        nic = self.get_nic(name=name, bridge=bridge)
        if nic:
            return nic["mac"]
        return None
    def get_data_nic_num(self):
        data_nics = self.get_nics_by_type(NIC_TYPE_DATA)
        return len(data_nics)

    def set_floating_ip(self, ip):
        self.CONFIG["floating_ip"] = ip
    def set_oam_ip(self, ip):
        if "default" in self.CONFIG["network"]:
            self.CONFIG["network"]["default"]["ip"] = ip
        else:
            self.Error("No default oam network.")
    def set_mgmt_ip(self, mgmt_ip):
        for nic in self.CONFIG["network"].keys():
            if nic == NIC_TYPE_MGMT or self.CONFIG["network"][nic]["type"] == NIC_TYPE_MGMT:
                self.CONFIG["network"][nic]["ip"] = mgmt_ip
                return
        self.Error("No Management Network specified.")
    def set_nic_type(self, mac=None, name=None, nictype=None):
        nic = self.get_nic(mac=mac, name=name)
        if nic and nictype in VALID_NIC_TYPES:
            if nic["type"] == NIC_TYPE_NONE:
                nic["type"] = nictype
                return True
            else:
                self.Error("NIC %s already occupied as %s." % (nic["name"], nic["type"]))
                return False
        self.Error("set_nic_type Bad parameter (name=%s, type=%s)." % (name, nictype))
        return False

    ### Power Controller ###
    ### should be inherited for each types of test nodes.
    
    def is_power_on(self):
        return False
    def power_on(self):
        return 0, []
    def power_off(self):
        return 0, []
    def reset(self):
        return 0, []

    def boot(self):
        return self.power_on()


class Node_KVM(Node):
    """
    KVM Node
    """
    def __init__(self,
        node_config_json,
        name,
        hostname,
        nodeid,
        oam_ip,
        net_config=None,
        user=DEFAULT_USER, password=DEFAULT_USER, slowdown=1):

        super(Node_KVM, self).__init__(
            node_config_json,
            hostname,
            nodeid,
            user, password, slowdown)

        self.CONFIG['name'] = name
        self.name = self.CONFIG['name']
        self.CONFIG['network']['default']['ip'] = oam_ip
        if net_config:
            for nic in self.CONFIG['network'].keys():
                if nic in net_config:
                    if "brname" in net_config[nic]:
                        self.CONFIG['network'][nic]["brname"] = net_config[nic]["brname"]
                    if "mac" in net_config[nic]:
                        self.CONFIG['network'][nic]["mac"] = net_config[nic]["mac"]

    def is_power_on(self):
        retval, retlog = CMD.shell("sudo virsh list | grep %s" % self.name, silent=True)
        return retval == 0
    def power_on(self):
        if not self.is_power_on():
            return CMD.shell("sudo virsh start %s" % self.name)
        return 0, []
    def power_off(self):
        if self.is_power_on():
            return CMD.shell("sudo virsh destroy %s" % self.name)
        return 0, []
    def reset(self):
        if self.is_power_on():
            retval, retlog = CMD.shell("sudo virsh destroy %s" % self.name)
            if retval != 0:
                return retval, retlog
        return CMD.shell("sudo virsh start %s" % self.name)

    def boot(self):
        return self.power_on()

    def __update_nic_info(self, nicid, mac, bridge):
        if nicid in self.CONFIG['network']:
            self.CONFIG['network'][nicid]['mac'] = mac
            self.CONFIG['network'][nicid]['brname'] = bridge

    def kvm_update_netmap(self):
        retval, mac_list = CMD.shell(
            "sudo virsh domiflist %s | grep bridge | awk '{print $NF}'" % self.name,
            silent=True)
        retval, br_list = CMD.shell(
            "sudo virsh domiflist %s | grep bridge | awk '{print $(NF-2)}'" % self.name,
            silent=True)

        nic_list = ['default', 'mgmt', 'data0', 'data1']
        if retval == 0:
            self.CONFIG['num_of_nic'] = len(mac_list)
            for i in range(len(mac_list)):
                self.Info("%s: %s %s" % (nic_list[i], mac_list[i], br_list[i]))
                self.__update_nic_info(nic_list[i], mac_list[i], br_list[i])
            return True

        else:
            self.Error("Failed to get Network Map.")
            return False

    def __get_nicname(self, mac):
        import re
        reg=re.compile('.*NAME="(?P<nic_name>[^"]*)"',re.M)
        retval, retlog = self.ssh(
            "grep %s /etc/udev/rules.d/70-persistent-net.rules" % mac,
            silent=True)

        if retval == 0:
            match = reg.match(retlog[0])
            if match:
                return match.group('nic_name')
        return None

    def kvm_update_nicname(self):
        if self.wait_for_node() == True:
            for n in self.CONFIG['network'].keys():
                nic = self.CONFIG['network'][n]
                nicname = self.__get_nicname(nic["mac"])
                print("DEBUG: NICNAME " + nicname)
                if nicname:
                    nic["name"] = nicname
                else:
                    self.Error("Failed to find name for nic: %s" % nic["mac"])
                    return False
        else:
            self.Error("Cannot connect to the node, failed to update NIC names.")
            return False

        return True


class Node_BM(Node):
    """
    Bare Metal Node
    """
    BOOT_FROM_PXE = "pxe"

    BOOT_MODE_EFI = "efiboot"
    BOOT_MODE_BIOS = None


    def __init__(self,
        node_config_json,
        hostname,
        nodeid,
        user=DEFAULT_USER, password=DEFAULT_USER, slowdown=1):

        super(Node_BM, self).__init__(
            node_config_json,
            hostname,
            nodeid,
            user, password, slowdown)

        self.name = self.CONFIG['name']
        self.bmc_ip = self.CONFIG['bmc_ip']
        self.bmc_port = self.CONFIG['bmc_port']
        self.bmc_user = self.CONFIG['bmc_user']
        self.bmc_pwd = self.CONFIG['bmc_pwd']

        self.force_pxe = True
        if "force_pxe_for_first_boot" in self.CONFIG:
            self.force_pxe = int(self.CONFIG['force_pxe_for_first_boot']) > 0


    def __check_ipmi_result(self, ret, log):
        if ret != 0:
            for l in log:
                self.Error("IPMI_OUTPUT: " + l)
        else:
            for l in log:
                self.Info("IPMI_OUTPUT: " + l)

    def __ipmi_cmd(self, ipmi_cmd, silent=False):
        cmd = 'ipmitool -I lanplus -H %s -U %s -P %s -p %s %s' \
                     % (self.bmc_ip,
                        self.bmc_user,
                        self.bmc_pwd,
                        self.bmc_port,
                        ipmi_cmd)
        self.Info("IPMICMD: %s" % cmd)
        ret, log = CMD.shell(cmd, silent=silent)
        if not silent:
            self.__check_ipmi_result(ret, log)
        time.sleep(3)
        return ret, log

    def is_power_on(self):
        ret, log = self.__ipmi_cmd(
            'chassis power status | grep on',
            silent=True)
        return 0 == ret
    def power_on(self):
        if not self.is_power_on():
            return self.__ipmi_cmd('chassis power on')
        return 0, ["already powered on."]
    def power_off(self):
        if self.is_power_on():
            return self.__ipmi_cmd('chassis power off')
        return 0, ["already powered off."]
    def reset(self):
        if not self.is_power_on():
            return self.__ipmi_cmd('chassis power on')
        return self.__ipmi_cmd('chassis power reset')

    def __set_bootdev(self, bootdev, bootmode=None):
        cmd = 'chassis bootdev %s' % bootdev
        if bootmode:
            cmd = 'chassis bootdev %s options=%s' % (bootdev, bootmode)
        return self.__ipmi_cmd(cmd)

    def __sol_session_activate(self):
        return self.__ipmi_cmd('sol activate')
    def __sol_session_deactivate(self):
        return self.__ipmi_cmd('sol deactivate')

    def __get_boot_parameter(self):
        ret, log = self.__ipmi_cmd('chassis bootparam get 5')
        for l in log:
            if ret == 0:
                self.Info("IPMI_OUTPUT: " + l)
            else:
                self.Error("IPMI_OUTPUT: " + l)

    def __force_pxe(self):
        """Boot the installation target server using PXE server"""
        self.Info('>> Node {}: Setting PXE as first boot option'
                 .format(self.name))
        retval, retlog = self.__set_bootdev(
            self.BOOT_FROM_PXE, bootmode=self.BOOT_MODE_EFI)
        self.__get_boot_parameter()
        return retval, retlog

    def boot(self):
        if self.force_pxe:
            self.__force_pxe()

        self.Info('>> Node {}: Resetting target.'.format(self.name))
        if self.is_power_on():
            return self.reset()
        else:
            return self.power_on()

## DEBUGGING ENTRY ##
if __name__ == '__main__':
    main()

