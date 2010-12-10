
# Beaker
#
# Copyright (C) Red Hat, Inc.
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

"""
A stub implementation of Cobbler's XML-RPC API. Used in tests to verify 
that Beaker is calling Cobbler correctly.
"""

import threading
import socket
from SimpleXMLRPCServer import SimpleXMLRPCServer
import logging
import time

log = logging.getLogger(__name__)

class StubCobbler(object):

    ACCEPTED_SYSTEM_KEYS = frozenset([
        'power_type',
        'power_address',
        'power_user',
        'power_pass',
        'power_id',
        'ksmeta',
        'kopts',
        'kopts_post',
        'profile',
        'netboot-enabled',
    ])
    ACCEPTED_POWER_ACTIONS = frozenset(['on', 'off', 'reboot'])
    ACCEPTED_PROFILE_KEYS = frozenset([
        'name',
        'kickstart',
        'parent',
    ])

    def __init__(self):
        self.systems = {}
        self.system_actions = {} #: system fdqn -> most recent power action
        self.incomplete_tasks = set()
        self.profiles = {}
        self.kickstarts = {}

    def version(self):
        return 2.0 # why is it a float? weird!

    def login(self, username, password):
        return 'logged_in'

    def get_system_handle(self, fqdn, token):
        assert token == 'logged_in'
        if fqdn not in self.systems:
            # pretend we had it all along
            self.systems[fqdn] = {}
        return 'StubCobblerSystem:%s' % fqdn

    def get_profile_handle(self, name, token):
        assert token == 'logged_in'
        if name not in self.profiles:
             # pretend we had it all along
             self.profiles[name] = {}
        return 'StubCobblerProfile:%s' % name

    def modify_system(self, system_handle, key, value, token):
        assert token == 'logged_in'
        assert system_handle.startswith('StubCobblerSystem:')
        fqdn = system_handle[len('StubCobblerSystem:'):]
        assert fqdn in self.systems
        assert key in self.ACCEPTED_SYSTEM_KEYS
        self.systems[fqdn][key] = value
        return True

    def save_system(self, system_handle, token):
        assert token == 'logged_in'
        assert system_handle.startswith('StubCobblerSystem:')
        fqdn = system_handle[len('StubCobblerSystem:'):]
        assert fqdn in self.systems
        # do nothing
        log.info('%r system %s saved with values %r', self,
                fqdn, self.systems[fqdn])
        return True

    def clear_system_logs(self, system_handle, token):
        assert token == 'logged_in'
        assert system_handle.startswith('StubCobblerSystem:')
        fqdn = system_handle[len('StubCobblerSystem:'):]
        assert fqdn in self.systems
        # do nothing
        return True

    def background_power_system(self, d, token):
        assert token == 'logged_in'
        fqdns = d['systems']
        action = d['power']
        assert action in self.ACCEPTED_POWER_ACTIONS
        for fqdn in fqdns:
            assert fqdn in self.systems
            self.system_actions[fqdn] = action
            log.info('%r power %s system %s', self, action, fqdn)
        task_handle = 'StubCobblerTask:%d' % int(time.time() * 1000)
        assert task_handle not in self.incomplete_tasks
        self.incomplete_tasks.add(task_handle)
        return task_handle

    def get_event_log(self, task_handle):
        assert task_handle in self.incomplete_tasks
        # always complete instantly, successfully
        self.incomplete_tasks.remove(task_handle)
        return '\n'.join(['### TASK COMPLETE ###', 'Stub cobbler did nothing'])

    def read_or_write_kickstart_template(self, filename, read, contents, token):
        assert token == 'logged_in'
        assert not read
        self.kickstarts[filename] = contents
        return True

    def modify_profile(self, profile_handle, key, value, token):
        assert token == 'logged_in'
        assert profile_handle.startswith('StubCobblerProfile:')
        name = profile_handle[len('StubCobblerProfile:'):]
        assert name in self.profiles
        assert key in self.ACCEPTED_PROFILE_KEYS
        self.profiles[name][key] = value
        return True

    def save_profile(self, profile_handle, token):
        assert token == 'logged_in'
        assert profile_handle.startswith('StubCobblerProfile:')
        name = profile_handle[len('StubCobblerProfile:'):]
        assert name in self.profiles
        # do nothing
        log.info('%r profile %s saved with values %r', self,
                name, self.profiles[name])
        return True

class NicerXMLRPCServer(SimpleXMLRPCServer):
    
    def __init__(self, addr):
        SimpleXMLRPCServer.__init__(self, addr, logRequests=False)
        self.timeout = 0.5
        self._running = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        SimpleXMLRPCServer.server_bind(self)

    # This is not necessary with Python 2.6:
    def serve_forever(self):
        self.socket.settimeout(self.timeout)
        while self._running:
            try:
                self.handle_request()
            except socket.timeout:
                pass

class StubCobblerThread(threading.Thread):

    def __init__(self):
        super(StubCobblerThread, self).__init__()
        self.daemon = True
        self.cobbler = StubCobbler()
        self._running = True
        self.port = 9010
        self.server = NicerXMLRPCServer(('localhost', self.port))
        self.server.register_introspection_functions()
        self.server.register_instance(self.cobbler)

    def stop(self):
        self.server._running = False
        self.join()

    def run(self):
        log.debug('Starting %r with %r', self.server, self.cobbler)
        try:
            self.server.serve_forever()
        finally:
            self.server.server_close()
