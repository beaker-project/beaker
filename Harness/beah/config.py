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
import random
from ConfigParser import ConfigParser
from optparse import OptionParser
from beah.misc import dict_update


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

    def _remove(id):
        del _Config._configs[id]
    _remove = staticmethod(_remove)

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
            tmpkey = "DEFAULT.%s" % key
            if defaults.has_key(tmpkey) and defaults[tmpkey] == value:
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
                tmpkey = "%s.%s" % (section, key)
                if defaults.has_key(tmpkey) and defaults[tmpkey] == value:
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

    def _conf_opt(self):
        return self.opts.get(self.conf_env_var, '')

    def upd_conf(conf, dict, warn_section=False):
        for (sec_name, value) in dict.items():
            sec_name_pair = _Config.parse_conf_name(sec_name)
            if not sec_name_pair:
                print >> sys.stderr, "--- WARNING: Can not parse %r." % sec_name
                continue
            section, name = sec_name_pair
            if not isinstance(value, basestring):
                print >> sys.stderr, "--- WARNING: Value for %s.%s (%r) is not an string." % (section, name, value)
                continue
            if section and section != 'DEFAULT' and not conf.has_section(section):
                if warn_section:
                    print >> sys.stderr, "--- WARNING: Section %r does not exist." % section
                conf.add_section(section)
            conf.set(section, name, value)
    upd_conf = staticmethod(upd_conf)

    def read_conf(self):
        conf = _ConfigParserFix()
        self.upd_conf(conf, self.defaults, warn_section=False)
        fn = self._get_conf_file(self._conf_opt())
        if not fn:
            if self.conf_filename:
                print >> sys.stderr, "--- WARNING: Could not find conf.file."
        else:
            try:
                #print "--- INFO: Reading %r." % fn
                conf.read(fn)
                #self.print_conf(conf)
            except:
                print >> sys.stderr, "--- ERROR: Could not read %r." % fn
                raise
        self.upd_conf(conf, self.opts, warn_section=True)
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
        return [opt, os.environ.get(self.conf_env_var, None)]

    def _conf_files(self):
        conf_list = []
        if self.conf_filename:
            if os.environ.has_key('HOME'):
                conf_list.append(os.environ.get('HOME')+'/.'+self.conf_filename)
            if sys.prefix not in ['', '/', '/usr']:
                conf_list.append(sys.prefix + '/etc/'+self.conf_filename)
            conf_list.append('/etc/'+self.conf_filename)
        return conf_list

    def _get_conf_file(self, opt=None):
        """Find a configuration file or raise an exception."""
        conf_list = self._conf_runtime(opt) + self._conf_files()
        no_file = True
        for conf_file in conf_list:
            if conf_file:
                no_file = False
                if self._check_conf_file(conf_file):
                    return conf_file
        if no_file:
            return ''
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
        conf_list = []
        if self.conf_filename and os.environ.has_key('BEAH_ROOT'):
            # used in devel.environment only:
            conf_list = [os.environ.get('BEAH_ROOT')+'/'+self.conf_filename,
                    os.environ.get('BEAH_ROOT')+'/etc/'+self.conf_filename]
        return conf_list + _Config._conf_files(self)

    def beah_conf(opts):
        return _BeahConfig('beah', 'BEAH_CONF', 'beah.conf', beah_defaults(), opts)
    beah_conf = staticmethod(beah_conf)

    def backend_conf(id, conf_env_var, conf_filename, defaults, opts):
        defs = dict(defaults)
        dict_update(defs, _Config.get_config('beah-tmp').conf.items('BACKEND', raw=True))
        _Config._remove('beah-tmp')
        return _BeahConfig(id, conf_env_var, conf_filename, defs, opts)
    backend_conf = staticmethod(backend_conf)


def get_conf(id):
    return _Config.get_config(id).conf


