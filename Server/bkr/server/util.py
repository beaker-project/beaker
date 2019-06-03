# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Random functions that don't fit elsewhere
"""

import contextlib
import logging
import os
import re
import socket
import subprocess
import sys
from collections import namedtuple

import lxml.etree
import turbogears
from sqlalchemy import create_engine
from sqlalchemy.orm.exc import NoResultFound
from turbogears import config, url
from turbogears.database import get_engine

from bkr.server.app import app
from bkr.server.bexceptions import DatabaseLookupError

log = logging.getLogger(__name__)

_config_loaded = None


def load_config_or_exit(configfile=None):
    try:
        load_config(configfile=configfile)
    except Exception as e:
        sys.stderr.write('Failed to read server configuration. %s.\n'
                         'Hint: run this command as root\n' % e)
        sys.exit(1)


def load_config(configfile=None):
    """
    Loads Beaker's configuration and configures logging.
    """
    setupdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    curdir = os.getcwd()
    if configfile and os.path.exists(configfile):
        pass
    elif 'BEAKER_CONFIG_FILE' in os.environ:
        configfile = os.environ['BEAKER_CONFIG_FILE']
    elif os.path.exists(os.path.join(setupdir, 'setup.py')) \
            and os.path.exists(os.path.join(setupdir, 'dev.cfg')):
        configfile = os.path.join(setupdir, 'dev.cfg')
    elif os.path.exists(os.path.join(curdir, 'beaker.cfg')):
        configfile = os.path.join(curdir, 'beaker.cfg')
    elif os.path.exists('/etc/beaker.cfg'):
        configfile = '/etc/beaker.cfg'
    elif os.path.exists('/etc/beaker/server.cfg'):
        configfile = '/etc/beaker/server.cfg'
    else:
        raise RuntimeError("Unable to find configuration to load!")

    # We only allow the config to be loaded once, update_config()
    # doesn't seem to update the config when called more than once
    # anyway
    configfile = os.path.realpath(configfile)
    global _config_loaded
    if _config_loaded is not None and configfile == _config_loaded:
        return
    elif _config_loaded is not None and configfile != _config_loaded:
        raise RuntimeError('Config has already been loaded from %s' % \
                           _config_loaded)

    # In general, we want all messages from application code, but no debugging
    # messages from the libraries we are using.
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger('bkr').setLevel(logging.DEBUG)
    # We don't need access logs from TurboGears, we have the Apache logs.
    logging.getLogger('turbogears.access').setLevel(logging.WARN)
    # Note that the actual level of log output is controlled by the handlers,
    # not the loggers (for example command line tools will typically log to
    # stderr at WARNING level). The main entry point for the program should
    # call bkr.log.log_to_{syslog,stream} to set up a handler.

    # We do not want TurboGears to touch the logging config, so let's
    # double-check the user hasn't left an old [logging] section in their
    # config file.
    from configobj import ConfigObj
    configdata = ConfigObj(configfile, unrepr=True)
    if 'logging' in configdata:
        raise RuntimeError('TurboGears logging configuration is not supported, '
                           'remove [logging] section from config file %s' % configfile)
    if not 'global' in configdata:
        raise RuntimeError('Config file is missing section [global]')

    # Read our beaker config and store it to Flask config
    app.config.update(configdata['global'])
    # Keep this until we completely remove TurboGears
    turbogears.update_config(configfile=configfile, modulename="bkr.server.config")
    _config_loaded = configfile


def to_unicode(obj, encoding='utf-8'):
    # TODO: Not needed for Python 3
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding, 'replace')
    return obj


def strip_webpath(url):
    webpath = (config.get('server.webpath') or '').rstrip('/')
    if webpath and url.startswith(webpath):
        return url[len(webpath):]
    return url


# TG1.1 has this: http://docs.turbogears.org/1.1/URLs#turbogears-absolute-url
def absolute_url(tgpath, tgparams=None, scheme=None,
                 labdomain=False, webpath=True, **kw):
    """
    Like turbogears.url, but makes the URL absolute (with scheme, hostname,
    and port from the tg.url_scheme and tg.url_domain configuration
    directives).
    If labdomain is True we serve an alternate tg.proxy_domain if defined
    in server.cfg.  This is to support multi-home systems which have
    different external vs internal names.
    """
    if labdomain and app.config.get('tg.lab_domain'):
        host_port = app.config.get('tg.lab_domain')
    elif app.config.get('tg.url_domain'):
        host_port = app.config.get('tg.url_domain')
    elif app.config.get('servername'):  # deprecated
        host_port = app.config.get('servername')
    else:
        # System hostname is cheap to look up (no DNS calls) but there is no
        # requirement that it be fully qualified.
        kernel_hostname = socket.gethostname()
        if '.' in kernel_hostname:
            host_port = kernel_hostname
        else:
            # Last resort, let glibc do a DNS lookup through search domains etc.
            host_port = socket.getfqdn()

    # TODO support relative paths
    theurl = url(tgpath, tgparams, **kw)
    if not webpath:
        theurl = strip_webpath(theurl)
    assert theurl.startswith('/')
    scheme = scheme or app.config.get('tg.url_scheme', 'http')
    return '%s://%s%s' % (scheme, host_port, theurl)


_reports_engine = None


def get_reports_engine():
    global _reports_engine
    if app.config.get('reports_engine.dburi'):
        if not _reports_engine:
            # same logic as in turbogears.database.get_engine
            engine_args = dict()
            for k, v in app.config.iteritems():
                if k.startswith('reports_engine.'):
                    engine_args[k[len('reports_engine.'):]] = v
            dburi = engine_args.pop('dburi')
            _reports_engine = create_engine(dburi, **engine_args)
            log.debug('Created reports_engine %r', _reports_engine)
        return _reports_engine
    else:
        log.debug('Using default engine for reports_engine')
        return get_engine()


# Based on a similar decorator from kobo.decorators
def log_traceback(logger):
    """
    A decorator which will log uncaught exceptions to the given logger, before
    re-raising them.
    """

    def decorator(func):
        def decorated(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                logger.exception('Uncaught exception in %s', func.__name__)
                raise

        decorated.__name__ = func.__name__
        decorated.__doc__ = func.__doc__
        decorated.__dict__.update(func.__dict__)
        return decorated

    return decorator


def run_createrepo(cwd=None, update=False):
    createrepo_command = config.get('beaker.createrepo_command', 'createrepo_c')
    args = [createrepo_command, '-q', '--no-database', '--checksum', 'sha']
    if update:
        args.append('--update')
    args.append('.')
    log.debug('Running createrepo as %r in %s', args, cwd)
    p = subprocess.Popen(args, cwd=cwd, stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    # Perhaps a bit fragile, but maybe better than checking version?
    if p.returncode != 0 and 'no such option: --no-database' in err:
        args.remove('--no-database')
        log.debug('Re-trying createrepo as %r in %s', args, cwd)
        p = subprocess.Popen(args, cwd=cwd, stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
    RepoCreate = namedtuple("RepoCreate", "command returncode out err")
    return RepoCreate(createrepo_command, p.returncode, out, err)


# Validate FQDN for a system
# http://stackoverflow.com/questions/1418423/_/1420225#1420225
VALID_FQDN_REGEX = (r"^(?=.{1,255}$)[0-9A-Za-z]"
                    r"(?:(?:[0-9A-Za-z]|\b-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z]"
                    r"(?:(?:[0-9A-Za-z]|\b-){0,61}[0-9A-Za-z])?)*\.?$")
# do this at the global scope to avoid compiling it on every call
regex_compiled = re.compile(VALID_FQDN_REGEX)


def is_valid_fqdn(fqdn):
    return regex_compiled.search(fqdn)


@contextlib.contextmanager
def convert_db_lookup_error(msg):
    """
    Context manager to handle SQLA's NoResultFound and report
    a custom error message
    """
    try:
        yield
    except NoResultFound:
        raise DatabaseLookupError(msg)


def parse_untrusted_xml(s):
    """
    Parses untrusted XML as a string and raises a ValueError if system entities
    are found.
    See: http://lxml.de/FAQ.html#how-do-i-use-lxml-safely-as-a-web-service-endpoint
    """
    parser = lxml.etree.XMLParser(resolve_entities=False, strip_cdata=False)
    root = lxml.etree.fromstring(s, parser)
    for ent in root.iter(lxml.etree.Entity):
        # fail once we find any system entity which is not supported
        raise ValueError('XML entity with name %s not permitted' % ent)
    return root
