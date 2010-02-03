# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2010 Marian Csontos <mcsontos@redhat.com>
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
import shelve
from beah.core import make_addict


UNDEFINED=[]


class BaseRuntime(object):

    """
    Baseclass for persistent objects with better granularity than shelve.

    Subclass should implement these methods:
        type_set_primitive(rt, type, key, value)
        type_del_primitive(rt, type, key)
        type_get(rt, type, key)
        type_keys(rt, type)
    And depending on the implementation these:
        close(rt)
        sync(rt, type=None)
    This one might be redefined for performance reasons:
        type_has_key(rt, type, key)

    Its instance can define dict members this way:
        rt = ShelveRuntime(fname)
        rt.vars = TypeDict(rt, 'var')
        rt.files = TypeDict(rt, 'file')
    or in subclass' contructor.
    These can be accessed as normal dictionary
        rt.vars['a'] = 11
    """

    def __init__(self):
        pass

    def close(self):
        self.sync()

    def sync(self, key=None):
        pass

    def type_set(self, type, key, value):
        self.type_set_primitive(type, key, value)
        self.sync(type)
        return None

    def type_del(self, type, key):
        self.type_del_primitive(type, key)
        self.sync(type)

    def type_has_key(self, type, key):
        return key in self.type_keys(type)


class TypeDict(object):

    """
    Class implementing dictionary functionality using runtime object for
    storage.
    """

    def __init__(self, runtime, type):
        self.runtime = runtime
        self.type = type

    def __setitem__(self, key, value):
        return self.runtime.type_set(self.type, key, value)

    def __getitem__(self, key):
        return self.runtime.type_get(self.type, key)

    def __delitem__(self, key):
        return self.runtime.type_del(self.type, key)

    def keys(self):
        return self.runtime.type_keys(self.type)

    def has_key(self, key):
        return self.runtime.type_has_key(self.type, key)

    def get(self, key, defval=UNDEFINED):
        if self.has_key(key):
            return self[key]
        if defval is UNDEFINED:
            raise exceptions.KeyError("Key %r is not present." % key)
        return defval

    def setdefault(self, key, defval=None):
        if self.has_key(key):
            return self[key]
        self[key] = defval
        return defval

    def update(self, *dicts, **kwargs):
        cache = {}
        for dict_ in dicts:
            cache.update(dict_)
        cache.update(kwargs)
        for key, value in cache.items():
            self.runtime.type_set_primitive(self.type, key, value)
        self.runtime.sync(self.type)


def TypeAddict_init(self, runtime, type):
    TypeDict.__init__(self, runtime, type)
TypeAddict = make_addict(TypeDict)
TypeAddict.__init__ = TypeAddict_init


