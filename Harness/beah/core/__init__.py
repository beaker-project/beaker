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
    # using and/or to simulate if/else
    # FIXME: is there a built-in?
    return ''.join([(c.isalnum() and c) or (c=='_' and '__') or '_%x' % ord(c)
            for c in name])

def test_esc_name():
    assert esc_name('') == ''
    assert esc_name('a') == 'a'
    assert esc_name('1') == '1'
    assert esc_name('_') == '__'
    assert esc_name('-') == '_%x' % ord('-')
    assert esc_name('a_b') == 'a__b'
    assert esc_name('a-b') == 'a_%xb' % ord('-')

def check_type(name, value, type_, allows_none=False):
    if isinstance(value, type_):
        return
    if allows_none and value is None:
        return
    raise exceptions.TypeError('%r not permitted as %s. Has to be %s%s.' \
            % (value, name, type_.__name__, allows_none and " or None" or ""))

def make_addict(d):

    class new_addict(d):

        """
        Dictionary extension, which filters input.
        """

        def __init__(self, *args, **kwargs):
            tmp = self.flatten(args, kwargs)
            d.__init__(self, tmp)

        def filter(self, k, v):
            """
            Filter function.

            This method is to be reimplemented.

            Returning True, if (k,v) pair is to be included in dictionary.
            """
            return k is not None and v is not None

        def flatten(self, args, kwargs):
            # FIXME: a in args could be:
            # - a dictionary
            # - an iterable of key/value pairs (as a tuple or another iterable
            #   of length 2.)
            tmp = dict()
            for a in args:
                #check_type('an argument', a, dict)
                for k, v in a.items():
                    if self.filter(k, v):
                        tmp[k] = v
            for k, v in kwargs.items():
                if self.filter(k, v):
                    tmp[k] = v
            return tmp

        def update(self, *args, **kwargs):
            d.update(self, self.flatten(args, kwargs))

        def __setitem__(self, k, v):
            if self.filter(k, v):
                d.__setitem__(self, k, v)

    return new_addict

addict = make_addict(dict)

def test_addict():
    ad = addict()
    d = dict()
    ad[None] = 'a'
    ad['a'] = None
    d['b'] = ad['b'] = 'c'
    ad.update(c=None, d='e')
    d.update(d='e')
    ad.update({None: 'e', 'e': None, 'f': 'g'})
    d.update({'f': 'g'})
    assert ad == dict(b='c', d='e', f='g')
    assert ad == d
    ad = addict(a=None, b='c')
    assert ad == dict(b='c')

if __name__ == '__main__':
    test_esc_name()
    test_addict()
