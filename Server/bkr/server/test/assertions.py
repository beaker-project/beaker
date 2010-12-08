
# Copyright (C) 2010 Red Hat, Inc.
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

def assert_sorted(things, key=None):
    """
    Asserts that the given sequence is in sorted order.
    """
    if len(things) == 0: return
    if key is not None:
        things = map(key, things)
    for n in xrange(1, len(things)):
        if things[n] < things[n - 1]:
            raise AssertionError('Not in sorted order, found %r after %r' %
                    (things[n], things[n - 1]))

def assert_has_key_with_value(system, key_name, value):
    for kv in system.key_values_int:
        if kv.key.key_name == key_name and kv.key_value == value:
            return
    for kv in system.key_values_string:
        if kv.key.key_name == key_name and kv.key_value == value:
            return
    raise AssertionError('No such key with name %r and value %r found on system %r'
            % (key_name, value, system))
