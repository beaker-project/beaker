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

from beah.misc import setfname, format_exc
import sys
import exceptions
import traceback

def log_this(logf, log_on=True):
    """Factory returning decorator for logging calls using logf.
    logf - function taking one string as its argument"""
    if log_on:
        def __call__(f):
            """Log decorator. This will take a function as an argument and return
            equivalent function loggign calls and return values"""
            fstr = repr(f)
            def tempf(*args, **kwargs):
                try: argstr = "*"+repr(args)+", **"+repr(kwargs)
                except: argstr = "???"
                try: logf("start %s(%s) {" % (fstr, argstr))
                except: pass
                try:
                    answ = f(*args, **kwargs)
                    try: logf("} %s returned %s" % (fstr, repr(answ)))
                    except: pass
                    return answ
                except:
                    (etype, e, etb) = sys.exc_info()
                    if getattr(e, '_printed', False):
                        tb = '...'
                    else:
                        tb = repr(format_exc())
                        setattr(e, '_printed', True)
                    try: logf("} %s raised %s (%s)" % (fstr, repr(e), tb))
                    except: pass
                    raise e, None, etb
            tempf.__doc__ = f.__doc__
            setfname(tempf, f.__name__)
            return tempf
    else:
        def __call__(f):
            """No logging decorator"""
            return f
    return __call__

def __print_func(s):
    print(s)

print_this = log_this(__print_func)

def __print_stderr_func(s):
    print >> stderr, s

print_stderr_this = log_this(__print_stderr_func)

