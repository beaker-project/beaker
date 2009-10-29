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

import uuid
import exceptions

def new_id():
    """
    Function generating unique id's.

    Return: a string representation of id.
    """
    return str(uuid.uuid1())

def esc_name(name):
    """
    Escape name to be suitable as an identifier.
    """
    if name.isalnum():
        return name
    return ''.join([c if c.isalnum() else '__' if c=='_' else '_%x' % ord(c)
            for c in name])

def check_type(name, value, type_, allows_none=False):
    if isinstance(value, type_):
        return
    if allows_none and value is None:
        return
    raise exceptions.TypeError('%r not permitted as %s. Has to be %s%s.' \
            % (value, name, type_.__name__,
                " or None" if allows_none else ""))

