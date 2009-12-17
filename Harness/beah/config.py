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


"""
Read configuration for beah.

Functions:
    config
        - seeks and reads conf file, and updates with arguments passed in.
    main_config
        - parses command line options for common options and then calls config.
Auxiliary:
    conf_opt
        - parses command line options.

Basic Usage:
    # Import:
    from beah.config import config

    # Read and set:
    conf = config()
    conf.set('CONTROLLER', 'LOG', 'True')

    # Use:
    if conf.get('CONTROLLER', 'LOG'):
        pass
"""


import exceptions
import sys
import os
import re
from ConfigParser import ConfigParser
from optparse import OptionParser


def conf_opt(args):
    """
    Parses command line for common options.

    This seeks only the few most common options. For other options use your own
    parser.

    Returns tuple (options, args). For descritpin see
    optparse.OptionParser.parse_args and optparse.Values
    """
    opt = OptionParser()
    opt.add_option("-c", "--config", action="store", dest="conf_file",
            help="Use FILE for configuration.", metavar="FILE")
    opt.add_option("-n", "--name", action="store", dest="name",
            help="Use NAME as identification.", metavar="NAME")
    opt.add_option("-v", "--verbose", action="count", dest="verbose",
            help="Increase verbosity.")
    opt.add_option("-q", "--quiet", action="count", dest="quiet",
            help="Decrease verbosity.")
    return opt.parse_args(args)


def _check_conf_file(filename):
    """Check the existence and readability of configuration file."""
    if filename and os.access(filename, os.R_OK):
        return filename
    return None

def _get_conf_file(conf_env_var, fname, opt=None):
    """Find a configuration file or raise an exception."""
    conf_list = []
    conf_list.append(opt)
    conf_list.append(os.environ.get(conf_env_var))
    # used in devel.environment only:
    if os.environ.has_key('BEAH_ROOT'):
        conf_list.append(os.environ.get('BEAH_ROOT')+'/'+fname)
        conf_list.append(os.environ.get('BEAH_ROOT')+'/etc/'+fname)
    if os.environ.has_key('HOME'):
        conf_list.append(os.environ.get('HOME')+'/.'+fname)
    if sys.prefix not in ['', '/']:
        conf_list.append(sys.prefix + '/etc/'+fname)
    conf_list.append('/etc/'+fname)
    for conf_file in conf_list:
        if _check_conf_file(conf_file):
            return conf_file
    raise exceptions.Exception("Could not find configuration file.")


_CONF_ID = '[a-zA-Z_][a-zA-Z_0-9]*'
_CONF_NAME_RE = re.compile('^(?:('+_CONF_ID+')\.)?('+_CONF_ID+')$')


def parse_conf_name(name):
    """Parses configuration name in form [SECTION.]NAME."""
    match = _CONF_NAME_RE.match(name)
    if not match:
        return None
    return (match.group(1) or 'DEFAULT', match.group(2))


def config(conf_env_var='BEAH_CONF', conf_filename='beah.conf', defaults=None,
        **opts):

    """
    Configure harness for the first time.

    opts -- parsed options (e.g. from command line and env.variables)

    returns instance of ConfigParser.ConfigParser. If configuration file was
    parsed already, it will return existing object.

    Uses these sources of data:
        1. Configuration file
        2. Environment
        3. Command line options
        4. Arguments set at runtime using "ConfigParser.set" function
    """

    glob_var = '_conf_%s' % conf_env_var
    if not globals().has_key(glob_var):
        if defaults is None:
            defaults = {}
        conf = ConfigParser(defaults=defaults)
        conf.read(_get_conf_file(conf_env_var, conf_filename,
            opts.get("CONF_FILE", '')))
        globals()[glob_var]=conf
    else:
        conf = globals()[glob_var]

    if os.environ.has_key('BEAH_DEVEL'):
        conf.set('DEFAULT', 'DEVEL', os.environ.get('BEAH_DEVEL', 'False'))

    for (key, value) in opts.items():
        sec_name_pair = parse_conf_name(key)
        if not sec_name_pair:
            print >> sys.stderr, "--- WARNING: Unknown option %r." % key
            continue
        conf.set(sec_name_pair[0], sec_name_pair[1], value)

    return conf


def main_config(conf_env_var='BEAH_CONF', conf_filename='beah.conf',
        defaults=None):
    """
    Configure harness, including command line arguments.

    This parses command line arguments for common options only! If more
    advanced options are expected, sys.argv has to be parsed by external
    parser.
    """
    (opts, _) = conf_opt(sys.argv[1:])
    conf = config(conf_env_var, conf_filename, defaults,
            CONF_FILE=opts.conf_file)
    if opts.verbose is not None or opts.quiet is not None:
        conf.set('CONTROLLER', 'VERBOSITY',
                str((opts.verbose or 0) - (opts.quiet or 0)))
    if opts.name is not None:
        conf.set('CONTROLLER', 'NAME', opts.name)
    return conf


def parse_bool(arg):
    """Premissive string into bool parser."""
    if arg == True or arg == False:
        return arg
    if str(arg).strip().lower() in ['', '0', 'false']:
        return False
    return True


if __name__ == '__main__':

    def _test():

        """Self test."""

        print _get_conf_file('BEAH_CONF', 'beah.conf')

        cfg = config(
                LOG='False',
                DEVEL='True',
                CONF_FILE="beah.conf",
                )

        def _tst_eq(result, expected):
            """Check test result against expected value and assert on
            missmatch."""
            try:
                assert result == expected
            except:
                print "result:%r != expected:%r" % (result, expected)
                raise

        cfg.set('BACKEND', 'INTERFACE', "localhost")

        _tst_eq(parse_bool(cfg.get('DEFAULT', 'DEVEL')), True)
        _tst_eq(parse_bool(cfg.get('DEFAULT', 'LOG')), False)
        _tst_eq(cfg.get('BACKEND', 'INTERFACE'), "localhost")
        _tst_eq(int(cfg.get('BACKEND', 'PORT')), 12432)
        _tst_eq(cfg.get('DEFAULT', 'ROOT'), "/tmp")

        cfg.set('DEFAULT', 'LOG', 'True')

        _tst_eq(parse_bool(cfg.get('DEFAULT', 'DEVEL')), True)
        _tst_eq(parse_bool(cfg.get('DEFAULT', 'LOG')), True)
        _tst_eq(cfg.get('BACKEND', 'INTERFACE'), "localhost")
        _tst_eq(int(cfg.get('BACKEND', 'PORT')), 12432)
        _tst_eq(cfg.get('DEFAULT', 'ROOT'), "/tmp")

    _test()

