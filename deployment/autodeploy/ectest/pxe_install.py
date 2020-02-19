"""
Bare Metal Utils:
    PxeAgent: mount StarlingX ISO to pxe server.
    Node: ipmitool wrapper to control StarlingX test nodes.

Pre-Condition:
    1. Install dnsmasq:
        sudo apt-get install dnsmasq

    2. Set your computer to use a static IP

    3. Configure dnsmasq add these lines to /etc/dnsmasq.conf
        interface=<nic_name_for_pxe_server>
        bind-interfaces
        dhcp-range=10.10.10.150,10.10.10.254 # dhcp IP range.
        dhcp-boot=grubx64.efi
        enable-tftp
        tftp-root=/var/lib/tftpboot/uefi # root for tftp server

        # Static IP map for the testnodes
        dhcp-host=a0:36:9f:c8:9b:8d,10.10.10.173 # should be in dhcp-range

    4. Reload dnsmasq
        sudo service dnsmasq restart

Config Files:
    Located in testnode_config folder.
    testnode_config
      |- pxe_server.json  # config file for pxe server

"""

import json
import os
import re
import shutil

try:
    import ectest.log as LOG
    import ectest.cmd as CMD
    import ectest.utils as UTILS
    import ectest.testnode as NODE
except:
    import log as LOG
    import cmd as CMD
    import utils as UTILS
    import testnode as NODE

MODE_UEFI_STD = 1
MODE_UEFI_AIO = 2
MODE_UEFI_AIO_LL = 3

MODE_BIOS_STD = 2
MODE_BIOS_AIO = 4
MODE_BIOS_AIO_LL = 6

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bare Metal Installer")
    parser.add_argument('pxe_config',
        help="Config file for pxe service", type=str)
    parser.add_argument('iso',
        help="The ISO file to deploy", type=str)
    parser.add_argument('controller0_config',
        help="Test Node for Controller0.", type=str)
    parser.add_argument('install_mode',
        help="Install mode for the specific ISO. 1: standard, 2: AIO, 3: AIO Low Latency", type=int,
        default=MODE_UEFI_AIO,
        choices=[
            MODE_UEFI_STD,
            MODE_UEFI_AIO,
            MODE_UEFI_AIO_LL
        ])

    args = parser.parse_args()

    pxe_agent = PxeAgent(
        pxe_server_config_json=args.pxe_config,
        iso=args.iso,
        default_install=args.install_mode)
    pxe_agent.mount_iso()

    node = NODE.Node_BM(args.controller0_config, "sysadmin", "Local.123")
    pxe_agent.prepare_for_node(node)
    pxe_agent.check_pxe_services()

    node.power_off()
    node.boot_to_pxe()
    print("OAM IF: %s" % node.get_oam_ip())


