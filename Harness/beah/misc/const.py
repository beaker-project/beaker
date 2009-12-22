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

from exceptions import TypeError

class Const(object):
    def __init__(self, aName, value=None):
        self.__name = aName
        self.__value = value
    def __call__(self):
        return self.__value
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.__name, self.__value)
    def __str__(self):
        return self.__name
    def name(self):
        return str(self.__name)

class EConst(Const):
    def __init__(self, owner, aName, value=None):
        self.__owner = owner
        self.__name = aName
        Const.__init__(self, self.__owner.name(aName), value)
    def clone(self, aName):
        self.__owner.link(aName, self)
    def name(self):
        return str(self.__name)

class Eval(object):
    def get_incf(o):
        if isinstance(o, int) or isinstance(o, float):
            return lambda x: x+1
        if isinstance(o, str):
            return lambda x: x+"_"
        raise TypeError("o is supposed to be a number or string")
    get_incf = staticmethod(get_incf)

    def __init__(self, aName, start=0, nextf=None):
        self.__name = aName
        self.__start = start
        self.__nextf = nextf or self.get_incf(start)
        self.__last = None

    def __rshift__(self, name):
        self[name] = self.__last
        return self

    def __lshift__(self, o):
        if isinstance(o, str):
            self[o] = None
            return self
        if isinstance(o, list) or isinstance(o, tuple):
            self[o[0]] = o[1]
            return self
        raise TypeError("Object has to be a string, a tuple or a list", o)

    def __setitem__(self, aName, value=None):
        if not isinstance(aName, str):
            raise TypeError("Name has to be a string", aName)
        if isinstance(value, EConst):
            c = value
        else:
            if value is None:
                self.__start = self.__nextf(self.__start)
                value = self.__start
            else:
                self.__start = value
            c = EConst(self, aName, value)
        self.__setattr__(aName, c)
        self.__last = c

    def __getitem__(self, aName):
        return self.__getattribute__(aName)

    def __call__(self, value):
        # FIXME: Find a constant with given value
        raise

    def name(self, aName):
        return self.__name + '.' + aName

if __name__ == '__main__':
    A = Const('A')
    B = Const('B')
    print A
    print A()
    print repr(A)
    print str(A)
    print A is A
    print A is B

    print "##### DEBUG_LEVEL"
    DEBUG_LEVEL = Eval('DEBUG_LEVEL')

    DEBUG_LEVEL << 'NOTHING'
    DEBUG_LEVEL['SOMETHING'] = None
    DEBUG_LEVEL['ANYTHING'] = DEBUG_LEVEL.SOMETHING

    DEBUG_LEVEL << ('DEBUG3', 20) << ('DEBUG2', 30) << ('DEBUG1', 40)
    DEBUG_LEVEL << ('INFO', 50) << ('WARNING', 60) << ('ERROR', 70)
    DEBUG_LEVEL << 'CRITICAL' << 'FATAL' >> 'OH_NO' >> 'NIEEE'
    DEBUG_LEVEL << ('DEBUG', DEBUG_LEVEL.DEBUG1)

    print DEBUG_LEVEL.NOTHING
    print DEBUG_LEVEL.ANYTHING
    print DEBUG_LEVEL.INFO
    print repr(DEBUG_LEVEL.INFO)
    print DEBUG_LEVEL.INFO()
    print DEBUG_LEVEL.DEBUG1
    print DEBUG_LEVEL.DEBUG1()
    print DEBUG_LEVEL.DEBUG
    print DEBUG_LEVEL.DEBUG()
    print DEBUG_LEVEL['ERROR']
    print DEBUG_LEVEL['ERROR'].name()
    print DEBUG_LEVEL['OH_NO']
    print DEBUG_LEVEL.NIEEE
    print DEBUG_LEVEL.NIEEE is DEBUG_LEVEL.FATAL