def defaults():
    return dict(
            LOG='Warning',
            ROOT='',
            ETC_ROOT='%(ROOT)s/etc',
            VAR_ROOT='%(ROOT)s/var/beah',
            LOG_PATH='%(ROOT)s/var/log',
            DEVEL='False',
            CONSOLE_LOG='False',
            NAME='beah-default-%2.2d' % random.randint(0,99),
            RUNTIME_FILE_NAME='%(VAR_ROOT)s/%(NAME)s.runtime',
            )


def beah_defaults():
    d = defaults()
    d.update({
            'CONTROLLER.NAME':'beah',
            'CONTROLLER.LOG_FILE_NAME':'%(LOG_PATH)s/%(NAME)s.log',
            'BACKEND.INTERFACE':'',
            'BACKEND.PORT':'12432',
            'TASK.INTERFACE':'localhost',
            'TASK.PORT':'12434'})
    return d


def backend_defaults():
    return {}


def beah_conf(overrides=None, args=None):
    if overrides is None:
        overrides = beah_opts(args)
    return _BeahConfig.beah_conf(overrides)


def backend_conf(env_var=None, filename=None, defaults={}, overrides={}):
    return _BeahConfig.backend_conf('beah-backend', env_var, filename, defaults, overrides)


def _get_config(id):
    return _Config.get_config(id)


def proc_verbosity(opts, conf):
    if opts.verbose is not None or opts.quiet is not None:
        verbosity = int(opts.verbose or 0) - int(opts.quiet or 0)
    else:
        return
    if verbosity >= 3:
        conf['DEVEL'] = 'True'
    if not conf.has_key('LOG'):
        level = 'error'
        if verbosity > 2:
            level = 'debug'
        else:
            level = ('warning', 'info', 'debug')[verbosity]
        conf['LOG'] = level


def beah_opts_aux(opt, conf, args=None):
    if args is None:
        args = sys.argv[1:]
    # Process environment:
    if os.environ.has_key('BEAH_DEVEL'):
        conf['DEVEL'] = os.environ.get('BEAH_DEVEL', 'False')
    # Process command line options:
    opts, rest = opt.parse_args(args)
    proc_verbosity(opts, conf)
    return conf, rest


def beah_opts(args=None):
    conf = {}
    conf, rest = beah_opts_aux(beah_opt(OptionParser(), conf), conf, args=args)
    if rest:
        opt.print_help()
        raise exceptions.RuntimeError('Program accepts no positional arguments.')
    return conf


def backend_opts_ex(args=None, option_adder=None):
    conf = {}
    opt = backend_opt(OptionParser(), conf)
    if option_adder is not None:
        opt = option_adder(opt, conf)
    conf, rest = beah_opts_aux(opt, conf, args=args)
    if conf.get('BEAH_CONF', ''):
        conf2 = {'BEAH_CONF': conf['BEAH_CONF']}
    else:
        conf2 = {}
    _BeahConfig('beah-tmp', 'BEAH_CONF', 'beah.conf', {}, conf2)
    return conf, rest


def backend_opts(args=None, option_adder=None):
    conf, rest = backend_opts_ex(args, option_adder)
    if rest:
        opt.print_help()
        raise exceptions.RuntimeError('Program accepts no positional arguments.')
    return conf


def parse_bool(arg):
    """Permissive string into bool parser."""
    if arg == True or arg == False:
        return arg
    if str(arg).strip().lower() in ['', '0', 'false']:
        return False
    return True