class PxeAgent(object):
    """Handle PXE services and mount ISO for Installation"""

    def __init__(self, pxe_server_config_json, iso, default_install=0):
        '''
        pxe_server_config_json: json file to describe pxe server.
        iso: ISO file to install.
        default_install: install mode for uefi mode
                0: boot from hard disk
                1: standard controller
                2: all-in-one controller
                3: all-in-one controoler (low-latency)
        '''
        CONFIG = UTILS.load_json_config(pxe_server_config_json)

        CONFIG["iso"] = os.path.abspath(iso)
        CONFIG["default_install"] = default_install
        for tag in ["tftp_dir", "mnt_point", "http_root"]:
            CONFIG[tag] = os.path.abspath(CONFIG[tag])

        self.iso = CONFIG["iso"]
        self.iso_name = os.path.basename(self.iso).replace('.iso', '')
        self.tftp_dir = CONFIG["tftp_dir"]
        self.mnt_point = CONFIG["mnt_point"]
        self.http_server = CONFIG["http_server"]
        self.http_mnt_point = os.path.join(CONFIG["http_root"], CONFIG["prj_name"])
        self.prj_name = CONFIG["prj_name"]
        self.default_install = CONFIG["default_install"]
        self.CONFIG = CONFIG

        CMD.shell("sudo mkdir -p %s" % self.http_mnt_point)

    def __print_errorlog(self, module, log):
        for l in log:
            LOG.Error(module + ": " + l)

    def __umount_point(self, mnt_point):
        umounting_attempts = 3

        while umounting_attempts > 0:
            ret, log = CMD.shell('sudo umount -l {}'.format(mnt_point))

            if ret != 0 and umounting_attempts:
                LOG.Info('Failed to umount {}, retrying...'.format(
                    mnt_point))
            elif ret != 0 and not umounting_attempts:
                LOG.Error('Max umounting attempts reached, leaving '
                         'installation')
                __print_errorlog("UMOUNT", log)
                exit(1)
            else:
                break

            umounting_attempts -= 1

    def __mount_point(self, mnt_point, iso):
        if os.listdir(mnt_point):
            LOG.Info('{} is already mounted, umounting'.format(mnt_point))
            self.__umount_point(mnt_point)

        ret, log = CMD.shell('sudo mount {0} {1}'.format(self.iso, mnt_point))
        if ret == 0:
            LOG.Info('ISO mounted on {}'.format(mnt_point))
        else:
            __print_errorlog("MOUNT", log)
            exit(1)

    def __remove_folder(self, folder):
        if os.path.exists(folder):
            CMD.shell("sudo rm -rf %s" % folder)
            # shutil.rmtree(folder)
        return folder

    def __create_folder(self, folder):
        self.__remove_folder(folder)
        CMD.shell("sudo mkdir -p %s" % folder)
        # os.makedirs(folder)
        return folder

    def __get_bios_install_label(self):
        if self.default_install == MODE_UEFI_STD:
            return MODE_BIOS_STD
        if self.default_install == MODE_UEFI_AIO:
            return MODE_BIOS_AIO
        if self.default_install == MODE_UEFI_AIO_LL:
            return MODE_BIOS_AIO_LL

    def mount_iso(self):
        """Mounting ISO and prepare pxe tftp server"""

        ## clean up test environment
        http_root = self.__remove_folder(
            os.path.join(self.http_mnt_point, self.iso_name))
        tftp_dir = self.__remove_folder(self.tftp_dir)

        ## Setup pxe install folder on tftp server
        self.__mount_point(self.mnt_point, self.iso)
        CMD.shell(
            "sudo %s/pxeboot_setup.sh "
            "-u http://%s/%s/%s "
            "-t %s" % (
                self.mnt_point,
                self.http_server, self.prj_name, self.iso_name,
                self.tftp_dir
            ))
        self.__umount_point(self.mnt_point)

        cmds = []
        cmds.append("sudo chmod 777 %s" % self.tftp_dir)

        ######## MODIFY INSTALL LABEL FOR UEFI BOOT
        # Modify default install option
        cmds.append("sudo sed -i -e \"s,default=0,default=%s,\" %s/grub.cfg" % (
            str(self.default_install), self.tftp_dir))
        # Modify timeout
        cmds.append("sudo sed -i -e \"s,timeout=10,timeout=3,\" %s/grub.cfg" % self.tftp_dir)
        # Modify console (always use graphic console)
        cmds.append("sudo sed -i -e \"s,serial console=ttyS0\\,115200n8,console=tty0,\" "
            "%s/grub.cfg" % (self.tftp_dir))
        # Backup grub.cfg
        cmds.append("sudo cp %s/grub.cfg %s/grub.cfg.bak" % (
            self.tftp_dir, self.tftp_dir))

        ######## MODIFY INSTALL LABEL FOR BIOS BOOT
        # Modify default install option
        cmds.append("sudo sed -i -e \"s,DEFAULT menu\\.c32,DEFAULT %s,\" %s/pxeboot.cfg" % (
            str(self.__get_bios_install_label()), self.tftp_dir))
        # Modify timeout
        cmds.append("sudo sed -i -e \"s,TIMEOUT 100,TIMEOUT 3,\" %s/pxeboot.cfg" % self.tftp_dir)
        # Backup pxeboot.cfg
        cmds.append("sudo cp %s/pxeboot.cfg %s/pxeboot.cfg.bak" % (
            self.tftp_dir, self.tftp_dir))

        # No change for the default password
        cmds.append("sed -i 's/chage -d 0 sysadmin/#chage -d 0 sysadmin/g' "
            "`grep \"chage -d 0 sysadmin\" %s -rl `" % self.tftp_dir)
        # Symbol link to http server
        cmds.append("sudo ln -s %s %s" % (self.tftp_dir, http_root))
        #####
        CMD.shell("; ".join(cmds))

        ## PXE server boot_file set as grubx64.efi
        CMD.shell("sudo cp EFI/grubx64.efi grubx64.efi", cwd=self.tftp_dir)

    def prepare_for_node(self, node):
        cmds = []
        # Special grub.cfg for the node
        cmds.append("sudo cp %s/grub.cfg.bak %s/grub.cfg" % (
            self.tftp_dir, self.tftp_dir))
        # Modify boot_device and rootfs_device
        cmds.append("sudo sed -i -e \"s,boot_device=sda,boot_device=%s,\" %s/grub.cfg" % (
            node.get_boot_device(), self.tftp_dir))
        cmds.append("sudo sed -i -e \"s,rootfs_device=sda,rootfs_device=%s,\" %s/grub.cfg" % (
            node.get_rootfs_device(), self.tftp_dir))

        # Special pxeboot.cfg for the node
        cmds.append("sudo cp %s/pxeboot.cfg.bak %s/pxeboot.cfg" % (
            self.tftp_dir, self.tftp_dir))
        # Modify boot_device and rootfs_device
        cmds.append("sudo sed -i -e \"s,boot_device=sda,boot_device=%s,\" %s/pxeboot.cfg" % (
            node.get_boot_device(), self.tftp_dir))
        cmds.append("sudo sed -i -e \"s,rootfs_device=sda,rootfs_device=%s,\" %s/pxeboot.cfg" % (
            node.get_rootfs_device(), self.tftp_dir))

        #####
        CMD.shell("; ".join(cmds))

    @staticmethod
    def check_pxe_services():
        """
        """
        services = ['dnsmasq']
        for service in services:
            LOG.Info("Restarting %s ..." % service)
            CMD.shell('sudo systemctl restart {}'.format(service))

    @staticmethod
    def close_pxe_services():
        """
        """
        services = ['dnsmasq']
        for service in services:
            LOG.Info("Stopping %s ..." % service)
            CMD.shell('sudo systemctl stop {}'.format(service))


## DEBUGGING ENTRY ##
if __name__ == '__main__':
    main()



