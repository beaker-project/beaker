import subprocess
import logging
from bkr.labcontroller.config import get_conf
from bkr.log import add_rotating_file_logger as arfl

logger = logging.getLogger(__name__)

class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


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

def check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: non_existent_file: No such file or directory\n'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output=output)
    return output

