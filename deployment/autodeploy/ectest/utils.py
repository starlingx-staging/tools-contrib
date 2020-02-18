import os
import subprocess as SP
import shutil
import json
import time

try:
    import ectest.log as LOG
    import ectest.cmd as CMD
except:
    import log as LOG
    import cmd as CMD

SSH_LOG_FLAG = "==SSH_LOG=="
TEST_KEY = "~/.ssh/testkey"
TEST_PUBKEY = "%s/.ssh/testkey.pub" % os.environ['HOME']

def run_expect_cmd_with_password(cmd, password, cwd=None, logfile=None, silent=False):

    ecmds = []
    ecmds.append("spawn %s" % cmd)
    ecmds.append("expect {")
    ecmds.append("  \"*assword:*\" {")
    ecmds.append("    send \"%s\\r\"" % password)
    ecmds.append("    expect \"*$ \"")
    ecmds.append("  }")
    ecmds.append("  \"*password for sysadmin:*\" {")
    ecmds.append("    send \"%s\\r\"" % password)
    ecmds.append("    expect \"*$ \"")
    ecmds.append("  }")
    ecmds.append("  \"*$ \"")
    ecmds.append("}")
    ecmds.append("lassign [wait] pid spawnid os_error_flag value")
    ecmds.append("exit $value")

    # LOG.print_log(ecmds)

    retval, retlog = CMD.shell(
        "expect -c '\n"
        "%s\n"
        "' 2>&1" % "\n".join(ecmds),
        cwd=cwd, logfile=logfile, silent=silent)

    return retval, retlog

def scp_to_server(src, dst, server, user, password=None, cwd=None, logfile=None, silent=True):
    scpcmd = "scp -r -oStrictHostKeyChecking=no -oCheckHostIP=no "  \
             "%s %s@%s:%s" % (src, user, server, dst)
    if password:
        retval, retlog = run_expect_cmd_with_password(scpcmd, password,
            cwd=cwd, logfile=logfile, silent=silent)
    else:
        retval, retlog = CMD.shell(scpcmd,
            cwd=cwd, logfile=logfile, silent=silent)

    for l in retlog:
        if l.find("No such file") >= 0:
            retval = 1
    remove_ssh_log_head(retlog)
    return retval, retlog

def scp_from_server(src, dst, server, user, password=None, cwd=None, logfile=None, silent=True):
    scpcmd = "scp -r -oStrictHostKeyChecking=no -oCheckHostIP=no "  \
             "%s@%s:%s %s" % (user, server, src, dst)
    if password:
        retval, retlog = run_expect_cmd_with_password(scpcmd, password,
            cwd=cwd, logfile=logfile, silent=silent)
    else:
        retval, retlog = CMD.shell(scpcmd,
            cwd=cwd, logfile=logfile, silent=silent)

    for l in retlog:
        if l.find("No such file") >= 0:
            retval = 1
    remove_ssh_log_head(retlog)
    return retval, retlog

def add_sshkey_config(server, user):
    ssh_config = "%s/.ssh/config" % os.environ['HOME']
    if os.path.exists(ssh_config):
        retval, retlog = CMD.shell("grep \"%s\" %s" % (server, ssh_config), silent=True)
        if retval == 0:
            LOG.Warning("%s already configured in .ssh/config." % server)
            return

    config_ssh = []
    config_ssh.append("Host %s" % server)
    config_ssh.append("    IdentityFile %s" % TEST_KEY)
    config_ssh.append("    User %s" % user)
    for config in config_ssh:
        CMD.shell("echo \"%s\" >> %s" % (config, ssh_config))

def create_secure_path(server, user, password):
    cmd = "ssh -t -oStrictHostKeyChecking=no -oCheckHostIP=no "  \
          "%s@%s mkdir -p ~/.ssh" % (user, server)
    retval, retlog = run_expect_cmd_with_password(cmd, password)
    if retval != 0:
        return retval, retlog

    if not os.path.exists(TEST_PUBKEY):
        LOG.Info("pubkey %s not existing, generate new key" % TEST_PUBKEY)
        ret, log = CMD.shell("ssh-keygen -o -f %s -P \"\"" % TEST_KEY)
        LOG.print_log(log)
    add_sshkey_config(server, user)

    retval, retlog = scp_to_server(
        TEST_PUBKEY,
        "~/.ssh/authorized_keys",
        server, user, password)

    return retval, retlog