def default_opt(opt, conf, kwargs):
    """
    Parser for common options.
    """
    opt.disable_interspersed_args()
    def config_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        conf['BEAH_CONF'] = value
    opt.add_option("-c", "--config",
            action="callback", callback=config_cb, type='string',
            help="Use FILE for configuration.", metavar="FILE")
    def name_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        if kwargs['type'] == 'beah':
            conf['CONTROLLER.NAME'] = value
        else:
            conf['NAME'] = value
    opt.add_option("-n", "--name",
            action="callback", callback=name_cb, type='string',
            help="Use NAME as identification.")
    opt.add_option("-v", "--verbose", action="count",
            help="Increase verbosity.")
    opt.add_option("-q", "--quiet", action="count",
            help="Decrease verbosity.")
    def log_stderr_cb(option, opt_str, value, parser, arg):
        conf['CONSOLE_LOG'] = arg
    opt.add_option("-O", "--log-stderr", action="callback",
            callback=log_stderr_cb, callback_args=("True",),
            help="Write all logging to stderr.")
    opt.add_option("--no-log-stderr", action="callback",
            callback=log_stderr_cb, callback_args=("False",),
            help="Do not write logging info to stderr.")
    def log_level_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        conf['LOG'] = value
    opt.add_option("-L", "--log-level",
            action="callback", callback=log_level_cb, type='string',
            help="Specify log level explicitly.")
    return opt


def beah_be_opt(opt, conf, kwargs):
    def interface_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        if kwargs['type'] == 'beah':
            conf['BACKEND.INTERFACE'] = value
        else:
            conf['INTERFACE'] = value
    opt.add_option("-i", "--interface", action="callback",
            callback=interface_cb, type='string',
            help="interface backends are connecting to.")
    def port_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        if kwargs['type'] == 'beah':
            conf['BACKEND.PORT'] = value
        else:
            conf['PORT'] = value
    opt.add_option("-p", "--port", action="callback", callback=port_cb,
            type='string',
            help="port number backends are using.")
    return opt


def beah_t_opt(opt, conf, kwargs):
    def interface_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        if kwargs['type'] == 'beah':
            conf['TASK.INTERFACE'] = value
        else:
            conf['INTERFACE'] = value
    opt.add_option("-I", "--task-interface", action="callback",
            callback=interface_cb, type='string',
            help="interface tasks are connecting to.")
    def port_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        if kwargs['type'] == 'beah':
            conf['TASK.PORT'] = value
        else:
            conf['PORT'] = value
    opt.add_option("-P", "--task-port", action="callback", callback=port_cb,
            type='string',
            help="port number tasks are using.")
    return opt


def beah_opt(opt, conf, kwargs=None):
    """
    Parser for beah-server
    """
    kwargs = dict(kwargs or {})
    kwargs['type'] = 'beah'
    default_opt(opt, conf, kwargs)
    beah_be_opt(opt, conf, kwargs)
    beah_t_opt(opt, conf, kwargs)
    return opt


def backend_opt(opt, conf, kwargs=None):
    """
    Parser for backends
    """
    kwargs = dict(kwargs or {})
    kwargs['type'] = 'backend'
    default_opt(opt, conf, kwargs)
    beah_be_opt(opt, conf, kwargs)
    def backend_conf_cb(option, opt_str, value, parser):
        # FIXME!!! check value
        conf['BACKEND_CONF'] = value
    opt.add_option("-C", "--backend-config", action="callback",
            callback=backend_conf_cb, type='string',
            help="Use BACKEND_CONFIG for configuration.")
    return opt


