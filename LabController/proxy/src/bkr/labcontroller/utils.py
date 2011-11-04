import subprocess
import logging
from bkr.labcontroller.config import get_conf
from bkr.log import add_rotating_file_logger as arfl

logger = logging.getLogger(__name__)

def add_rotating_file_logger(*args, **kw):
    conf = get_conf()
    max_bytes = conf.get('LOG_MAXBYTES')
    backup_count = conf.get('LOG_BACKUPCOUNT')
    file_logger_kw = kw
    if backup_count:
        file_logger_kw.update({'backupCount' : backup_count})
    if max_bytes:
        file_logger_kw.update({'maxBytes' : max_bytes})
    return arfl(*args, **file_logger_kw)

def subprocess_sp(cmd, shell=True):
    logger.debug("running: %s", cmd)
    try:
        sp = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        logger.exception("OS Error, command not found?  While running: %s", cmd)
        raise

    data = sp.communicate()[0]
    rc = sp.returncode
    logger.debug("received: %s" % data)
    return data, rc

def subprocess_call(cmd, shell=True):
    data, rc = subprocess_sp(cmd, shell=shell)
    return rc

def subprocess_get(cmd, shell=True):
    data, rc = subprocess_sp(cmd, shell=shell)
    return data

