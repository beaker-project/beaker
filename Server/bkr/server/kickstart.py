
import string
import re
import urlparse
import logging
import netaddr
from sqlalchemy.orm.exc import NoResultFound
from turbogears import identity, config
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
        lineno = parser.stream.next()
        snippet_name = parser.parse_expression()
        node = jinja2.nodes.Output([
            jinja2.nodes.Call(jinja2.nodes.Name('snippet', 'load'),
                    [snippet_name], [], None, None),
        ])
        node.set_lineno(lineno)
        return node

template_env = jinja2.sandbox.SandboxedEnvironment(
        loader=jinja2.ChoiceLoader([
            jinja2.FileSystemLoader('/etc/beaker'),
            jinja2.PackageLoader('bkr.server', ''),
        ]),
        trim_blocks=True,
        extensions=[SnippetExtension])

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

def snippet_template(name, distro_tree, system):
    candidates = [
        'snippets/per_system/%s/%s' % (name, system.fqdn),
        'snippets/per_lab/%s/%s' % (name, system.lab_controller.fqdn),
        'snippets/per_osversion/%s/%s' % (name, distro_tree.distro.osversion),
        'snippets/per_osmajor/%s/%s' % (name, distro_tree.distro.osversion.osmajor),
        'snippets/%s' % name,
    ]
    for candidate in candidates:
        try:
            return template_env.get_template(candidate)
        except jinja2.TemplateNotFound:
            continue

def generate_kickstart(install_options, distro_tree, system, user,
        recipe=None, ks_appends=None, kickstart=None):
    # User-supplied templates don't get access to our model objects, in case
    # they do something foolish/naughty.
    restricted_context = {
        'kernel_options_post': install_options.kernel_options_post_str,
    }
    restricted_context.update(install_options.ks_meta)
    # XXX find a better place to set this, perhaps from the kickstart templates
    if distro_tree.distro.osversion.osmajor.osmajor == 'RedHatEnterpriseLinux7' \
            or distro_tree.distro.osversion.osmajor.osmajor.startswith('Fedora'):
        restricted_context['end'] = '%end'

    # System templates and snippets have access to more useful stuff.
    context = dict(restricted_context)
    context.update({
        'distro_tree': distro_tree,
        'distro': distro_tree.distro,
        'system': system,
        'user': user,
        'recipe': recipe,
        'config': config,
        'ks_appends': ks_appends or [],
    })

    def snippet(name):
        template = snippet_template(name, distro_tree, system)
        if template:
            retval = template.render(context)
            if retval and not retval.endswith('\n'):
                retval += '\n'
            return retval
        else:
            return u'# Error: no snippet data for %s\n' % name
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
