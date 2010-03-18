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
import os.path
import shlex
from sys import stderr
from optparse import OptionParser
from beah.core import command, new_id

class CmdFilter(object):

    __ignore_re = re.compile('^\s*(.*?)\s*(#.*)?$')
    __cmd_re = re.compile('^(\S+).*$')
    __args_re = re.compile('^\S+(?:\s+(.*?))?$')
    __varre = re.compile('''^([a-zA-Z_][a-zA-Z0-9_]*)=(.*)$''')

    __run_opt = OptionParser()
    __run_opt.add_option("-n", "--name", action="store", dest="name",
            help="task name")
    __run_opt.add_option("-D", "--define", action="append", dest="variables",
            metavar="VARIABLES",
            help="VARIABLES specify list of overrides.")

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

    def proc_cmd_quit(self, cmd, cmd_args):
        raise exceptions.StopIteration("quit")
    proc_cmd_q = proc_cmd_quit

    def proc_cmd_help(self, cmd, cmd_args):
        return self.echo(self.usage_msg())
    proc_cmd_h = proc_cmd_help

    def proc_cmd_ping(self, cmd, cmd_args):
        if cmd_args:
            message = ' '.join(cmd_args)
        else:
            message = None
        return command.ping(message)

    def proc_cmd_PING(self, cmd, cmd_args):
        if cmd_args:
            message = ' '.join(cmd_args)
        else:
            message = None
        return command.PING(message)

    def proc_cmd_dump(self, cmd, cmd_args):
        return command.Command('dump')

    def proc_cmd_kill(self, cmd, cmd_args):
        return command.kill()

    def proc_cmd_run(self, cmd, cmd_args):
        opts, args = self.__run_opt.parse_args(cmd_args)
        if len(args) < 1:
            raise exceptions.RuntimeError('file to run must be provided.')
        variables = {}
        if opts.variables:
            for pair in opts.variables:
                key, value = self.__varre.match(pair).group(1, 2)
                variables[key] = value
        return command.run(os.path.abspath(args[0]), name=opts.name or args[0],
                env=variables, args=args[1:])
    proc_cmd_r = proc_cmd_run

    def proc_line(self, data):
        args = shlex.split(data, True)
        if not args:
            return None
        cmd = args[0]
        f = getattr(self, "proc_cmd_"+cmd, None)
        if f:
            return f(cmd=cmd, cmd_args=args[1:])
        return self.echoerr("Command %s is not implemented. Input line: %s" % (cmd, line))

    def usage_msg(self):
        return """\
ping [MESSAGE]\n\tping a controller, response is sent to issuer only.
PING [MESSAGE]\n\tping a controller, response is broadcasted to all backends.
run [OPTS] TASK [ARGS]\nr TASK\trun a task. TASK is an executable.
\tOptions:
\t-n --name=NAME -- task name
\t-D --define VARIABLE=VALUE -- define environment variable VARIABLE.
kill\tkill a controller.
dump\tinstruct controller to print a diagnostics message on stdout.
quit\nq\tclose this backend.
help\nh\tprint this help message.
"""

if __name__ == '__main__':
    cp = CmdFilter()
    def test_(result, expected):
        if not result.same_as(expected):
            print "--- ERROR: result is not same as expected"
            print "result: %r" % (result,)
            print "expected: %r" % (expected,)
            assert False
    test_(cp.proc_line('r a'), command.run(os.path.abspath('a'), name='a', args=[], env={}))
    test_(cp.proc_line('run a_task'), command.run(os.path.abspath('a_task'),
        name='a_task', args=[], env={}))
    test_(cp.proc_line('run -n NAME a_task'), command.run(os.path.abspath('a_task'),
        name='NAME', args=[], env={}))
    test_(cp.proc_line('run -D VAR=VAL -D VAR2=VAL2 a_task'), command.run(os.path.abspath('a_task'),
        name='a_task', args=[], env={'VAR':'VAL', 'VAR2':'VAL2'}))
    test_(cp.proc_line('run a_task arg1 arg2'), command.run(os.path.abspath('a_task'),
        name='a_task', args=['arg1', 'arg2'], env={}))
    test_(cp.proc_line('ping'), command.ping())
    test_(cp.proc_line('ping hello world'), command.ping('hello world'))
    test_(cp.proc_line('PING'), command.PING())
    test_(cp.proc_line('PING hello world'), command.PING('hello world'))
    cp.proc_line('help')
    test_(cp.proc_line('kill'), command.command('kill'))
    print cp.proc_line('quit')
    #cp.proc_line('r')
