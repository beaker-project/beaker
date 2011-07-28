
"""
Sphinx extension with useful things related to Beaker client.
"""

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
                    f = open(os.path.join(app.srcdir, '%s.rst' % docname), 'w')
                    f.write(module.__doc__)
                    f.close()
                    app.config.man_pages.append((docname, docname, doctitle,
                            [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 1))

def setup(app):
    app.connect('builder-inited', generate_subcommand_docs)
