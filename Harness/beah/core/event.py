#!/usr/bin/env python

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
from beah.core.constants import RC, LOG_LEVEL

"""
Events are used to communicate events from Task to Controller and finally back
to Backend.

Classes:
    Event

Module contains many functions (e.g. idle, pong, start, end, etc.) to
instantiate Event of particular type.

Event is basically a list ['Event', evt, origin, timestamp, args] where:
    isinstance(evt, string)
    isinstance(origin, dict)
    isinstance(timestamp,float) or timestamp is None
    isinstance(args,dict)

"""

################################################################################
# PUBLIC INTERFACE:
################################################################################
def idle():
    """Event sent to newly registerred backend when Controller is idle"""
    return Event('idle')

def pong(origin={}, timestamp=None, message=None):
    """Event generated as a reposne to ping command"""
    if message:
        return Event('pong', origin={}, timestamp=None, message=message)
    return Event('pong', origin, timestamp)

def start(task_info, origin={}, timestamp=None):
    """Event generated when task is started"""
    return Event('start', origin, timestamp, task_info=task_info)

def end(task_info, rc, origin={}, timestamp=None):
    """Event generated when task finished"""
    return Event('end', origin, timestamp, task_info=task_info, rc=rc)

def echo(cmd, rc, message="", origin={}, timestamp=None, **kwargs):
    """Event generated as a response to a command"""
    return Event('echo', origin, timestamp, cmd=cmd, rc=rc, message=message, **kwargs)

def lose_item(data, origin={}, timestamp=None):
    """Event generated when unformatted data are received."""
    return Event('lose_item', origin, timestamp, data=data)

def output(data, out_handle="", origin={}, timestamp=None):
    return Event('output', origin, timestamp, out_handle=out_handle, data=data)
def stdout(data, origin={}, timestamp=None):
    return output(data, "stdout", origin, timestamp)
def stderr(data, origin={}, timestamp=None):
    return output(data, "stderr", origin, timestamp)

def output(data, out_handle="", origin={}, timestamp=None):
    return event('output', origin, timestamp, out_handle=out_handle, data=data)
def stdout(data, origin={}, timestamp=None):
    return output(data, "stdout", origin, timestamp)
def stderr(data, origin={}, timestamp=None):
    return output(data, "stderr", origin, timestamp)

def log(message="", log_level=LOG_LEVEL.INFO, log_handle="", origin={},
        timestamp=None, **kwargs):
    return Event('log', origin, timestamp, log_level=log_level,
            log_handle=log_handle, message=message, **kwargs)

def mk_log_level(log_level):
    def logf(message="", log_handle="", origin={}, timestamp=None, **kwargs):
        return Event('log', origin, timestamp, log_level=log_level,
                log_handle=log_handle, message=message, **kwargs)
    logf.__name__ = "log_level_%s" % log_level
    logf.__doc__ = "Create log event with log_level = %s" % log_level
    return logf

lfatal = mk_log_level(LOG_LEVEL.FATAL)
lcritical = mk_log_level(LOG_LEVEL.CRITICAL)
lerror = mk_log_level(LOG_LEVEL.ERROR)
lwarning = mk_log_level(LOG_LEVEL.WARNING)
linfo = mk_log_level(LOG_LEVEL.INFO)
ldebug1 = mk_log_level(LOG_LEVEL.DEBUG1)
ldebug2 = mk_log_level(LOG_LEVEL.DEBUG2)
ldebug3 = mk_log_level(LOG_LEVEL.DEBUG3)
ldebug = ldebug1

def result(rc, origin={}, timestamp=None, **kwargs):
    return Event('result', origin, timestamp, rc=rc, **kwargs)

def passed(origin={}, timestamp=None, **kwargs):
    return result(RC.PASS, origin=origin, timestamp=timestamp, **kwargs)

def warning(origin={}, timestamp=None, **kwargs):
    return result(RC.WARNING, origin=origin, timestamp=timestamp, **kwargs)

def failed(origin={}, timestamp=None, **kwargs):
    return result(RC.FAIL, origin=origin, timestamp=timestamp, **kwargs)

def critical(origin={}, timestamp=None, **kwargs):
    return result(RC.CRITICAL, origin=origin, timestamp=timestamp, **kwargs)

def fatal(origin={}, timestamp=None, **kwargs):
    return result(RC.FATAL, origin=origin, timestamp=timestamp, **kwargs)

################################################################################
# IMPLEMENTATION:
################################################################################
def event(evt, origin={}, timestamp=None, **kwargs):
    return Event(evt, origin, timestamp, **kwargs)

import time
class Event(list):
    def __init__(self, evt, origin={}, timestamp=None, **kwargs):
        list.__init__(self, ['Event', None, None, None, None]) # is this backwards compatible? Even with Python 2.3?
        if isinstance(evt, list):
            if evt[0] != 'Event':
                raise exceptions.TypeError('%r\'s first element has to be \'Event\'' % evt)
            self[1] = evt[1]
            self[2] = evt[2]
            self[3] = evt[3]
            self[4] = evt[4]
        else:
            self[1] = evt
            self[2] = origin
            self[3] = timestamp
            self[4] = kwargs

        for i in range(1,5):
            if callable(self[i]):
                self[i] = self[i](self)

        if self[3] is True:
            self[3] = time.time()

        for key in self[4].keys():
            if callable(self[4][key]):
                self[4][key] = self[4][key](self)

        if not isinstance(self.event(), str):
            raise exceptions.TypeError('%r not permitted as event. Has to be str.' % self.event())
        if not isinstance(self.origin(), dict):
            raise exceptions.TypeError('%r not permitted as origin. Has to be dict.' % self.origin())
        if not isinstance(self.args(), dict):
            raise exceptions.TypeError('%r not permitted as args. Has to be dict.' % self.args())
        if not isinstance(self.timestamp(), float) and not (self.timestamp() is None):
            raise exceptions.TypeError('%r not permitted as timestamp. Has to be float.' % self.timestamp())

    def event(self): return self[1]
    def origin(self): return self[2]
    def timestamp(self): return self[3]
    def args(self): return self[4]
    def arg(self, name, val=None):
        return self.args().get(name, val)

################################################################################
# TESTING:
################################################################################
if __name__=='__main__':
    import traceback, sys
    def test(expected, evt, origin={}, timestamp=None, **kwargs):
        try:
            answ = list(Event(evt, origin, timestamp, **kwargs))
            if answ != expected:
                print >> sys.stderr, "--- ERROR: Event(%r, %r) == %r != %r" % (evt,
                        kwargs, answ, expected)
        except:
            answ = sys.exc_type.__name__
            if answ != expected:
                print >> sys.stderr, "--- ERROR: Event(%r, %r) raised %r != %r" % (evt,
                        kwargs, answ, expected)
                traceback.print_exc()

    test(['Event', 'ping', {}, None, {}], 'ping')
    test('TypeError', 1)
    test(['Event', 'ping', {}, None, {}], evt='ping')
    test('TypeError', evt=1)
    test('TypeError', evt='ping', origin='')
    test('TypeError', evt='ping', origin={}, timestamp='')
    test(['Event', 'ping', {}, None, {'value':1}], evt='ping', value=1)
    test(['Event', 'ping', {}, None, {'value':1}], **{'evt':'ping', 'value':1})
    test(['Event', 'ping', {}, None, {'value':1}], value=1, evt='ping')
    test(['Event', 'ping', {}, None, {'value':1}], **{'value':1, 'evt':'ping'})

