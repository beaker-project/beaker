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

################################################################################
# Generic Input Filters:
################################################################################

class Receiver(object):
    def __init__(self, **kwargs):
        pass
    def proc_data(self, data):
        """Reimplement this in sublcass."""
        pass
    def close(self):
        pass

class CachingReceiver(Receiver):
    def __init__(self, **kwargs):
        Receiver.__init__(self, **kwargs)
        self.cache = ''
        self.raise_pending = kwargs.get('raise_pending', False)
    def proc_data(self, data):
        self.cache += data
        self.proc_cache()
    def proc_cache(self):
        """Reimplement this in sublcass."""
        self.cache = ''
    def close(self):
        if self.cache and self.raise_pending:
            raise exceptions.RuntimeError('Pending data in cache')

class LineReceiver(CachingReceiver):
    def __init__(self, delim=None, **kwargs):
        CachingReceiver.__init__(self, **kwargs)
        self.delim = delim or '\n'
    def proc_cache(self):
        while True:
            line_list = self.cache.split(self.delim, 1)
            if len(line_list) <= 1:
                return
            (head, self.cache) = line_list
            self.proc_line(head)
    def proc_line(self, line):
        """Reimplement this in sublcass."""
        pass
    def redir(self, processor):
        def proc_line(line):
            "Forward proc_line calls to %s" % processor
            processor(line)
        self.proc_line = proc_line
        self.close = lambda: processor(None)

class Deserializer(LineReceiver):
    def __init__(self, deserializer=None, **kwargs):
        from simplejson import loads
        self.deserializer = deserializer or loads
        LineReceiver.__init__(self, **kwargs)
    def proc_line(self, line):
        try:
            obj = self.deserializer(line)
        except:
            self.not_obj(line)
            return
        self.proc_obj(obj)
    def not_obj(self, line):
        raise
    def proc_obj(self, obj):
        """Reimplement this in sublcass."""
        pass
    def redir(self, processor):
        def proc_obj(obj):
            "Forward proc_obj calls to %s" % processor
            processor(obj)
        self.proc_obj = proc_obj
        self.close = lambda: processor(None)

class ListDeserializer(LineReceiver):
    def __init__(self, deserializer=None, **kwargs):
        from simplejson import loads
        self.deserializer = deserializer or loads
        LineReceiver.__init__(self, **kwargs)
    def proc_line(self, line):
        try:
            obj = self.deserializer(line)
        except:
            self.not_obj(line)
            return
        if isinstance(obj, list) or isinstance(obj, tuple):
            for item in obj:
                self.proc_item(item)
        else:
            self.proc_obj(obj)
    def not_obj(self, line):
        raise
    def proc_obj(self, obj):
        raise exceptions.TypeError("Not a list or a tuple", obj)
    def proc_item(self, item):
        """Reimplement this in sublcass."""
        pass
    def redir(self, processor):
        def proc_item(item):
            "Forward proc_item calls to %s" % processor
            processor(item)
        self.proc_item = proc_item
        self.close = lambda: processor(None)

################################################################################
# Object Filters - filters expecting python object on their input - proc_obj
################################################################################

class ObjFilter_Dummy(object):
    def proc_obj(self, obj):
        pass

from sys import stdout
class ObjectWriter(object):
    def __init__(self, writer=None, serializer=None, delim=None):
        self.writer = writer or stdout.write
        self.serializer = serializer or str
        self.delim = delim or '\n'
        if not callable(self.writer):
            raise exceptions.TypeError('%r is not callable.' % self.writer)
    def format_obj(self, obj):
        return self.serializer(obj) + self.delim
    def proc_obj(self, obj):
        self.writer(self.format_obj(obj))

def Pprinter(**kwargs):
    from pprint import pformat
    ka = dict(kwargs)
    ka['serializer'] = pformat
    return ObjectWriter(**ka)
# FIXME: it is much easier to use pprint.pprint instead of Pprinter().proc_obj

def JSONSerializer(**kwargs):
    from simplejson import dumps
    ka = dict(kwargs)
    ka['serializer'] = dumps
    return ObjectWriter(**ka)
# FIXME: it is easier to use lambda obj: stdout.write(json.dumps(obj)+"\n")

################################################################################
# Special Filters:
################################################################################

def nop(*args, **kwargs):
    pass

def true(*args, **kwargs):
    return True

class Select(object):
    def __init__(self, *args, **kwargs):
        self.args = []
        for arg in args:
            self += arg
        self.first_only = kwargs.get('first_only',True)
    def __iadd__(self, arg):
        if not ((arg[0] is None or callable(arg[0])) and
                (arg[1] is None or callable(arg[1]))):
            raise TypeError('Each arg has to have 2 callable elements.', arg)
        self.args.append(arg)
        return self
    def __call__(self, data):
        for arg in self.args:
            if not arg[0] or arg[0](data):
                arg[1] and arg[1](data)
                if self.first_only:
                    break

class Tee(object):
    # FIXME: Select could be used to simulate this
    def __init__(self, *args, **kwargs):
        self.args = []
        for arg in args:
            self += arg
    def __iadd__(self, arg):
        if not callable(arg):
            raise TypeError('Each arg must be a callable.', arg)
        self.args.append(arg)
        return self
    def __call__(self, data):
        for arg in self.args:
            arg(data)

################################################################################
# Test:
################################################################################

if __name__ == '__main__':
    import traceback
    from beah.misc import log_this
    import pprint
    pretty_log = log_this.log_this(pprint.pprint)

    print "1..1"
    print "# BASIC USAGE:"
    try:
        ow = ObjectWriter()
        ow.proc_obj([])
        ow.proc_obj({'a':[('H3110', 1.0, None)]})
        ow = Pprinter()
        ow.proc_obj({'a':[('H3110', 1.0, None)]})
    except:
        raise

    print "# ADVANCED USAGE:"
    a = Deserializer()
    a.redir(Tee(
        JSONSerializer().proc_obj,
        Select(
            (lambda obj: isinstance(obj, dict),
                Pprinter().proc_obj),
            ),
        ))
    b = JSONSerializer(writer=a.proc_data)

    def test(data):
        a.proc_data(data)
    def Test(obj):
        b.proc_obj(obj)

    for str in ['[]\n', 'null\n', '[]\n', '{}\n', '{}\n', '[', ']', '\n',
            '"Hello', ' ', 'World!"', '\n']:
        test(str)
    for obj in [[], {}, {'a':[('H3110', 1.0, None)]}, None,
            "Hello World!\n", 12]:
        Test(obj)

    print "# FAILURES:"
    for str in ['\n', '[\n', '}\n', '"\n', '()\n', '1a', 'a']:
        try:
            test(str)
            raise exceptions.Error("String passed, should have failed.", str)
        except:
            print "%r Failed as expected" % str
            pass

    print "ok 1 Passed"

