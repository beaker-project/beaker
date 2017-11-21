
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['TurboGears']

from itertools import chain
import sys
import optparse
from turbogears.database import session
from sqlalchemy.orm.exc import NoResultFound
from bkr.common import __version__
from bkr.server.model import DistroTree, System, User, Recipe, \
        install_options_for_distro
from bkr.server.util import load_config_or_exit
from bkr.server.installopts import InstallOptions
from bkr.server.kickstart import generate_kickstart, template_env, add_to_template_searchpath
from bkr.server.bexceptions import DatabaseLookupError

__description__ = 'Creates an Anaconda kickstart file'

class FakeInstallation(object):
    def __init__(self, osmajor, osminor, name, variant, arch, tree_url):
        self.osmajor = osmajor
        self.osminor = osminor
        self.distro_name = name
        self.variant = variant
        self.arch = arch
        self.tree_url = tree_url

def main(*args):
    parser = optparse.OptionParser('usage: %prog [options]',
        description=__description__,
        version=__version__)
    parser.add_option('-u', '--user', metavar='USERNAME',
        help='The user we are creating a kickstart for', default='admin')
    parser.add_option('-r', '--recipe-id', metavar='ID',
        help='Recreate kickstart based on recipe ID')
    parser.add_option('-d', '--distro-tree-id', metavar='ID',
        help='Recreate kickstart based on distro ID')
    parser.add_option('-t', '--template-dir', metavar='DIR',
        help='Retrieve templates from DIR')
    parser.add_option('-f', '--system', metavar='FQDN',
        help='Generate kickstart for system identified by FQDN')
    parser.add_option('-m', '--ks-meta', metavar='OPTIONS', default='',
        help='Kickstart meta data')
    parser.add_option('-p', '--kernel-options-post', metavar='OPTIONS', default='',
        help='Kernel options post')
    options, args = parser.parse_args(*args)
    ks_meta = options.ks_meta.decode(sys.getfilesystemencoding())
    koptions_post = options.kernel_options_post.decode(sys.getfilesystemencoding())
    template_dir = options.template_dir
    if template_dir:
        add_to_template_searchpath(template_dir)

    if not options.recipe_id:
        if not options.distro_tree_id and not options.system:
            parser.error('Must specify either a recipe or a distro tree and system')
        elif not options.distro_tree_id:
            parser.error('Must specify a distro tree id when passing in a system')
        elif not options.system:
            parser.error('Must specify a system when not specifying a recipe')

    load_config_or_exit()
    with session.begin():
        user = User.by_user_name(options.user.decode(sys.getfilesystemencoding()))
        ks_appends = None
        recipe = None
        distro_tree = None
        system = None
        install_options = None

        if options.distro_tree_id:
            try:
                distro_tree = DistroTree.by_id(options.distro_tree_id)
            except NoResultFound:
                raise RuntimeError("Distro tree id '%s' does not exist" % options.distro_tree_id)
        if options.system:
            fqdn = options.system.decode(sys.getfilesystemencoding())
            try:
                system = System.by_fqdn(fqdn, user)
            except DatabaseLookupError:
                raise RuntimeError("System '%s' does not exist" % fqdn)

            if distro_tree and not options.recipe_id:
                install_options = system.manual_provision_install_options(distro_tree)\
                    .combined_with(InstallOptions.from_strings(ks_meta, None, koptions_post))

        if options.recipe_id:
            try:
                recipe = Recipe.by_id(options.recipe_id)
            except NoResultFound:
                raise RuntimeError("Recipe id '%s' does not exist" % options.recipe_id)
            if not recipe.resource and not options.system:
                raise RuntimeError('Recipe must have (or had) a resource'
                                   ' assigned to it')
            if not system:
                system = getattr(recipe.resource, 'system', None)
            if not distro_tree:
                distro_tree = recipe.distro_tree

            sources = []
            # if distro_tree is specified, distro_tree overrides recipe
            osmajor = distro_tree.distro.osversion.osmajor.osmajor if distro_tree else recipe.installation.osmajor
            osminor = distro_tree.distro.osversion.osminor if distro_tree else recipe.installation.osminor
            variant = distro_tree.variant if distro_tree else recipe.installation.variant
            arch = distro_tree.arch if distro_tree else recipe.installation.arch

            sources.append(install_options_for_distro(osmajor, osminor, variant, arch))
            if distro_tree:
                sources.append(distro_tree.install_options())
            sources.extend(system.install_options(arch, osmajor, osminor))
            sources.append(recipe.generated_install_options())
            sources.append(InstallOptions.from_strings(recipe.ks_meta,
                                                       recipe.kernel_options, recipe.kernel_options_post))
            sources.append(InstallOptions.from_strings(ks_meta, None, koptions_post))

            install_options = InstallOptions.reduce(sources)

            ks_appends = [ks_append.ks_append for ks_append \
                          in recipe.ks_appends]
            user = recipe.recipeset.job.owner

        # Render the kickstart
        installation = recipe.installation if recipe and recipe.installation else \
            FakeInstallation(distro_tree.distro.osversion.osmajor.osmajor,
                             distro_tree.distro.osversion.osminor,
                             distro_tree.distro.name,
                             distro_tree.variant,
                             distro_tree.arch,
                             distro_tree.url_in_lab(lab_controller=system.lab_controller))
        rendered_kickstart = generate_kickstart(install_options=install_options,
                                                distro_tree=distro_tree,
                                                installation=installation,
                                                system=system,
                                                user=user,
                                                recipe=recipe,
                                                ks_appends=ks_appends)
        kickstart = rendered_kickstart.kickstart

    print kickstart


if __name__ in ('main', '__main__'):
    sys.exit(main())