class TypeList(object):

    """
    Class implementing list functionality using runtime object for storage.
    """

    def __init__(self, runtime, type):
        self.runtime = runtime
        self.type = type
        f = self.__first = int(self.runtime.type_get(self.type, 'first', 0))
        l = self.__last = int(self.runtime.type_get(self.type, 'last', -1))
        index = []
        while f <= l:
            key = str(f)
            if self.runtime.type_has_key(self.type, key):
                index.append(key)
            f += 1
        self.__index = index

    def __len__(self):
        return len(self.__index)

    def __contains__(self, value):
        for v in self:
            if v == value:
                return True
        return False

    def __eq__(self, iterable):
        it = self.__iter__()
        it2 = iterable.__iter__()
        while True:
            try:
                v = it.next()
            except exceptions.StopIteration:
                break
            try:
                v2 = it2.next()
            except exceptions.StopIteration:
                return False
            if v != v2:
                return False
        try:
            it2.next()
            return False
        except exceptions.StopIteration:
            return True

    def __ne__(self, iterable):
        return not (self == iterable)

    def __iter__(self):
        for ix in self.__index:
            yield self.runtime.type_get(self.type, ix)
        raise exceptions.StopIteration

    def __normalize_ix(self, ix):
        if ix < 0:
            ix = len(self) + ix
            if ix < 0:
                raise exceptions.KeyError('Not enough items in list')
        return ix

    def __getitem__(self, ix):
        ix = self.__normalize_ix(ix)
        return self.runtime.type_get(self.type, self.__index[ix])

    def __setitem__(self, ix, value):
        ix = self.__normalize_ix(ix)
        return self.runtime.type_set(self.type, self.__index[ix], value)

    def __delitem__(self, ix):
        ix = self.__normalize_ix(ix)
        self.runtime.type_del(self.type, str(self.__index[ix]))
        del self.__index[ix]
        n = len(self)
        upd = False
        if n == 0:
            self.__first = 0
            self.__last = -1
            upd = True
        elif ix == 0:
            self.__first = int(self.__index[0])
            upd = True
        elif ix == n:
            self.__last = int(self.__index[-1])
            upd = True
        if upd:
            self.runtime.type_set_primitive(self.type, 'first', self.__first)
            self.runtime.type_set_primitive(self.type, 'last', self.__last)
            self.runtime.sync(self.type)

    def __add(self, value):
        l = self.__last = self.__last + 1
        self.runtime.type_set_primitive(self.type, 'last', l)
        key = str(l)
        self.__index.append(key)
        self.runtime.type_set_primitive(self.type, key, value)

    def __iadd__(self, value):
        self.__add(value)
        self.runtime.sync(self.type)
        return self

    def append(self, value):
        self.__add(value)
        self.runtime.sync(self.type)

    def extend(self, iterable):
        for value in iterable:
            self.__add(value)
        self.runtime.sync(self.type)

    def pop(self, ix=-1):
        answ = self[ix]
        del self[ix]
        return answ

    def dump(self):
        return (self.__first, self.__last, list([(ix, self[i]) for i, ix in enumerate(self.__index)]))

    def check(self):
        f = int(self.runtime.type_get(self.type, 'first', 0))
        l = int(self.runtime.type_get(self.type, 'last', -1))
        v = list([(str(i), self.runtime.type_get(self.type, str(i)))
            for i in range(f, l+1) if self.runtime.type_has_key(self.type,
                str(i))])
        d = self.dump()
        r = (f, l, v)
        assert d == r


class ShelveRuntime(BaseRuntime):
    """
    Runtime using shelve to store data.
    """

    def __init__(self, fname):
        self.fname = fname
        self.so = shelve.open(fname, 'c')

    def close(self):
        self.so.close()

    def sync(self, key=None):
        self.so.sync()

    def mk_type_key(self, type, key):
        # NOTE: In python 2.3 this might return unicode, which is not handled
        # by shelve.
        return str("%s/%s" % (type, key))

    def unmk_type_key(self, id):
        l = id.find("/")
        # Note: ``id[l:][1:]'' is not the same as ``id[l+1:]'' if l is -1
        return (id[:l], id[l:][1:])

    def type_set_primitive(self, type, key, value):
        self.so[self.mk_type_key(type, key)] = value

    def type_del_primitive(self, type, key):
        del self.so[self.mk_type_key(type, key)]

    def type_get(self, type, key, defval=UNDEFINED):
        if defval is UNDEFINED:
            return self.so[self.mk_type_key(type, key)]
        return self.so.get(self.mk_type_key(type, key), defval)

    def type_has_key(self, type, key):
        return self.so.has_key(self.mk_type_key(type, key))

    def type_keys(self, type):
        tl = len(type)+1
        type = type + '/'
        return [key[tl:] for key in self.so.keys() if key[:tl] == type]

    def dump(self):
        return list([(k, v) for k, v in enumerate(self.so)])


