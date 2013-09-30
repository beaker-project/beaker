# $Id: util.py,v 1.2 2006/12/31 09:10:14 lmacken Exp $
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""
Random functions that don't fit elsewhere
"""

import os
import sys
import logging
import socket
import datetime
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import create_session
import turbogears
from turbogears import config, url
from turbogears.database import get_engine
import socket

log = logging.getLogger(__name__)

_config_loaded = None
def load_config(configfile=None):
    """ Loads Beaker's configuration and configures logging. """
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

    # In general, we want all messages from application code.
    logging.getLogger().setLevel(logging.DEBUG)
    # Well-behaved libraries will set their own log levels to something 
    # suitable (sqlalchemy sets it to WARNING, for example) but the TurboGears 
    # stuff leaves its unset.
    logging.getLogger('turbomail').setLevel(logging.INFO)
    logging.getLogger('turbogears').setLevel(logging.INFO)
    logging.getLogger('turbokid').setLevel(logging.INFO)
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
    if configdata.has_key('logging'):
        raise RuntimeError('TurboGears logging configuration is not supported, '
                'remove [logging] section from config file %s' % configfile)

    turbogears.update_config(configfile=configfile, modulename="bkr.server.config")
    _config_loaded = configfile

def to_unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding, 'replace')
    return obj

def url_no_webpath(tgpath, tgparams=None, **kw):
    """
    Like turbogears.url but without webpath pre-pended
    """
    webpath = (config.get('server.webpath') or '').rstrip('/')
    theurl = url(tgpath, tgparams=tgparams, **kw)
    if webpath and theurl.startswith(webpath):
        theurl = theurl[len(webpath):]
    return theurl

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
    order = []
    if labdomain:
        order.append(config.get('tg.lab_domain'))
    order.extend([config.get('tg.url_domain'),
                  config.get('servername'),
                  socket.getfqdn()])

    # TODO support relative paths
    if webpath:
        theurl = url(tgpath, tgparams, **kw)
    else:
        theurl = url_no_webpath(tgpath, tgparams, **kw)
    assert theurl.startswith('/')
    scheme = scheme or config.get('tg.url_scheme', 'http')
    host_port = filter(None, order)[0]
    return '%s://%s%s' % (scheme, host_port, theurl)

# http://stackoverflow.com/questions/1809531/_/1820949#1820949
def unicode_truncate(s, bytes_length, encoding='utf8'):
    """
    Returns a copy of the given unicode string, truncated to fit within the 
    given number of bytes when encoded.
    """
    if len(s) * 4 < bytes_length: return s # fast path
    encoded = s.encode(encoding)[:bytes_length]
    return encoded.decode(encoding, 'ignore')

_reports_engine = None
def get_reports_engine():
    global _reports_engine
    if config.get('reports_engine.dburi'):
        if not _reports_engine:
            # same logic as in turbogears.database.get_engine
            engine_args = dict()
            for k, v in config.config.configMap['global'].iteritems():
                if k.startswith('reports_engine.'):
                    engine_args[k[len('reports_engine.'):]] = v
            dburi = engine_args.pop('dburi')
            log.debug('Creating reports_engine: %r %r', dburi, engine_args)
            _reports_engine = create_engine(dburi, **engine_args)
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
                func(*args, **kwargs)
            except:
                logger.exception('Uncaught exception in %s', func.__name__)
                raise
        decorated.__name__ = func.__name__
        decorated.__doc__ = func.__doc__
        decorated.__dict__.update(func.__dict__)
        return decorated
    return decorator

# This is a method on timedelta in Python 2.7+
def total_seconds(td):
    """
    Returns the total number of seconds (float)
    represented by the given timedelta.
    """
    return (float(td.microseconds) + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
