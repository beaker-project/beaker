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
    beah_conf
        - create controller configuration
    backend_conf
        - create backend configuration
    get_conf
        - find ConfigParser instance with given id

Auxiliary:
    _Config
        - common configuration behavior
    _BeahConfig
        - beah specific behavior
    _ConfigParserFix
        - fixed ConfigParser
    _get_config
        - find _Config instance with given id

Basic Usage:
    # Import:
    from beah import config

    # Read and set:
    beah_conf = config.beah_conf(beah_overrides)
    beaker_backend_conf = config.backend_conf('beaker-backend',
        'BEAKER_BACKEND_CONF', 'beaker_backend.conf', beaker_defaults,
        beaker_overrides)
    beaker_backend_conf.conf.set('CONTROLLER', 'LOG', 'True')

    # Use:
    beaker_backend_conf = config.get_config('beaker-backend')
    if beaker_backend_conf.conf.get('CONTROLLER', 'LOG'):
        pass
"""


import sys
import os
import os.path
import re
import exceptions
from ConfigParser import ConfigParser
from beah.misc import dict_update, log_this, make_class_verbose


# FIXME: Use config option for log_on:
#print_this = log_this.log_this(lambda s: log.debug(s), log_on=True)
print_this = log_this.print_this


class _ConfigParserFix(ConfigParser):
    """
    Class overriding ConfigParser to workaround a bug in Python 2.3.

    The problem is that optionxform is not applied consistently to keys.

    Using str.upper for optionxform, as uppercase keys are used in beah.
    """
    def __init__(self, defaults={}, optionxformf=str.upper):
        self.optionxform = optionxformf
        defs = {}
        if defaults:
            for key, value in defaults.items():
                defs[self.optionxform(key)] = value
        ConfigParser.__init__(self, defs)


class _Config(object):

    _VERBOSE = ('_get_conf_file', '_conf_files', '_conf_runtime', 'read_conf',
            ('parse_conf_name', staticmethod), ('get_config', staticmethod),
            ('has_config', staticmethod))

    _CONF_ID = '[a-zA-Z_][a-zA-Z_0-9]*'
    _CONF_NAME_RE = re.compile('^(?:('+_CONF_ID+')\.)?('+_CONF_ID+')$')

    _configs = {}

    def __init__(self, id, conf_env_var, conf_filename, defaults, opts):
        if self._configs.has_key(id):
            raise exceptions.RuntimeError('configuration already defined')
        self.id = id
        self.conf_env_var = conf_env_var
        self.conf_filename = conf_filename
        self.defaults = defaults
        self.opts = opts
        self.conf = None
        self.read_conf()
        self._configs[id] = self

    def print_conf(conf, raw=False, defaults={}, show_defaults=False):
        if show_defaults and defaults:
            print "defaults=dict("
            for key, value in defaults.items():
                print "%s=%r" % (key, value)
            print ")\n"
        defs = conf.items('DEFAULT', raw=raw)
        print "[DEFAULT]"
        for key, value in defs:
            if defaults.has_key(key) and defaults[key] == value:
                continue
            print "%s=%r" % (key, value)
        print ""
        defs = dict(defs)
        for section in conf.sections():
            if section == 'DEFAULT':
                continue
            print "[%s]" % section
            for key, value in conf.items(section, raw=raw):
                if defs.has_key(key) and defs[key] == value:
                    continue
                print "%s=%r" % (key, value)
            print ""
    print_conf = staticmethod(print_conf)

    def print_(self, raw=False, defaults_display='include'):
        print "\n=== %s ===" % self.id
        if defaults_display:
            defaults_display = defaults_display.lower()
        if not defaults_display or defaults_display == 'include':
            defs = {}
            show_defaults = False
        elif defaults_display == 'exclude':
            defs = self.defaults
            show_defaults = False
        elif defaults_display in ('show', 'extra'):
            defs = self.defaults
            show_defaults = True
        else:
            raise exceptions.NotImplementedError('print_ does not know how to handle %s' % (defaults_display,))
        self.print_conf(self.conf, raw=raw, defaults=defs,
                show_defaults=show_defaults)

    def read_conf(self):
        conf = _ConfigParserFix(self.defaults)
        conf.read(self._get_conf_file(self.opts.get(self.conf_env_var, '')))
        for (sec_name, value) in self.opts.items():
            sec_name_pair = self.parse_conf_name(sec_name)
            if not sec_name_pair:
                print >> sys.stderr, "--- WARNING: Unknown option %r." % sec_name
                continue
            section, name = sec_name_pair
            conf.set(section, name, value)
        self.conf = conf

    def parse_conf_name(name):
        """Parses configuration name in form [SECTION.]NAME."""
        if isinstance(name, (tuple, list)):
            if len(name) == 1:
                return ('DEFAULT', name[0])
            if len(name) == 2:
                return (name[0], name[1])
            raise exceptions.RuntimeError('tuple %r should have one or two items.' % name)
        if isinstance(name, basestring):
            match = _Config._CONF_NAME_RE.match(name)
            if not match:
                return None
            return (match.group(1) or 'DEFAULT', match.group(2))
    parse_conf_name = staticmethod(parse_conf_name)

    def _check_conf_file(self, filename):
        """Check the existence of configuration file."""
        if filename and os.path.isfile(filename):
            return filename
        return None

    def _conf_runtime(self, opt=None):
        return [opt, os.environ.get(self.conf_env_var)]

    def _conf_files(self):
        conf_list = []
        if os.environ.has_key('HOME'):
            conf_list.append(os.environ.get('HOME')+'/.'+self.conf_filename)
        if sys.prefix not in ['', '/', '/usr']:
            conf_list.append(sys.prefix + '/etc/'+self.conf_filename)
        conf_list.append('/etc/'+self.conf_filename)
        return conf_list

    def _get_conf_file(self, opt=None):
        """Find a configuration file or raise an exception."""
        conf_list = self._conf_runtime(opt) + self._conf_files()
        for conf_file in conf_list:
            if self._check_conf_file(conf_file):
                return conf_file
        raise exceptions.Exception("Could not find configuration file.")

    def has_config(id):
        return _Config._configs.get(id, None)
    has_config = staticmethod(has_config)

    def get_config(id):
        return _Config._configs[id]
    get_config = staticmethod(get_config)


class _BeahConfig(_Config):

    _VERBOSE = ('_conf_files', ('beah_conf', staticmethod), ('backend_conf', staticmethod))

    def _conf_files(self):
        if os.environ.has_key('BEAH_ROOT'):
            # used in devel.environment only:
            conf_list = [os.environ.get('BEAH_ROOT')+'/'+self.conf_filename, os.environ.get('BEAH_ROOT')+'/etc/'+self.conf_filename]
        else:
            conf_list = []
        return conf_list + _Config._conf_files(self)

    def beah_conf(opts):
        return _BeahConfig('beah', 'BEAH_CONF', 'beah.conf', {}, opts)
    beah_conf = staticmethod(beah_conf)

    def backend_conf(id, conf_env_var, conf_filename, defaults, opts):
        defs = dict(defaults)
        defs.update(defaults)
        dict_update(defs, _Config.get_config('beah').conf.items('BACKEND'))
        return _BeahConfig(id, conf_env_var, conf_filename, defs, opts)
    backend_conf = staticmethod(backend_conf)


def get_conf(id):
    return _Config.get_config(id).conf


def beah_conf(opts={}):
    return _BeahConfig.beah_conf(opts)


def backend_conf(id, conf_env_var, conf_filename, defaults={}, opts={}):
    return _BeahConfig.backend_conf(id, conf_env_var, conf_filename, defaults, opts)


def _get_config(id):
    return _Config.get_config(id)


def beah_opts():
    opts = {}
    # Process environment:
    if os.environ.has_key('BEAH_DEVEL'):
        opts['DEFAULT.DEVEL'] = os.environ.get('BEAH_DEVEL', 'False')
    # Process command line options:
    return opts


def parse_bool(arg):
    """Permissive string into bool parser."""
    if arg == True or arg == False:
        return arg
    if str(arg).strip().lower() in ['', '0', 'false']:
        return False
    return True


# FIXME!!! move conf_opt to beah_opts? factor out common options.
def conf_opt():
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
    return opt
# FIXME!!! define common options for backends (tasks use env.variables)


if __name__ == '__main__':
    make_class_verbose(_BeahConfig, print_this)
    beah_conf({'BEAH_CONF':'', 'TEST':'Test'})
    def dump_config(config):
        print "\n=== Dump:%s ===" % config.id
        print "files: %s + %s" % (config._conf_runtime({}), config._conf_files())
        print "file: %s" % (config._get_conf_file({}), )
    _get_config('beah').print_()
    backend_conf('beah-beaker-backend', 'BEAH_BEAKER_CONF', 'beah_beaker.conf', {'MY_OWN':'1'}, {'MY_OWN':'2', 'DEFAULT.MY_OWN':'3'})
    _get_config('beah-beaker-backend').print_()
    _get_config('beah-beaker-backend').print_(defaults_display='exclude')
    _get_config('beah-beaker-backend').print_(defaults_display='show')
    _get_config('beah-beaker-backend').print_(raw=True)
    _get_config('beah-beaker-backend').print_(raw=True, defaults_display='exclude')
    _get_config('beah-beaker-backend').print_(raw=True, defaults_display='show')
    #dump_config(_get_config('beah-beaker-backend'))

    def _test():

        """Self test."""

        c = _Config('test', 'BEAH_CONF', 'beah.conf', {}, dict(ROOT='/tmp', LOG='False', DEVEL='True', BEAH_CONF='beah.conf'))
        print c._get_conf_file()

        cfg = c.conf

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


