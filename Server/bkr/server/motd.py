import logging
import os.path
import turbogears as tg
from lxml import etree
import logging
log = logging.getLogger(__name__)

try:
    motd_filename = tg.config.get('beaker.motd', '/etc/beaker/motd.xml')
    if not os.path.exists(motd_filename):
        log.info('Motd not found at %s, ignoring', motd_filename)
        the_motd = None
    else:
        f = open(motd_filename, 'rb')
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(f,parser)
        the_motd = etree.tostring(tree.getroot())
except Exception, e:
    log.exception('Unable to read motd')
    the_motd = None
