#!/usr/bin/python
from bkr.server.model import Product
from bkr.server.util import load_config
from lxml import etree
from optparse import OptionParser
from turbogears.database import session
from sqlalchemy.exceptions import InvalidRequestError, IntegrityError

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
            except InvalidRequestError, e: 
                if '%s' % e == 'No rows returned for one()':
                    session.save(Product(u'%s' % cpe_to_add))
                    continue
                else:
                    raise
        print 'These are the dupe errors: %s' % dupe_errors
        session.commit()
    finally:
        session.rollback()

def main():
    parser = get_parser()
    opts,args = parser.parse_args()
    configfile = opts.configfile
    xml_file = opts.productfile
    load_config(configfile)
    update_products(xml_file)

if __name__ == '__main__':
    main()