if __name__ == '__main__':

    class TestRuntime(ShelveRuntime):
        def __init__(self, fname):
            ShelveRuntime.__init__(self, fname)
            self.vars = TypeDict(self, 'var')
            self.files = TypeDict(self, 'file')
            self.queue = TypeList(self, 'queue')

    TESTDB='.test-runtime.db.tmp'
    tr = TestRuntime(TESTDB)
    tr.tasks = TypeDict(tr, 'tasks')
    tr.tqueue = TypeList(tr, 'testqueue')
    tr.addict = TypeAddict(tr, 'addict')
    tr.vars['var1'] = 'Hello'
    tr.vars['var2'] = 'World'
    tr.vars['var3'] = '!'
    tr.vars.update(x=1, y=2, d=dict(en="Hi", cz="Ahoj", sk="Ahoj"))
    tr.files['f1'] = dict(name='file/f1', id='f1')
    tr.files['f2'] = dict(name='file/f2', id='f2')
    tr.files['f3'] = dict(name='file/f3', id='f3')
    del tr.files['f3']
    tr.tasks['1'] = 'task1'
    tr.tasks['2'] = 'task2'
    while len(tr.queue) > 0:
        tr.queue.pop()
    assert len(tr.queue) == 0
    tr.queue.append('first')
    tr.queue.extend(['second', 'third', 'fourth'])
    tr.queue += 'fifth'
    assert tr.queue == ['first', 'second', 'third', 'fourth', 'fifth']
    assert tr.queue != ['first', 'second', 'third', 'fourth']
    assert tr.queue != ['first', 'second', 'third', 'fourth', 'fifth', 'sixth']
    tr.queue[0] = '1st'
    tr.queue[4] = '5th'
    assert tr.queue == ['1st', 'second', 'third', 'fourth', '5th']
    tr.queue[-5] = 'First'
    tr.queue[-1] = 'Fifth'
    assert tr.queue == ['First', 'second', 'third', 'fourth', 'Fifth']
    tr.queue.check()
    tr.tqueue.extend([0, 1, 2, 3])
    del tr.tqueue[3]
    del tr.tqueue[-1]
    del tr.tqueue[0]
    del tr.tqueue[0]
    assert tr.tqueue == []
    tr.tqueue.check()
    tr.addict[None] = 'b'
    tr.addict['a'] = None
    tr.addict['b'] = 'c'
    tr.addict.update(dict(c=None, d='e'))
    assert not tr.addict.has_key('a')
    assert tr.addict['b'] == 'c'
    assert not tr.addict.has_key('c')
    assert tr.addict['d'] == 'e'
    tr.close()

    tr = TestRuntime(TESTDB)
    tr.tasks = TypeDict(tr, 'tasks')
    tr.tqueue = TypeList(tr, 'testqueue')
    tr.addict = TypeAddict(tr, 'addict')
    print "\n== vars =="
    for k in tr.vars.keys():
        print "%r: %r" % (k, tr.vars[k])
    print "\n== files =="
    for k in tr.files.keys():
        print "%r: %r" % (k, tr.files[k])
    print "\n== tasks =="
    for k in tr.tasks.keys():
        print "%r: %r" % (k, tr.tasks[k])
    print "\n== queue =="
    for ix, v in enumerate(tr.queue):
        print "[%r]: %r" % (ix, v)
    assert tr.vars['var1'] == 'Hello'
    assert tr.vars['var2'] == 'World'
    assert tr.vars['var3'] == '!'
    assert tr.vars['x'] == 1
    assert tr.vars['y'] == 2
    assert tr.vars['d']['en'] == 'Hi'
    assert tr.files['f1'] == dict(name='file/f1', id='f1')
    assert tr.files['f2'] == dict(name='file/f2', id='f2')
    assert tr.files.get('f3', None) == None
    assert tr.tasks['1'] == 'task1'
    assert tr.tasks['2'] == 'task2'
    assert tr.queue == ['First', 'second', 'third', 'fourth', 'Fifth']
    assert tr.tqueue == []
    assert not tr.addict.has_key('a')
    assert tr.addict['b'] == 'c'
    assert not tr.addict.has_key('c')
    assert tr.addict['d'] == 'e'
    tr.close()