if __name__ == '__main__':

    from beah.misc import log_this, make_class_verbose

    def _tst_eq(result, expected):
        """Check test result against expected value and assert on
        missmatch."""
        try:
            assert result == expected
        except:
            print "Failed: result:%r == expected:%r" % (result, expected)
            raise

    def _tst_ne(result, expected):
        """Check test result against expected value and assert on
        missmatch."""
        try:
            assert result != expected
        except:
            print "Failed: result:%r != expected:%r" % (result, expected)
            raise

    def _try_beah_conf():
        beah_conf(overrides={'BEAH_CONF':'', 'TEST':'Test'}, args=())
        def dump_config(config):
            print "\n=== Dump:%s ===" % config.id
            print "files: %s + %s" % (config._conf_runtime(None), config._conf_files())
            print "file: %s" % (config._get_conf_file({}), )
        _get_config('beah').print_()
        _Config._remove('beah')

    def _try_backend_conf():
        _BeahConfig('beah-tmp', None, None, beah_defaults(), {})
        backend_conf('BEAH_BEAKER_CONF', 'beah_beaker.conf', {'MY_OWN':'1', 'TEST.MY_OWN':'2'}, {'DEFAULT.MY_OWN':'4', 'TEST.MY_OWN':'3'})
        _get_config('beah-backend').print_()
        #_get_config('beah-backend').print_(defaults_display='exclude')
        #_get_config('beah-backend').print_(defaults_display='show')
        #_get_config('beah-backend').print_(raw=True)
        #_get_config('beah-backend').print_(raw=True, defaults_display='exclude')
        #_get_config('beah-backend').print_(raw=True, defaults_display='show')
        #dump_config(_get_config('beah-backend'))
        _Config._remove('beah-backend')

    def _try_conf():
        #_try_beah_conf()
        _try_backend_conf()

    def _try_conf2():
        overrides = backend_opts()
        #c = _get_config('beah-tmp')
        #print c._get_conf_file()
        #c.print_()
        backend_conf(
                defaults={'NAME':'beah_demo_backend'},
                overrides=overrides)
        #_Config._remove('beah')
        _Config._remove('beah-backend')

    def _test_conf():

        """Self test."""

        _tst_eq(_Config.parse_conf_name('NAME'), ('DEFAULT', 'NAME'))
        _tst_eq(_Config.parse_conf_name('SEC.NAME'), ('SEC', 'NAME'))

        c = _Config('test', 'BEAH_CONF', 'beah.conf', {}, dict(ROOT='/tmp', LOG='False', DEVEL='True', BEAH_CONF='beah.conf'))
        _tst_eq(c._get_conf_file('beah.conf'), 'beah.conf')
        _tst_eq(c._get_conf_file('beah.conf.tmp'), 'beah.conf.tmp')
        try:
            _tst_ne(c._get_conf_file('empty-beah.conf.tmp'), 'empty-beah.conf.tmp')
            raise exceptions.RuntimeError("c._get_conf_file('empty-beah.conf.tmp') should have failed with exception")
        except:
            pass

        cfg = c.conf
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

        try:
            c = _Config('test2', None, 'empty-missing-no.conf', dict(GREETING="Hello %(NAME)s!"), dict(NAME="World"))
            _Config._remove('test2')
            raise exceptions.RuntimeError("this should have failed with exception")
        except:
            pass

        c = _Config('test3', None, None, dict(GREETING="Hello %(NAME)s!"), dict(NAME="World"))
        _tst_eq(c.conf.get('DEFAULT', 'GREETING'), 'Hello World!')
        _tst_eq(get_conf('test3').get('DEFAULT', 'GREETING'), 'Hello World!')
        _Config._remove('test')
        _Config._remove('test3')

    def _test_opt():
        conf = {}
        opt = beah_opt(OptionParser(), conf)
        #print opt.get_usage()
        #opt.print_help()
        #print opt.format_help()

        cmd_args = '-v -v -q -L info -O arg1 arg2'.split(' ')
        opts, args = opt.parse_args(cmd_args)
        #print opts, args, conf
        assert opts.verbose == 2
        assert opts.quiet == 1
        assert conf['LOG'] == 'info'
        assert conf['CONSOLE_LOG'] == 'True'

        cmd_args = "-v -v -v -v -q -p 1234 -i '' -P 4321 -I localhost -c conf -L debug -O arg1 arg2".split(" ")
        opts, args = opt.parse_args(cmd_args)
        #print opts, args, conf

        if 0:
            def cb_test(option, opt_str, value, parser):
                print option, opt_str, value, parser
                #print dir(option)
                #print dir(parser)
                print option.dest
                print option.metavar
            opt.add_option("--cb", "--test-cb", "--cb-test", action="callback", callback=cb_test)
            opt.parse_args(['--cb'])

    #make_class_verbose(_BeahConfig, log_this.print_this)
    _try_conf()
    _test_conf()
    _test_opt()
    _try_conf2()

