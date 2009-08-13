# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import exceptions
import re
from sys import stderr
from beah.core import command

class CmdFilter(object):
    __ignore_re = re.compile('^\s*(.*?)\s*(#.*)?$')
    __cmd_re = re.compile('^(\S+).*$')
    __args_re = re.compile('^\S+(?:\s+(.*?))?$')
    __run_re = re.compile('^\S+\s+(\S+)$')

    def __init__(self):
        self.__handlers = {}

    def add_handler(self, handler, help='', *cmds):
        for cmd in cmds:
            self.__handlers[cmd] = (handler, help or handler.__doc__)

    # FIXME: this could block(?)
    # In case of cmd filter it is not crucial(?)
    def echo(self, msg):
        print msg
        return None

    def echoerr(self, msg):
        print >> stderr, msg
        return None

    def proc_cmd_quit(self, cmd, line):
        raise exceptions.StopIteration("quit")
    proc_cmd_q = proc_cmd_quit

    def proc_cmd_help(self, cmd, line):
        return self.echo(self.usage_msg())
    proc_cmd_h = proc_cmd_help

    def proc_cmd_ping(self, cmd, line):
        args = self.__args_re.match(line).group(1)
        return command.ping(args)

    def proc_cmd_PING(self, cmd, line):
        args = self.__args_re.match(line).group(1)
        return command.PING(args)

    def proc_cmd_dump(self, cmd, line):
        return command.command('dump')

    def proc_cmd_kill(self, cmd, line):
        return command.kill()

    def proc_cmd_run(self, cmd, line):
        # FIXME: add a proper option parser: -i --id=ID, -n --name=NAME
        m_run = self.__run_re.match(line)
        return command.run(m_run.group(1))
    proc_cmd_r = proc_cmd_run

    def proc_line(self, data):
        line = self.__ignore_re.match(data).group(1)
        if not line:
            return None

        cmd = self.__cmd_re.match(line).group(1)

        if "proc_cmd_"+cmd in dir(self):
            return self.__getattribute__("proc_cmd_"+cmd)(cmd=cmd, line=line)

        return self.echoerr("Command %s is not implemented. Input line: %s" % (cmd, line))

    def usage_msg(self):
        return """\
ping [MESSAGE]\n\tping a controller, response is sent to issuer only.
PING [MESSAGE]\n\tping a controller, response is broadcasted to all backends.
run TASK\nr TASK\trun a task. TASK is an executable.
kill\tkill a controller.
dump\tinstruct controller to print a diagnostics message on stdout.
quit\nq\tclose this backend.
help\nh\tprint this help message.
"""

if __name__ == '__main__':
    cp = CmdFilter()
    print cp.proc_line('r a')
    print cp.proc_line('run a_task')
    print cp.proc_line('ping')
    print cp.proc_line('ping hello world')
    print cp.proc_line('PING')
    print cp.proc_line('PING hello world')
    print cp.proc_line('help')
    print cp.proc_line('kill')
    print cp.proc_line('quit')
    #cp.proc_line('r')
