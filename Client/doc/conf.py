import sys, os
sys.path.insert(0, os.path.dirname(__file__))
extensions = ['bkrclientext']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']

project = u'Beaker client'
copyright = u'2012, Red Hat, Inc'
import bkr
version = bkr.__version__
release = version

# subcommands are automatically generated, see bkrclientext.py
man_pages = [
    ('bkr', 'bkr', 'Beaker client',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 1),
    ('bkr-workflow-xslt', 'bkr-workflow-xslt', 'XSLT-based Beaker job generator',
        [u'David Sommerseth <davids@redhat.com>'], 1),
]
