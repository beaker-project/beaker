
"""
Sphinx extension for Beaker-specific customisations.
"""

import re

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

def setup(app):
    app.setup_extension('sphinx.ext.autodoc')
    app.connect('autodoc-process-signature', strip_decorator_args)
