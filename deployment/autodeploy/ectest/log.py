from datetime import datetime
import logging

def Start(filename, level=logging.DEBUG):
    logging.basicConfig(filename=filename, level=level)

# Logging
def InProgress():
    import sys
    sys.stdout.write('.')
    sys.stdout.flush()
def EndProgress(msg):
    print(msg)

def Info(msg, silent=False):
    print("INFO: %s" % msg)
    if not silent:
        logging.info(msg)
def Debug(msg):
    print("DEBUG: %s" % msg)
    logging.debug(msg)
def Warning(msg):
    print("WARNING: %s" % msg)
    logging.warning(msg)
def Error(msg):
    print("ERROR: %s" % msg)
    logging.error(msg)

def Time(msg):
    Info("# %s at %s ####" % (msg, datetime.now().strftime('%Y-%m-%d_%H-%M-%S')))

def print_log(log):
    if isinstance(log, list):
        for l in log:
            Info(l)
    else:
        Info(str(log))

def print_error(log):
    if isinstance(log, list):
        for l in log:
            Error(l)
    else:
        Error(str(log))

def print_warning(log):
    if isinstance(log, list):
        for l in log:
            Warning(l)
    else:
        Warning(str(log))


