
extensions = ['sphinx.ext.intersphinx', 'sphinx.ext.todo']
master_doc = 'index'
project = u'Beaker Administration Guide'
copyright = u'2013, Red Hat, Inc'

import bkr
version = bkr.__version__
release = version

html_title = 'Beaker Administration Guide'
html_use_index = False
html_domain_indices = False

latex_documents = [
  ('index', 'admin-guide.tex', u'Beaker Administration Guide',
   u'Red Hat, Inc.', 'manual'),
]

intersphinx_mapping = {'http://docs.python.org/': None}
