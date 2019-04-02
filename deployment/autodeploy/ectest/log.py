from datetime import datetime
import logging

def Start(filename, level=logging.DEBUG):
    logging.basicConfig(filename=filename, level=level)

# Logging
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
