#!/usr/bin/python
#
# SPDX-License-Identifier: Apache-2.0
#

import sys
import paramiko
import yaml


class SSHConnection:
    """ Perform commands through SSH to a remote host."""
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def open(self):
        try:
            self.ssh.connect(self.host, username=self.username, password=self.password)
        except paramiko.AuthenticationException:
            print("Authentication failure.")
            sys.exit(1)

    def close(self):
        self.ssh.close()

    def command(self, cmd, sudo=False):
        if sudo:
            cmd = "sudo -k -S -p '' {}".format(cmd)

        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        if sudo:
            stdin.write(self.password + '\n')
            stdin.flush()
        while not stdout.channel.exit_status_ready():
            # May hang but we don't care right now.
            continue

        out = stdout.readlines()
        err = stderr.readline()
        retcode = stdout.channel.recv_exit_status()
        return (out, err, retcode)

class Config:

    def load(self):
        try:
            with open('config.yaml') as f:
                lines = f.read()
        except FileNotFoundError:
            print ("Cannot find configuration file")
            raise

        data = yaml.load(lines, Loader=yaml.BaseLoader)
        if not data:
            print ("No data loaded from config file")
            return

        self.username = data['username']
        self.password = data['password']
        self.hosts = data['hosts']
        self.myip = data['myip']


def main():
    c = Config()
    c.load()
    for h in c.hosts:
        ssh = SSHConnection(h, c.username, c.password)
        ssh.open()
        print ("Downloading node_exporter in {}".format(h))
        cmd = "curl -o /usr/bin/node_exporter http://{}:8787/node_exporter".format(c.myip)
        out, err, retcode = ssh.command(cmd, sudo=True)
        if retcode:
            print ("Cannot download node_exporter")

        cmd = "chmod +x /usr/bin/node_exporter"
        out, err, retcode = ssh.command(cmd, sudo=True)

        print ("Downloading node_exporter.service in {}".format(h))
        cmd = "curl -o /etc/systemd/system/node_exporter.service http://{}:8787/node_exporter.service".format(c.myip)
        out, err, retcode = ssh.command(cmd, sudo=True)
        if retcode:
            print ("Cannot download node_exporter.service")

        print ("Downloading k8s policy")
        cmd = "curl -o policy.yaml http://{}:8787/policy.yaml".format(c.myip)
        out, err, retcode = ssh.command(cmd)
        if retcode:
            print ("Cannot download k8s policy: {}".format(err))

        cmd = "systemctl daemon-reload"
        out, err, retcode = ssh.command(cmd, sudo=True)

        print ("Enabling service in {}".format(h))
        cmd = "systemctl enable node_exporter.service"
        out, err, retcode = ssh.command(cmd, sudo=True)
        if retcode:
            print ("Cannot enable service")

        print ("Starting service in {}".format(h))
        cmd = "systemctl start node_exporter.service"
        out, err, retcode = ssh.command(cmd, sudo=True)
        if retcode:
            print ("Cannot start service")

        cmd = "KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f policy.yaml"
        out, err, retcode = ssh.command(cmd)
        if retcode:
            print ("Cannot apply policy: {}".format(err))


        ssh.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
