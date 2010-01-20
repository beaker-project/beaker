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
import socket
import traceback
import os
import sys
import logging

def raiser(exc=exceptions.Exception, *args, **kwargs):
    raise exc(*args, **kwargs)

if sys.version_info[1] >= 4:
    def setfname(f, name):
        f.__name__= name
else:
    def setfname(f, name):
        pass

def Raiser(exc=exceptions.Exception, *args, **kwargs):
    def raiser():
        raise exc(*args, **kwargs)
    setfname(raiser, "raiser_"+exc.__name__)
    return raiser

def mktemppipe():
    from tempfile import mktemp
    from os import mkfifo
    retries = 3
    while True:
        pname=mktemp()
        try:
            mkfifo(pname)
            return pname
        except:
            retries -= 1
            if retries <= 0:
                raise

def localhost(host):
    if host in [None, '', 'localhost']:
        return True
    if host in ['test.loop']:
        return False
    fqdn, aliaslist, ipaddrs = socket.gethostbyname_ex(socket.gethostname())
    if host == fqdn or host in aliaslist or host in ipaddrs:
        return True
    hfqdn, haliaslist, hipaddrs = socket.gethostbyname_ex(host)
    if hfqdn == fqdn:
        return True
    return False

if sys.version_info[1] < 4:
    def format_exc():
        """Compatibility wrapper - in python 2.3 can not use traceback.format_exc()."""
        return traceback.format_exception(sys.exc_type, sys.exc_value,
                sys.exc_traceback)
else:
    format_exc = traceback.format_exc

if sys.version_info[1] < 4:
    def dict_update(d, *args, **kwargs):
        """Compatibility wrapper - in python 2.3 dict.update does not accept keyword arguments."""
        return d.update(dict(*args, **kwargs))
else:
    dict_update = dict.update

def log_flush(logger):
    for h in logger.handlers:
        try:
            h.flush()
        except:
            pass

def make_log_handler(log, log_path, log_file_name=None, syslog=None):

    # FIXME: add config.option?
    if sys.version_info[0] == 2 and sys.version_info[1] <= 4:
        fmt = ': %(levelname)s %(message)s'
    else:
        fmt = ' %(funcName)s: %(levelname)s %(message)s'

    if log_file_name:
        if log_file_name[0] == '/':
            sep_ix = log_file_name.rfind('/')
            (log_path, log_file_name) = (log_file_name[:sep_ix], log_file_name[sep_ix+1:])

        # Create a directory for logging and check permissions
        if not os.access(log_path, os.F_OK):
            try:
                os.makedirs(log_path, mode=0755)
            except:
                print >> sys.stderr, "ERROR: Could not create %s." % log_path
                # FIXME: should attempt to create a temp file
                raise
        elif not os.access(log_path, os.X_OK | os.W_OK):
            print >> sys.stderr, "ERROR: Wrong access rights to %s." % log_path
            # FIXME: should attempt to create a temp file
            raise

        #lhandler = logging.handlers.RotatingFileHandler(log_path + "/" + log_file_name,
        #        maxBytes=1000000, backupCount=5)
        lhandler = logging.FileHandler(log_path + "/" + log_file_name)
        lhandler.setFormatter(logging.Formatter('%(asctime)s'+fmt))
        log.addHandler(lhandler)

    if syslog:
        lhandler = logging.handlers.SysLogHandler()
        lhandler.setFormatter(logging.Formatter('%(asctime)s %(name)s'+fmt))
        lhandler.setLevel(logging.WARNING)
        log.addHandler(lhandler)

