#!/usr/bin/python

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['TurboGears']

import sys
from bkr.server.model import Product
from bkr.server.util import load_config, log_to_stream
from lxml import etree
from optparse import OptionParser
from turbogears.database import session
from sqlalchemy.orm.exc import NoResultFound

__version__ = '0.1'
__description__ = 'Script to update product table with cpe'

USAGE_TEXT = """ Usage: product_update --file <product_xml_file> """


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option("-f","--product-file", default=None, dest='productfile',
                      help="This should be the XML file that contains the product cpe")
    parser.add_option("-c","--config-file",dest="configfile",default=None)
    return parser


def usage():
    print USAGE_TEXT
    sys.exit(-1)

def update_products(xml_file):
    dom = etree.parse(xml_file)
    xpath_string = '//cpe'
    cpes = dom.xpath(xpath_string)
    
    session.begin()
    try:
        to_add = {}
        dupe_errors = []
        for cpe in cpes:
            cpe_text = cpe.text

            if cpe_text in to_add:
                dupe_errors.append(cpe_text)
            else:
                to_add[cpe_text] = 1

        for cpe_to_add in to_add:
            try:
                prod = Product.by_name(u'%s' % cpe_to_add)
            except NoResultFound:
                session.add(Product(u'%s' % cpe_to_add))
                continue
        session.commit()
    finally:
        session.rollback()

def main():
    parser = get_parser()
    opts,args = parser.parse_args()
    configfile = opts.configfile
    xml_file = opts.productfile
    load_config(configfile)
    log_to_stream(sys.stderr)
    update_products(xml_file)

if __name__ == '__main__':
    main()
