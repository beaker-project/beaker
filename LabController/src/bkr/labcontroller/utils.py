
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess
import logging
from bkr.labcontroller.config import get_conf

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


def get_console_files(console_logs_directory, system_name):
    """Return a list of the console log files for a system

    Given a path to the console_logs_directory and the FQDN (Fully Qualified
    Domain Name) of the system. Search the console_logs_directory and return a
    list containing tuples of the full path name to the log file and the name
    to use when uploading the logfile for log files that are for system_name.

    :param console_logs_directory: Path to the console logs directory
    :param system_name: Fully qualified domain name of the system
    :return: List[Tuple[absolute path to log file, name to use for log file]]
    """
    if not os.path.isdir(console_logs_directory):
        logger.info("Console files directory does not exist: %s",
                    console_logs_directory)
        return []

    if not system_name:
        logger.info("No System Name for console log file...Ignoring")
        return []

    output = []
    for filename in sorted(os.listdir(console_logs_directory)):
        if filename.startswith(system_name):
            full_path = os.path.join(console_logs_directory, filename)
            if filename == system_name:
                logfile_name = "console.log"
            else:
                description = filename[len(system_name):]
                # Remove leading hyphens
                description = description.lstrip('-')
                logfile_name = "console-{}.log".format(description)
            output.append((full_path, logfile_name))
    return output
