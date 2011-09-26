import subprocess
from bkr.labcontroller.config import get_conf
from bkr.log import add_rotating_file_logger as arfl

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

def die(logger, msg):

    # log the exception once in the per-task log or the main
    # log if this is not a background op.
    try:
       raise CX(msg)
    except:
       if logger is not None:
           log_exc(logger)

    # now re-raise it so the error can fail the operation
    raise CX(msg)

def log_exc(logger):
    """
    Log an exception.
    """
    (t, v, tb) = sys.exc_info()
    logger.info("Exception occured: %s" % t )
    logger.info("Exception value: %s" % v)
    logger.info("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))


def subprocess_sp(logger, cmd, shell=True):
    if logger is not None:
        logger.info("running: %s" % cmd)
    try:
        sp = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        if logger is not None:
            log_exc(logger)
        die(logger, "OS Error, command not found?  While running: %s" % cmd)

    data = sp.communicate()[0]
    rc = sp.returncode
    if logger is not None:
        logger.info("received: %s" % data)
    return data, rc

def subprocess_call(logger, cmd, shell=True):
    data, rc = subprocess_sp(logger, cmd, shell=shell)
    return rc

def subprocess_get(logger, cmd, shell=True):
    data, rc = subprocess_sp(logger, cmd, shell=shell)
    return data

