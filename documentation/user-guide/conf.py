
extensions = ['sphinx.ext.intersphinx', 'sphinx.ext.todo']
master_doc = 'index'
project = u'Beaker User Guide'
copyright = u'2013, Red Hat, Inc'

import bkr
version = bkr.__version__
release = version

html_title = 'Beaker User Guide'
html_use_index = False
html_domain_indices = False

latex_documents = [
  ('index', 'user-guide.tex', u'Beaker User Guide',
   u'Red Hat, Inc.', 'manual'),
]

intersphinx_mapping = {'http://docs.python.org/': None}
