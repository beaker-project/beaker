
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import pkg_resources
import subprocess
import logging

log = logging.getLogger(__name__)

class CommandError(Exception):
    def __init__(self, command, status, stderr_output):
        Exception.__init__(self, 'Command %r failed '
                'with exit status %s:\n%s' % (command, status, stderr_output))
        self.status = status
        self.stderr_output = stderr_output

def run_command(script_filename, executable_filename, args=None, ignore_stderr=False):
    # XXX maybe find a better condition than this?
    if os.environ.get('BEAKER_CLIENT_COMMAND') == 'bkr':
        # Running in dogfood, invoke the real executable
        cmdline = [executable_filename] + (args or [])
    else:
        # Running from the source tree
        script = pkg_resources.resource_filename('bkr.server.tools', script_filename)
        cmdline = [sys.executable, script] + (args or [])
    p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode:
        raise CommandError(cmdline, p.returncode, err)
    if not ignore_stderr:
        assert err == '', err
    else:
        log.debug('Command %r completed successfully with stderr:\n%s', cmdline, err)
    return out
