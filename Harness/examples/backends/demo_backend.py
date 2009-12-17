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

from beacon_common import *

import backend
import exceptions, tempfile, os, sys, time

################################################################################
# DEMO BACKEND:
################################################################################

ON_EXIT_DO_NOTHING=0
ON_EXIT_KILL_BACKEND=1
ON_EXIT_KILL_SERVER=2

class DemoBackendSeq(backend.BasicOutputBackend):
    def __init__(self, tasks, host=BEACON_HOST, port=BEACON_PORT,
            on_exit=ON_EXIT_DO_NOTHING):
        self.tasks = tasks(self)
        self.on_exit = on_exit
        backend.BasicOutputBackend.__init__(self, host, port)
    def connect(self):
        backend.BasicOutputBackend.connect(self)
        self.tasks.next()
    def proc_input(self, cmd):
        #print "Backend:%s:%s" % (time.asctime(), repr(cmd))
        backend.BasicOutputBackend.proc_input(self, cmd)
        if cmd['event']=='end':
            try:
                self.tasks.next()
            except exceptions.StopIteration:
                if self.on_exit==ON_EXIT_KILL_SERVER:
                    print "Backend: sending kill to server"
                    self.send_kill()
                elif self.on_exit==ON_EXIT_KILL_BACKEND:
                    print "Backend: stopping backend"
                    raise exceptions.StopIteration()

class DemoBackendPPSeq(backend.PprintBackend):
    def __init__(self, tasks, host=BEACON_HOST, port=BEACON_PORT,
            on_exit=ON_EXIT_DO_NOTHING):
        self.tasks = tasks(self)
        self.on_exit = on_exit
        backend.PprintBackend.__init__(self, backend.FileBackend.FILE_STDOUT, host, port)
    def connect(self):
        backend.PprintBackend.connect(self)
        self.tasks.next()
    def proc_input(self, cmd):
        backend.PprintBackend.proc_input(self, cmd)
        if cmd['event']=='end':
            try:
                self.tasks.next()
            except exceptions.StopIteration:
                if self.on_exit==ON_EXIT_KILL_SERVER:
                    print "Backend: sending kill to server"
                    self.send_kill()
                elif self.on_exit==ON_EXIT_KILL_BACKEND:
                    print "Backend: stopping backend"
                    raise exceptions.StopIteration()

class DemoBackendPar(backend.BasicOutputBackend):
    def __init__(self, tasks, host=BEACON_HOST, port=BEACON_PORT,
            on_exit=ON_EXIT_DO_NOTHING):
        self.tasks = tasks(self)
        self.running = 0
        self.on_exit = on_exit
        backend.BasicOutputBackend.__init__(self, host, port)
    def connect(self):
        backend.BasicOutputBackend.connect(self)
        for filename in self.tasks:
            self.running += 1
    def proc_input(self, cmd):
        #print('Backend', (time.asctime(), cmd))
        backend.BasicOutputBackend.proc_input(self, cmd)
        if cmd['event']=='end':
            self.running -= 1
            if self.running <= 0:
                if self.on_exit==ON_EXIT_KILL_SERVER:
                    print "Backend: sending kill to server"
                    self.send_kill()
                elif self.on_exit==ON_EXIT_KILL_BACKEND:
                    print "Backend: stopping backend"
                    raise exceptions.StopIteration()

if __name__ == '__main__':
    import traceback
    from tests import run_on_backend
    try:
        bes = DemoBackendSeq(run_on_backend)
        bes.main()
    except:
        traceback.print_exc()
    try:
        bep = DemoBackendPar(run_on_backend)
        bep.main()
    except:
        traceback.print_exc()
    print >> sys.stderr, "To test this module properly, run beacon.py, please."
    sys.exit(1)
