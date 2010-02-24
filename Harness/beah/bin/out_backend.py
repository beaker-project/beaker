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

from beah import config
from beah.core.backends import PprintBackend
from beah.wires.internals.twbackend import start_backend, log_handler
from twisted.internet import reactor

out_backend_intro="""
This is a Backend pretty-printing all events received from Controller.

Type <Ctrl-C> to exit.
"""

def out_backend():
    """
    Simple backend for pretty-printing events received from Controller.
    """
    config.backend_conf(
            defaults={'NAME':'beah_out_backend'},
            overrides=config.backend_opts())
    log_handler()
    start_backend(PprintBackend())

def main():
    print out_backend_intro
    out_backend()
    reactor.run()

if __name__ == '__main__':
    main()

