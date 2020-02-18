import os
import subprocess as SP

try:
    import ectest.log as LOG
except:
    import log as LOG

CurrPath = os.path.join(os.path.abspath(os.getcwd()))

def shell(cmd, cwd=None, logfile=None, silent=False, DEBUG=False):
    realcmd = cmd
    if DEBUG:
        realcmd = "echo \"%s\"" % cmd
    result = None
    retval = 0

    if cwd != None:
        os.chdir(cwd)
    try:
        result = SP.check_output(realcmd, shell = True).splitlines()
    except SP.CalledProcessError as ecp:
        if not silent:
            LOG.Error("ERROR: failed to run \"%s\": returned %s" % (cmd, ecp.returncode))
            LOG.print_error(ecp.output.splitlines())
        retval = ecp.returncode
        retlog = ecp.output.splitlines()
    except Exception as error:
        if not silent:
            LOG.Error("ERROR: failed to run \"%s\": %s" % (cmd, error))
        retval = -1

    result_str = []
    if result:
        for l in result:
            if isinstance(l, bytes):
                result_str.append(l.decode(encoding="utf-8", errors="strict"))
            else:
                result_str = result
                break

    if logfile != None:
        with open(logfile, "w") as f:
            for l in result_str:
                f.write(l)
                f.write("\n")
    if cwd != None:
        os.chdir(CurrPath)

    return retval, result_str

class stoppable_task():
    cmd = None
    cwd = None
    running_process = None
    stop_event = None
    stdout = None
    stderr = None
    filename = None
    logfile = None

    def __init__(self, cmd, stop_event, cwd=None, filename=None):
        self.cmd = cmd
        if cwd:
            self.cwd = cwd
        self.stop_event = stop_event

        if filename:
            self.filename = filename
            self.logfile = open(self.filename, "a")
            self.stdout = self.logfile
            self.stderr = self.logfile
        else:
            self.stdout = SP.PIPE
            self.stderr = SP.PIPE

        self.running_process = SP.Popen(
            cmd.split(),
            cwd=cwd,
            stdout=self.stdout,
            stderr=self.stderr)

    def wait(self):
        if not self.running_process or not self.stop_event:
            return -1, ["Error to launch the cmd %s" % self.cmd]

        while self.running_process.poll() == None and not self.stop_event.is_set():
            self.stop_event.wait(timeout=5)
        if self.stop_event.is_set():
            try:
                self.running_process.terminate()
            except:
                pass

        returncode = self.running_process.poll()
        if self.filename:
            self.logfile.flush()
            self.logfile.close()
            return returncode, []
        else:
            (stdoutdata, stderrdata) = self.running_process.communicate()
            return returncode, stdoutdata
