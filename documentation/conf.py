
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo',
    'sphinxcontrib.httpdomain']
master_doc = 'index'
project = u'Beaker'
copyright = u'2013, Red Hat, Inc'

try:
    import bkr.common
    release = bkr.common.__version__
    version = '.'.join(release.split('.')[:2])
except ImportError:
    release = 'dev'
    version = 'dev'

import warnings

html_title = 'Beaker %s' % version
html_short_title = 'Beaker'
html_use_index = False
html_domain_indices = False

# subcommands are automatically generated, see extension below
man_pages = [
    ('man/bkr', 'bkr', 'Beaker client',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 1),
    ('man/bkr-workflow-xslt', 'bkr-workflow-xslt', 'XSLT-based Beaker job generator',
        [u'David Sommerseth <davids@redhat.com>'], 1),
    ('man/beaker-wizard', 'beaker-wizard', 'Tool to ease the creation of a new Beaker task',
        [u'Petr Splichal <psplicha@redhat.com>'], 1),
    ('admin-guide/man/beaker-create-kickstart', 'beaker-create-kickstart', 'Generate Anaconda kickstarts',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 8),
    ('admin-guide/man/beaker-create-ipxe-image', 'beaker-create-ipxe-image',
        'Generate and upload iPXE boot image to Glance',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 8),
    ('admin-guide/man/beaker-repo-update', 'beaker-repo-update',
        'Update cached harness packages',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 8),
    ('admin-guide/man/beaker-usage-reminder', 'beaker-usage-reminder',
        'Send Beaker usage reminder',
        [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 8),
]
man_show_urls = True

latex_documents = [
  ('admin-guide/index', 'admin-guide.tex', u'Beaker Administration Guide',
   u'Red Hat, Inc.', 'manual'),
  ('user-guide/index', 'user-guide.tex', u'Beaker User Guide',
   u'Red Hat, Inc.', 'manual'),
]

intersphinx_mapping = {'python': ('http://docs.python.org/', None),
                       'beakerdev': ('http://beaker-project.org/dev', None),
                      }

# This config is also a Sphinx extension with some Beaker-specific customisations:

import os
import re
import docutils.core, docutils.nodes

def strip_decorator_args(app, what, name, obj, options, signature, return_annotation):
    """
    Sphinx handler for autodoc-process-signature event, to strip out the weird 
    arguments which appear on functions decorated by TurboGears.
    """
    if what in ('function', 'method'):
        assert signature.startswith('(')
        assert signature.endswith(')')
        args = [arg.strip() for arg in signature[1:-1].split(',')]
        fixed_args = [arg for arg in args if arg not in
                ('*_decorator__varargs', '**_decorator__kwargs')]
        fixed_signature = '(%s)' % ', '.join(fixed_args)
        return (fixed_signature, return_annotation)

def find_client_subcommands():
    """
    Finds Beaker client subcommand modules matching bkr.client.commands.cmd_* 
    and creates a Sphinx document for each one.
    """
    from bkr.client import BeakerCommand
    from bkr.client.main import BeakerCommandContainer
    import bkr.client.commands
    subcommands = []
    for module_name in dir(bkr.client.commands):
        if module_name.startswith('cmd_'):
            module = getattr(bkr.client.commands, module_name)
            if not module.__doc__:
                continue
            for item in module.__dict__.values():
                if isinstance(item, type) and issubclass(item, BeakerCommand) and item.enabled:
                    subcommands.append((module, item,))
    return subcommands

def _get_title_from_docstring(docstring):
    # There seems to be no good way to parse a Sphinx specific
    # rst string. docutils.core.publish_string cannot do it, and I 
    # don't know what can, so we will have to continue grabbing the first
    # line that looks like a title
    for line in docstring.splitlines():
        line.strip()
        # Skip empty lines and directives
        if not line:
            continue
        if line.startswith('..'):
            continue
        # First line we find should be the title
        title = line
        break
    return title


def generate_subcommand_list(app):
    from bkr.client.main import BeakerCommandContainer
    subcommand_list = []
    for module, cls in find_client_subcommands():
        cmd_name = BeakerCommandContainer.normalize_name(cls.__name__)
        man_entry_name = 'bkr-%s' % cmd_name
        subcommand_list_entry = [man_entry_name]
        docstring = module.__doc__
        title = _get_title_from_docstring(docstring)
        # Get the descriptive text from the title
        match = re.search('bkr %s: (.+)$' % cmd_name, title)
        if match:
            try:
                title_description = match.group(1)
                subcommand_list_entry.append(title_description)
            except IndexError:
                pass
        # Ideally we should have the man entry name, and the description
        if len(subcommand_list_entry) < 2:
            warnings.filterwarnings('always',
                'Cannot find command description for %s, not adding it to bkr.rst' % module)
        subcommand_list.append(subcommand_list_entry)
    # Write bkr.rst subcommands
    subcommands_path = os.path.join(app.srcdir, 'man', 'subcommands.rst')
    with open(subcommands_path, 'w') as command_file:
        command_file.write(':orphan:\n\n')
        command_file.write('.. This file is autogenerated with commands found'
            ' in bkr.client.commands\n\n')
        command_file.write('Subcommands\n***********\n\n')
        # Sort by command name
        subcommand_list = sorted(subcommand_list,
            key=lambda subcommand_list_entry: subcommand_list_entry[0])
        for subcommand_list_entry in subcommand_list:
            man_text = subcommand_list_entry[0]
            desc = ''
            if len(subcommand_list_entry) == 2:
                desc = subcommand_list_entry[1]
            command_file.write('* :manpage:`%s(1)` -- %s\n' % (man_text, desc))

def generate_client_subcommand_docs(app):
    """
    Finds Beaker client subcommand modules matching bkr.client.commands.cmd_* 
    and creates a Sphinx document for each one.
    """
    for module, item in find_client_subcommands():
        generate_client_subcommand_doc(app, module, item)

def generate_client_subcommand_doc(app, module, cls):
    from bkr.client.main import BeakerCommandContainer
    docname = 'bkr-%s' % BeakerCommandContainer.normalize_name(cls.__name__)
    doc = module.__doc__
    doctitle = _get_title_from_docstring(doc)
    doc = '.. GENERATED FROM %s, DO NOT EDIT THIS FILE\n%s' % (module.__file__, doc)
    outpath = os.path.join(app.srcdir, 'man', '%s.rst' % docname)
    # only write it if the contents have changed, this helps conditional builds
    if not os.path.exists(outpath) or open(outpath, 'r').read() != doc:
        open(outpath, 'w').write(doc)
    description = doctitle.split(':', 1)[1].strip()
    app.config.man_pages.append(('man/%s' % docname, docname, description,
            [u'The Beaker team <beaker-devel@lists.fedorahosted.org>'], 1))

# A poor man's version of sphinxcontrib-issuetracker 
# <https://pypi.python.org/pypi/sphinxcontrib-issuetracker> which unfortunately 
# requires a newer python-requests than is available in Fedora.
# This code inspired by Doug Hellman's article 
# <http://doughellmann.com/2010/05/defining-custom-roles-in-sphinx.html>.
def beaker_bugzilla_issue_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    bz_url = 'https://bugzilla.redhat.com/show_bug.cgi?id=%s' % text
    text = "#" + text
    node = docutils.nodes.reference(rawtext, text, refuri=bz_url, **options)
    return [node], []

def setup(app):
    app.setup_extension('sphinx.ext.autodoc')
    app.connect('autodoc-process-signature', strip_decorator_args)
    app.connect('builder-inited', generate_client_subcommand_docs)
    app.connect('builder-inited', generate_subcommand_list)
    app.add_role('issue', beaker_bugzilla_issue_role)