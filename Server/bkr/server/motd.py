
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import errno
from turbogears import config
from lxml import etree
import logging
log = logging.getLogger(__name__)

# The MOTD is loaded once and cached globally. Admins need to restart the 
# application (or wait for it to be recycled by mod_wsgi) when updating 
# the MOTD.
_motd_loaded = False
_motd = None

def _load_motd(filename):
    try:
        f = open(filename, 'rb')
    except IOError, e:
        if e.errno == errno.ENOENT:
            log.info('Motd not found at %s, ignoring', filename)
            return None
        else:
            raise
    parser = etree.XMLParser(recover=True)
    try:
        tree = etree.parse(f,parser)
    except etree.XMLSyntaxError as e:
        # Workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1298018
        # When recover=True is used, the parser is not supposed to raise 
        # a syntax error. But due to changes in libxml2 the empty document has 
        # started raising.
        log.info('Motd has syntax error, ignoring: %s', e)
        return None
    if tree.getroot() is None:
        return None
    return etree.tostring(tree.getroot(), encoding='utf8')

def get_motd():
    global _motd, _motd_loaded
    if not _motd_loaded:
        try:
            _motd = _load_motd(config.get('beaker.motd', '/etc/beaker/motd.xml'))
        except Exception:
            log.exception('Unable to read motd')
        _motd_loaded = True
    return _motd
