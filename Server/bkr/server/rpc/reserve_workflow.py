
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import six
from turbogears import expose
from bkr.server import identity
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.model import (Distro, Arch, OSMajor, DistroTag, OSVersion,
        DistroTree, LabController, System)


class ReserveWorkflow:

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.reserve_workflow')
    def index(self, **kwargs):
        # CherryPy will give us distro_tree_id as a scalar if it only has one
        # value, but we want it to always be a list of int
        if not kwargs.get('distro_tree_id'):
            kwargs['distro_tree_id'] = []
        elif not isinstance(kwargs['distro_tree_id'], list):
            kwargs['distro_tree_id'] = [int(kwargs['distro_tree_id'])]
        else:
            kwargs['distro_tree_id'] = [int(x) for x in kwargs['distro_tree_id']]

        # If we got a distro_tree_id but no osmajor or distro, fill those in
        # with the right values so that the distro picker is populated properly
        if kwargs['distro_tree_id']:
            distro_tree = DistroTree.by_id(kwargs['distro_tree_id'][0])
            if not kwargs.get('distro'):
                kwargs['distro'] = distro_tree.distro.name
            if not kwargs.get('osmajor'):
                kwargs['osmajor'] = distro_tree.distro.osversion.osmajor.osmajor

        options = {}
        options['tag'] = [tag.tag for tag in DistroTag.used()]
        options['osmajor'] = [osmajor.osmajor for osmajor in
                OSMajor.ordered_by_osmajor(OSMajor.in_any_lab())]
        options['distro'] = self._get_distro_options(
                osmajor=kwargs.get('osmajor'), tag=kwargs.get('tag'))
        options['distro_tree_id'] = self._get_distro_tree_options(
                distro=kwargs.get('distro'))
        options['lab'] = [lc.fqdn for lc in
                LabController.query.filter(LabController.removed == None)]
        return dict(title=u'Reserve Workflow',
                selection=kwargs, options=options)

    @expose(allow_json=True)
    def get_distro_options(self, **kwargs):
        return {'options': self._get_distro_options(**kwargs)}

    def _get_distro_options(self, osmajor=None, tag=None, system=None, **kwargs):
        """
        Returns a list of distro names for the given osmajor and tag.
        """
        if not osmajor:
            return []
        distros = Distro.query.join(Distro.osversion, OSVersion.osmajor)\
                .filter(Distro.trees.any(DistroTree.lab_controller_assocs.any()))\
                .filter(OSMajor.osmajor == osmajor)\
                .order_by(Distro.date_created.desc())
        if tag:
            distros = distros.filter(Distro._tags.any(DistroTag.tag == tag))
        if system:
            try:
                system = System.by_fqdn(system, identity.current.user)
            except DatabaseLookupError:
                return []
            distros = system.distros(query=distros)
        return [name for name, in distros.values(Distro.name)]

    @expose(allow_json=True)
    def get_distro_tree_options(self, **kwargs):
        return {'options': self._get_distro_tree_options(**kwargs)}

    def _get_distro_tree_options(self, distro=None, system=None, **kwargs):
        """
        Returns a list of distro trees for the given distro.
        """
        if not distro:
            return []
        try:
            distro = Distro.by_name(distro)
        except DatabaseLookupError:
            return []
        trees = distro.dyn_trees.join(DistroTree.arch)\
                .filter(DistroTree.lab_controller_assocs.any())\
                .order_by(DistroTree.variant, Arch.arch)
        if system:
            try:
                system = System.by_fqdn(system, identity.current.user)
            except DatabaseLookupError:
                return []
            trees = system.distro_trees(query=trees)
        return [(tree.id, six.text_type(tree)) for tree in trees]
