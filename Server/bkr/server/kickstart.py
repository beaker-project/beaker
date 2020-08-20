# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import pipes  # For pipes.quote, since it isn't available in shlex until 3.3
import re
import string
import urlparse

import jinja2.ext
import jinja2.nodes
import jinja2.sandbox
import netaddr
from flask import redirect, abort, Response
from sqlalchemy.exc import DataError
from sqlalchemy.orm.exc import NoResultFound

from bkr.server.app import app
from bkr.server.model import session, RenderedKickstart
from bkr.server.model.distrolibrary import split_osmajor_name_version
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
    cache_size=0,  # https://bugzilla.redhat.com/show_bug.cgi?id=862235
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
        # self.saved_identity = identity.current
        # identity.set_current_identity(None)
        session.begin_nested()

    def __exit__(self, exc_type, exc_val, exc_tb):
        session.rollback()
        # identity.set_current_identity(self.saved_identity)


# For user-supplied templates we only expose these "fake" objects which wrap
# real model objects, providing only safe documented attributes. Otherwise
# users could invoke arbitrary methods on the model objects which we don't
# want. Server templates (controlled by the admin) on the other hand have
# access to the real model objects because it is more powerful.
class RestrictedOSMajor(object):
    def __init__(self, osmajor, name=None, number=None):
        self.osmajor = unicode(osmajor)
        name, number = split_osmajor_name_version(osmajor)
        self.name = unicode(name)
        self.number = unicode(number)


class RestrictedOSVersion(object):
    def __init__(self, osmajor, osminor):
        self.osmajor = RestrictedOSMajor(osmajor)
        if osminor is None:
            self.osminor = None
        else:
            self.osminor = unicode(osminor)


class RestrictedDistro(object):
    def __init__(self, osmajor, osminor, name):
        self.osversion = RestrictedOSVersion(osmajor, osminor)
        self.name = unicode(name)


class RestrictedArch(object):
    def __init__(self, arch):
        self.arch = unicode(arch)


class RestrictedDistroTree(object):
    def __init__(self, osmajor, osminor, name, variant, arch, tree_url, distro_tree=None):
        self.distro = RestrictedDistro(osmajor, osminor, name)
        if variant is None:
            self.variant = None
        else:
            self.variant = unicode(variant)
        self.arch = RestrictedArch(arch)
        self.distro_tree = distro_tree
        self.tree_url = tree_url
        # Empty repo list to avoid breaking templates
        self.repos = []

    def url_in_lab(self, lab_controller, scheme=None, required=False):
        if self.distro_tree:
            return self.distro_tree.url_in_lab(lab_controller, scheme)
        else:
            return self.tree_url


class RestrictedLabController(object):
    def __init__(self, lab_controller):
        self.fqdn = unicode(lab_controller.fqdn)


class RestrictedRecipe(object):
    def __init__(self, recipe):
        self.id = recipe.id
        self.whiteboard = recipe.whiteboard
        self.role = recipe.role


# Some custom Jinja template filters and tests,
# for added convenience when writing kickstart/snippet templates
# http://jinja.pocoo.org/docs/api/#custom-filters
# http://jinja.pocoo.org/docs/api/#custom-tests

def dictsplit(s, delim=',', pairsep=':'):
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


def kickstart_template(osmajor):
    candidates = [
        'kickstarts/%s' % osmajor,
        'kickstarts/%s' % osmajor.rstrip(string.digits),
        'kickstarts/default',
    ]
    for candidate in candidates:
        try:
            return template_env.get_template(candidate)
        except jinja2.TemplateNotFound:
            continue
    raise ValueError('No kickstart template found for %s, tried: %s'
                     % (osmajor, ', '.join(candidates)))


def generate_kickstart(install_options,
                       distro_tree,
                       system, user,
                       recipe=None,
                       ks_appends=None,
                       kickstart=None,
                       installation=None,
                       no_template=None):
    if recipe:
        lab_controller = recipe.recipeset.lab_controller
    elif system:
        lab_controller = system.lab_controller
    else:
        raise ValueError("Must specify either a system or a recipe")

    recipe_whiteboard = job_whiteboard = ''
    if recipe:
        if recipe.whiteboard:
            recipe_whiteboard = recipe.whiteboard
        if recipe.recipeset.job.whiteboard:
            job_whiteboard = recipe.recipeset.job.whiteboard

    installation = installation if installation is not None else recipe.installation
    # User-supplied templates don't get access to our model objects, in case
    # they do something foolish/naughty.
    restricted_context = {
        'kernel_options_post': install_options.kernel_options_post_str,
        'recipe_whiteboard': recipe_whiteboard,
        'job_whiteboard': job_whiteboard,
        'distro_tree': RestrictedDistroTree(installation.osmajor, installation.osminor,
                                            installation.distro_name, installation.variant,
                                            installation.arch.arch, installation.tree_url,
                                            distro_tree),
        'distro': RestrictedDistro(installation.osmajor, installation.osminor,
                                   installation.distro_name),
        'lab_controller': RestrictedLabController(lab_controller),
        'recipe': RestrictedRecipe(recipe) if recipe else None,
        'ks_appends': ks_appends or [],
    }

    restricted_context.update(install_options.ks_meta)

    # System templates and snippets have access to more useful stuff.
    context = dict(restricted_context)
    context.update({
        'system': system,
        'lab_controller': lab_controller,
        'user': user,
        'recipe': recipe,
        'config': app.config,
    })
    if distro_tree:
        context.update({
            'distro_tree': distro_tree,
            'distro': distro_tree.distro,
        })
    else:
        # But user-defined distros only get access to our "Restricted" model objects
        context.update({
            'distro_tree': RestrictedDistroTree(installation.osmajor, installation.osminor,
                                                installation.distro_name, installation.variant,
                                                installation.arch.arch, installation.tree_url),
            'distro': RestrictedDistro(installation.osmajor, installation.osminor,
                                       installation.distro_name),
        })

    snippet_locations = []
    if system:
        snippet_locations.append('snippets/per_system/%%s/%s' % system.fqdn)
    snippet_locations.extend([
        'snippets/per_lab/%%s/%s' % lab_controller.fqdn,
        'snippets/per_osversion/%%s/%s.%s' % (installation.osmajor, installation.osminor),
        'snippets/per_osmajor/%%s/%s' % installation.osmajor,
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
            template_string = ("{% snippet 'install_method' %}\n" + kickstart
                               if not no_template else kickstart)
            template = template_env.from_string(template_string)
            result = template.render(restricted_context)
        else:
            template = kickstart_template(installation.osmajor)
            result = template.render(context)

    rendered_kickstart = RenderedKickstart(kickstart=result)
    session.add(rendered_kickstart)
    try:
        session.flush()  # so that it has an id
    except DataError:
        raise ValueError('Kickstart generation failed. Please report this issue.')
    return rendered_kickstart


@app.route('/kickstart/<id>', methods=['GET'])
def get_kickstart(id):
    """
    Flask endpoint for serving up generated kickstarts.
    """
    try:
        kickstart = RenderedKickstart.by_id(id)
    except NoResultFound:
        abort(404)
    return redirect(kickstart.url) if kickstart.url else Response(
        kickstart.kickstart.encode('utf8'),
        mimetype='text/plain')