def secure_ssh(cmd, server, user, password=None, cwd=None, logfile=None, silent=False):
    if not silent:
        LOG.Info("EXEC >>> %s@%s: \"%s\"" % (user, server, cmd))
    head = "ssh -t -oStrictHostKeyChecking=no -oCheckHostIP=no "  \
           "%s@%s" % (user, server)    
    if password:
        sshcmd = "%s %s" % (head, cmd)
        retval, retlog = run_expect_cmd_with_password(sshcmd, password,
            cwd=cwd, logfile=logfile, silent=silent)
        for l in retlog:
            if l.find("spawn id exp4 not open") >= 0:
                retval = 1
                break
    else:
        sshcmd = "%s 'echo \"%s\"; %s' 2>&1" % (head, SSH_LOG_FLAG, cmd)
        retval, retlog = CMD.shell(sshcmd,
            cwd=cwd, logfile=logfile, silent=silent)

    remove_ssh_log_head(retlog)
    return retval, retlog

def remove_ssh_log_head(log):
    head = []
    found = False
    for l in log:
        head.append(l)
        if l == SSH_LOG_FLAG or l.find("assword") >= 0:
            found = True
            break
    if found:
        for h in head:
            log.remove(h)

def load_json_config(json_config):
    if not json_config: return None
    CONFIG = {}
    try:
        with open(json_config, "r") as f:
            CONFIG = json.load(f)
    except json.decoder.JSONDecodeError as e:
        LOG.Error("%s is not in json format." % json_config)
        exit(1)
    except FileNotFoundError as e:
        LOG.Error("%s not found." % json_config)
        exit(1)
    return CONFIG

class wait_for():
    check_func = None
    interval = 10

    def __init__(self, msg, check_func, interval=10, slowdown=1):
        LOG.Info("Waiting for " + msg)
        self.check_func = check_func
        self.interval = interval
        self.slowdown = slowdown

    def run(self, minutes):
        rounds = (int)(minutes * 60 * self.slowdown / self.interval)
        for i in range(rounds):
            LOG.InProgress()
            if self.check_func and self.check_func():
                LOG.EndProgress("Finished")
                return 0
            time.sleep(self.interval)

        LOG.EndProgress("TIMEOUT")

        return -1

# system level functions
def check_file_exist(f):
    if os.path.exists(f):
        return True
    LOG.Error("%s is not existing" % f)
    return False

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

def save_json_config(config, fn):
    with open(fn, "w") as outfile:
        json.dump(config, outfile, indent=2)

def check_ret(result, func_exit_failure=None, log=None):
    if isinstance(result, bool):
        if not result:
            if func_exit_failure:
                func_exit_failure()
            LOG.Error(log)
            return -1
    elif isinstance(result, int) and 0 != result:
        if func_exit_failure:
            func_exit_failure()
        LOG.Error(log)
        return -1
    elif isinstance(result, tuple) and 0 != result[0]:
        if func_exit_failure:
            func_exit_failure()
        LOG.Error(log)
        return -1
    return 0

# other utils
def update_json_config(json_config, overwrite):
    for k in overwrite:
        if k in json_config and isinstance(json_config[k], dict):
            json_config[k].update(overwrite[k])
        else:
            json_config[k]= overwrite[k]

## DEBUGGING ENTRY ##
if __name__ == '__main__':
    print("### Run cmd on server with password.")
    retval, retlog = secure_ssh("ls", "10.10.10.3", "sysadmin", password="sysadmin")
    print("Result Value: %d" % retval)
    LOG.print_log(retlog)

    print("### Create secure path.")
    create_secure_path("10.10.10.3", "sysadmin", password="sysadmin")

    print("### Run cmd on server without password.")
    retval, retlog = secure_ssh("ls", "10.10.10.3", "sysadmin")
    print("Result Value: %d" % retval)
    LOG.print_log(retlog)

    print("### Run cmd for unreachable server.")
    retval, retlog = secure_ssh("ls", "10.10.10.5", "sysadmin", password="sysadmin", silent=True)
    print("Result Value: %d" % retval)
    LOG.print_log(retlog)

