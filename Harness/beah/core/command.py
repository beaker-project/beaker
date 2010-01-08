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
import sys
from beah.core import event, new_id
from beah.misc import setfname

"""
Commands are used to send instructions from Backend to Controller (and
eventually Task.)
"""

################################################################################
# PUBLIC INTERFACE:
################################################################################
def ping(message=None):
    if message:
        return command('ping', message=message)
    return command('ping')

def PING(message=None):
    if message:
        return command('PING', message=message)
    return command('PING')

def run(file, name=None, env=None, args=None):
    if name is None:
        name = file
    return command('run', task_info={'file':file, 'name':name}, env=env, args=args)

def run_this(script, name=None, env=None, args=None):
    return command('run_this', script=script, task_info={'name':name}, env=env, args=args)

def kill():
    return command('kill')

def no_input():
    return command('no_input')

def no_output():
    return command('no_output')

def variable_value(key, value, handle='', **kwargs):
    """Used to return a "variable's" value to task."""
    return command('variable_value', key=key, value=value, handle=handle,
            **kwargs)

def forward(event, host, port=None):
    """
    Used to forward an event to another controller.

    @event - the original event.
    @host, @port - host and port where remote controller is listening.

    event.forward_response could be used in answer. Sending answer is required
    before sending event.echo. command.forward is recommended afterwards, as
    connection could be closed.
    """
    return command('forward', event=event, destination=(host, port))

################################################################################
# IMPLEMENTATION:
################################################################################
def command(cmd, **kwargs):
    return Command(cmd, **kwargs)

def mkcommand(cmd, __doc__="", **kwargs):
    def cmdf(**kwargs):
        return command(cmd)
    setfname(cmdf, cmd)
    cmdf.__doc__ = __doc__ or "Command %s" % cmd
    return cmdf

class Command(list):

    COMMAND = 1
    ID = 2
    ARGS = 3

    if sys.version_info[1] < 4:
        # FIXME: Tweak to make it Python 2.3 compatible
        TESTTYPE = (str, unicode)
    else:
        TESTTYPE = str

    def __init__(self, cmd, id=None, **kwargs):
        if isinstance(cmd, Command):
            list.__init__(self, cmd)
            return
        list.__init__(self, ['Command', None, None, None]) # is this backwards compatible? Even with Python 2.3?
        if isinstance(cmd, list):
            if cmd[0] != 'Command' or not isinstance(cmd[self.COMMAND], self.TESTTYPE) or not isinstance(cmd[self.ARGS], dict):
                raise exceptions.TypeError('%r not permitted. Has to be [\'Command\', str, str, dict]' % cmd)
            self[self.COMMAND] = str(cmd[self.COMMAND])
            self[self.ID] = cmd[self.ID]
            self[self.ARGS] = dict(cmd[self.ARGS])
        elif isinstance(cmd, self.TESTTYPE):
            self[self.COMMAND] = str(cmd)
            self[self.ID] = id
            self[self.ARGS] = dict(kwargs)
        else:
            raise exceptions.TypeError('%s not permitted as command, it has to be an instance of list or str' % cmd.__class__.__name__)

        if self[self.ID] is None:
            self[self.ID] = new_id()
        if not isinstance(self.id(), self.TESTTYPE):
            raise exceptions.TypeError('%r not permitted as id. Has to be str.' % self.id())

    def command(self):
        return self[self.COMMAND]
    def id(self):
        return self[self.ID]
    def args(self):
        return self[self.ARGS]
    def arg(self, name, val=None):
        return self.args().get(name, val)

################################################################################
# TESTING:
################################################################################
if __name__=='__main__':
    import traceback, sys
    def test(expected, cmd, **kwargs):
        try:
            answ = list(Command(cmd, **kwargs))
            if answ != expected:
                print >> sys.stderr, "--- ERROR: Command(%r, %r) == %r != %r" % (cmd,
                        kwargs, answ, expected)
        except:
            answ = sys.exc_type.__name__
            if answ != expected:
                print >> sys.stderr, "--- ERROR: Command(%r, %r) raised %r != %r" % (cmd,
                        kwargs, answ, expected)
    test(['Command', 'ping', '99', {}], 'ping', id='99')
    test('TypeError', 1)
    test(['Command', 'ping', '99', {}], cmd='ping', id='99')
    test('TypeError', cmd=1)
    test(['Command', 'ping', '99', {'value':1}], cmd='ping', value=1, id='99')
    test(['Command', 'ping', '99', {'value':1}], **{'cmd':'ping', 'value':1, 'id':'99'})
    test(['Command', 'ping', '99', {'value':1}], value=1, cmd='ping', id='99')
    test(['Command', 'ping', '99', {'value':1}], **{'value':1, 'cmd':'ping', 'id':'99'})

