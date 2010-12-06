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
import turbogears
from turbogears import config, url

log = logging.getLogger(__name__)

def load_config(configfile=None):
    """ Load beaker's configuration """
    setupdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    curdir = os.getcwd()
    if configfile and os.path.exists(configfile):
        pass
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
        log.error("Unable to find configuration to load!")
        return
    log.debug("Loading configuration: %s" % configfile)
    turbogears.update_config(configfile=configfile, modulename="bkr.server.config")

def to_unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding, 'replace')
    return obj

# TG1.1 has this: http://docs.turbogears.org/1.1/URLs#turbogears-absolute-url
def absolute_url(tgpath, tgparams=None, **kw):
    """
    Like turbogears.url, but makes the URL absolute (with scheme, hostname, 
    and port from the tg.url_scheme and tg.url_domain configuration 
    directives).
    """
    # TODO support relative paths
    theurl = url(tgpath, tgparams, **kw)
    assert theurl.startswith('/')
    scheme = config.get('tg.url_scheme', 'http')
    host_port = config.get('tg.url_domain',
            '%s:%s' % (config.get('server.socket_host', 'localhost'),
                config.get('socket_port', '8080')))
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
