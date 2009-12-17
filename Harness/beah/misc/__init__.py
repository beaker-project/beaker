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

def raiser(exc=exceptions.Exception, *args, **kwargs):
    raise exc(*args, **kwargs)

def Raiser(exc=exceptions.Exception, *args, **kwargs):
    def raiser():
        raise exc(*args, **kwargs)
    raiser.__name__ = "raiser_"+exc.__name__
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

