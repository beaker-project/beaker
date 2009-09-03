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

# FIXME: change this to singleton class(?)
DEVEL    = lambda: False
ROOT     = lambda: ''
LOG_PATH = lambda: ROOT() + '/var/log'

__DEF = dict(
        # Devel flag. Will activate some debug features:
        DEVEL          = lambda: False,
        # Logging on:
        LOG            = lambda: False,

        # Address to listen on for backends:
        #HOST   = lambda: socket.gethostname,
        HOST           = lambda: "localhost",
        PORT           = lambda: 12432,

        # Address to listen on for tasks:
        THOST          = lambda: "localhost",
        TPORT          = lambda: 12434,

        # FIXME: add function - use environment
        # Root directory. Log and config files are relative to this directory:
        ROOT           = lambda: '' if not DEVEL() else '/tmp',

        # FIXME: add function - use environment
        CONF_FILE_NAME = lambda: ROOT() + '/etc/beacon.conf',

        # FIXME: add function - use config
        LOG_PATH       = lambda: ROOT() + '/var/log',
        LOG_FILE_NAME  = lambda: LOG_PATH() + '/beacon.log',

        # Print log messages to server's stdout:
        SRV_LOG        = lambda: False
)

__ARGS = {}
__OPTS = {}
__CFG = {}

def config(**opts):
    """
    Configure harness for the first time.

    opts -- parsed options (e.g. from command line)
    """
    global __OPTS
    __OPTS = dict(opts)
    reconf(True)

def reconf(full=False):
    """
    Reread configuration.

    Uses several sources of data.
        1. Default configuration - __DEF
        2. Configuration file - __CFG
        3. Environment
        4. Command line options - __OPTS
        5. Arguments set at runtime - __ARGS
    Location of configuration file is not affected by __ARGS.
    """
    global __CFG
    if full:
        # FIXME: read configuration - options, environment, config.file
        __CFG = {}
    # FIXME: define things which not be set at runtime
    # FIXME: do a reconfiguration
    temp = {}
    temp.update(__DEF)
    temp.update(__CFG)
    temp.update(__OPTS)
    temp.update(__ARGS)
    for key in temp.keys():
        val = temp[key]
        if globals().has_key('set_'+key):
            globals()['set_'+key](key, val)
        else:
            globals()[key] = val

def update(**kwargs):
    """Change Harness configuration at the runtime."""
    if kwargs:
        __ARGS.update(kwargs)
    reconf()

if __name__ == '__main__':
    LOG = lambda: False
    HOST = lambda: "localhost"
    config(
            DEVEL = lambda: True,
            )
    assert DEVEL() == True
    assert LOG()   == False
    assert HOST()  == "localhost"
    assert ROOT()  == "/tmp"
    update(
            LOG   = lambda: True,
            )
    assert DEVEL() == True
    assert LOG()   == True
    assert HOST()  == "localhost"
    assert ROOT()  == "/tmp"

