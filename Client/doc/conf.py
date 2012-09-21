
extensions = ['sphinx.ext.autodoc']
master_doc = 'index'
exclude_patterns = ['_build']

project = u'Beaker client'
copyright = u'2012, Red Hat, Inc'
import bkr
version = bkr.__version__
release = version

html_title = 'Beaker client documentation'

# subcommands are automatically generated, see extension below
man_pages = [
    ('bkr', 'bkr', 'Beaker client',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 1),
    ('bkr-workflow-xslt', 'bkr-workflow-xslt', 'XSLT-based Beaker job generator',
        [u'David Sommerseth <davids@redhat.com>'], 1),
    ('beaker-wizard', 'beaker-wizard', 'Tool to ease the creation of a new Beaker task',
        [u'Petr Splichal <psplicha@redhat.com>'], 1),
]
man_show_urls = True

# This config is also a Sphinx extension with some Beaker-specific customisations:

import os
import docutils.core

def generate_subcommand_docs(app):
    """
    Finds Beaker client subcommand modules matching bkr.client.commands.cmd_* 
    and creates a Sphinx document for each one.
    """
    from bkr.client import BeakerCommand
    from bkr.client.main import BeakerCommandContainer
    import bkr.client.commands
    for module_name in dir(bkr.client.commands):
        if module_name.startswith('cmd_'):
            module = getattr(bkr.client.commands, module_name)
            if not module.__doc__:
                continue
            for item in module.__dict__.values():
                if isinstance(item, type) and issubclass(item, BeakerCommand) and item.enabled:
                    docname = 'bkr-%s' % BeakerCommandContainer.normalize_name(item.__name__)
                    doc = module.__doc__
                    doctitle = doc.splitlines()[1] # XXX dodgy, parse doc instead
                    outpath = os.path.join(app.srcdir, '%s.rst' % docname)
                    # only write it if the contents have changed, this helps conditional builds
                    if not os.path.exists(outpath) or open(outpath, 'r').read() != module.__doc__:
                        with open(outpath, 'w') as f:
                            f.write(module.__doc__)
                    description = doctitle.partition(': ')[2]
                    app.config.man_pages.append((docname, docname, description,
                            [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 1))

def setup(app):
    app.connect('builder-inited', generate_subcommand_docs)
