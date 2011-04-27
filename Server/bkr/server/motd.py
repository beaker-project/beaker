import logging
import turbogears as tg
from lxml import etree
import logging
log = logging.getLogger(__name__)

try:
    f = open(tg.config.get('beaker.motd', '/etc/beaker/motd.xml'), 'rb')
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(f,parser)
    the_motd = etree.tostring(tree.getroot())
except Exception, e:
    log.exception('Unable to read motd')
    the_motd = None
