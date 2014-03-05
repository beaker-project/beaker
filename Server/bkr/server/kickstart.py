
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import string
import re
import urlparse
import logging
import netaddr
import pipes # For pipes.quote, since it isn't available in shlex until 3.3
from sqlalchemy.orm.exc import NoResultFound
from turbogears import config, redirect
from turbogears.controllers import expose
import cherrypy
import jinja2.sandbox, jinja2.ext, jinja2.nodes
from bkr.server.model import session, RenderedKickstart
from bkr.server.util import absolute_url

log = logging.getLogger(__name__)

class SnippetExtension(jinja2.ext.Extension):

    """
    An extension which defines a block-level snippet statement::

        {% snippet 'rhts_post' %}

    equivalent to the expression::

        {{ snippet('rhts_post') }}

    See http://jinja.pocoo.org/docs/extensions/
    """

    tags = set(['snippet'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        snippet_name = parser.parse_expression()
        node = jinja2.nodes.Output([
            jinja2.nodes.Call(jinja2.nodes.Name('snippet', 'load'),
                    [snippet_name], [], None, None),
        ])
        node.set_lineno(lineno)
        return node

template_env = jinja2.sandbox.SandboxedEnvironment(
        cache_size=0, # https://bugzilla.redhat.com/show_bug.cgi?id=862235
        loader=jinja2.ChoiceLoader([
            jinja2.FileSystemLoader('/etc/beaker'),
            jinja2.PackageLoader('bkr.server', ''),
        ]),
        trim_blocks=True,
        extensions=[SnippetExtension])

def add_to_template_searchpath(dir):
    """Adds a new searchpath to our template_env var

    Finds the first FileSystemLoader of template_env and prepends dir to its
    searchpath
    """
    global template_env
    def _add_template(loaders, dir):
        for loader in loaders:
            # Let's squeeze a new FS path in
            if isinstance(loader, jinja2.FileSystemLoader):
                loader.searchpath.insert(0, dir)
                break
            elif getattr(loader, 'loaders', None):
                _add_template(loader.loaders, dir)
            else:
                continue
    _add_template([template_env.loader], dir)


class TemplateRenderingEnvironment(object):
    """
    This is a context manager which sets up a few things to make evaluating
    kickstart templates more secure.

    It's more of a sanity check, to prevent a mistake in a template
    or snippet from wreaking too much havoc. User-supplied templates are not
    allowed to access our model objects at all so they are not a concern.
    """
    def __enter__(self):
        # Can't do this without a CherryPy request :-(
        #self.saved_identity = identity.current
        #identity.set_current_identity(None)
        session.begin_nested()
    def __exit__(self, exc_type, exc_val, exc_tb):
        session.rollback()
        #identity.set_current_identity(self.saved_identity)

# Some custom Jinja template filters and tests,
# for added convenience when writing kickstart/snippet templates
# http://jinja.pocoo.org/docs/api/#custom-filters
# http://jinja.pocoo.org/docs/api/#custom-tests

def dictsplit(s, delim=',', pairsep=':'):
    """
    Returns a dict based on a sequence of key-value pairs encoded in a string,
    like this:

        type:mdraid,part:swap,size:256
    """
    return dict(pair.split(pairsep, 1) for pair in s.split(delim))

template_env.filters.update({
    'split': string.split,
    'dictsplit': dictsplit,
    'urljoin': urlparse.urljoin,
    'parsed_url': urlparse.urlparse,
    'shell_quoted': pipes.quote,
})

def is_arch(distro_tree, *arch_names):
    return distro_tree.arch.arch in arch_names

def is_osmajor(distro, *osmajor_names):
    return distro.osversion.osmajor.osmajor in osmajor_names

def is_osversion(distro, *osversion_names):
    return (u'%s.%s' % (distro.osversion.osmajor.osmajor, distro.osversion.osminor)
            in osversion_names)

template_env.tests.update({
    'arch': is_arch,
    'osmajor': is_osmajor,
    'osversion': is_osversion,
})

@jinja2.contextfunction
def var(context, name):
    return context.resolve(name)

template_env.globals.update({
    're': re,
    'netaddr': netaddr,
    'chr': chr,
    'ord': ord,
    'var': var,
    'absolute_url': absolute_url,
})

def kickstart_template(distro_tree):
    candidates = [
        'kickstarts/%s' % distro_tree.distro.osversion.osmajor.osmajor,
        'kickstarts/%s' % distro_tree.distro.osversion.osmajor.osmajor.rstrip(string.digits),
    ]
    for candidate in candidates:
        try:
            return template_env.get_template(candidate)
        except jinja2.TemplateNotFound:
            continue
    raise ValueError('No kickstart template found for %s, tried: %s'
            % (distro_tree.distro, ', '.join(candidates)))

def generate_kickstart(install_options, distro_tree, system, user,
        recipe=None, ks_appends=None, kickstart=None):
    if recipe:
        lab_controller = recipe.recipeset.lab_controller
    elif system:
        lab_controller = system.lab_controller
    else:
        raise ValueError("Must specify either a system or a recipe")

    # User-supplied templates don't get access to our model objects, in case
    # they do something foolish/naughty.
    recipe_whiteboard = job_whiteboard = ''
    if recipe:
        if recipe.whiteboard:
            recipe_whiteboard = recipe.whiteboard
        if recipe.recipeset.job.whiteboard:
            job_whiteboard = recipe.recipeset.job.whiteboard

    restricted_context = {
        'kernel_options_post': install_options.kernel_options_post_str,
        'recipe_whiteboard': recipe_whiteboard,
        'job_whiteboard': job_whiteboard,
    }

    restricted_context.update(install_options.ks_meta)
    # XXX find a better place to set this, perhaps from the kickstart templates
    rhel_osmajor = ['RedHatEnterpriseLinux6', 'RedHatEnterpriseLinux7']
    if distro_tree.distro.osversion.osmajor.osmajor in rhel_osmajor \
            or distro_tree.distro.osversion.osmajor.osmajor.startswith('Fedora'):
        restricted_context['end'] = '%end'

    # System templates and snippets have access to more useful stuff.
    context = dict(restricted_context)
    context.update({
        'distro_tree': distro_tree,
        'distro': distro_tree.distro,
        'system': system,
        'lab_controller': lab_controller,
        'user': user,
        'recipe': recipe,
        'config': config,
        'ks_appends': ks_appends or [],
    })

    snippet_locations = []
    if system:
        snippet_locations.append(
             'snippets/per_system/%%s/%s' % system.fqdn)
    snippet_locations.extend([
        'snippets/per_lab/%%s/%s' % lab_controller.fqdn,
        'snippets/per_osversion/%%s/%s' % distro_tree.distro.osversion,
        'snippets/per_osmajor/%%s/%s' % distro_tree.distro.osversion.osmajor,
        'snippets/%s',
    ])

    def snippet(name):
        template = None
        candidates = [location % name for location in snippet_locations]
        for candidate in candidates:
            try:
                template = template_env.get_template(candidate)
                break
            except jinja2.TemplateNotFound:
                continue
        if template:
            retval = template.render(context)
            if retval and not retval.endswith('\n'):
                retval += '\n'
            return retval
        else:
            return u'# no snippet data for %s\n' % name
    restricted_context['snippet'] = snippet
    context['snippet'] = snippet

    with TemplateRenderingEnvironment():
        if kickstart:
            template = template_env.from_string(
                    "{% snippet 'install_method' %}\n" + kickstart)
            result = template.render(restricted_context)
        else:
            template = kickstart_template(distro_tree)
            result = template.render(context)

    rendered_kickstart = RenderedKickstart(kickstart=result)
    session.add(rendered_kickstart)
    session.flush() # so that it has an id
    return rendered_kickstart

class KickstartController(object):

    """
    TurboGears controller for serving up generated kickstarts.
    """

    @expose(content_type='text/plain; charset=UTF-8')
    def default(self, id):
        try:
            kickstart = RenderedKickstart.by_id(id)
        except NoResultFound:
            raise cherrypy.NotFound(id)
        if kickstart.url:
            redirect(kickstart.url)
        return kickstart.kickstart.encode('utf8')
