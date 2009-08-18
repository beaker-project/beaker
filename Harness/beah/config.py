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

#DEVEL    = lambda: False
#ROOT     = lambda: ''
#LOG_PATH = lambda: ROOT() + '/var/log'

__def = dict(
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

__args = {}
        #HOST=socket.gethostname()

def config(**opts):
    global __opts
    __opts = dict(opts)
    reconf(True)
    pass

def reconf(full=False):
    """\
Reconfigure Harness.
Uses several sources of data.
    1. Default configuration - __def
    2. Configuration file - __cfg
    3. Environment
    4. Command line options - __opts
    5. Arguments set at runtime - __args
Location of configuration file is not affected by __args.
"""
    global __cfg
    if full:
        # FIXME: read configuration - options, environment, config.file
        __cfg = {}
    # FIXME: define things which not be set at runtime
    # FIXME: do a reconfiguration
    temp = {}
    temp.update(__def)
    temp.update(__cfg)
    temp.update(__opts)
    temp.update(__args)
    for key in temp.keys():
        val = temp[key]
        if globals().has_key('set_'+key):
            globals()['set_'+key](key, val)
        else:
            globals()[key] = val
    pass

def update(**kwargs):
    if kwargs:
        __args.update(kwargs)
    reconf()

if __name__ == '__main__':
    config(
            DEVEL = lambda: True,
            )
    assert DEVEL() == True
    assert LOG()   == False
    assert HOST()  == "localhost"
    update(
            LOG   = lambda: True,
            )
    assert DEVEL() == True
    assert LOG()   == True
    assert HOST()  == "localhost"

