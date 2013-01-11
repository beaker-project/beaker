
extensions = ['sphinx.ext.intersphinx', 'sphinx.ext.todo']
master_doc = 'index'
project = u'Beaker'
copyright = u'2013, Red Hat, Inc'

try:
    import bkr
    version = bkr.__version__
except ImportError:
    version = "dev"
release = version

html_title = 'Beaker'
html_use_index = False
html_domain_indices = False

latex_documents = [
  ('admin-guide/index', 'admin-guide.tex', u'Beaker Administration Guide',
   u'Red Hat, Inc.', 'manual'),
  ('user-guide/index', 'user-guide.tex', u'Beaker User Guide',
   u'Red Hat, Inc.', 'manual'),
]

intersphinx_mapping = {'http://docs.python.org/': None}
