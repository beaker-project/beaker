
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, url
from flask import request
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.app import app
from bkr.server.flask_util import BadRequest400, \
        convert_internal_errors, auth_required
from bkr.server.model import (Distro, Job, System, Arch, OSMajor, DistroTag,
                              SystemType, OSVersion, DistroTree, LabController)

import logging
log = logging.getLogger(__name__)

MAX_DAYS_PROVISION = 7
DEFAULT_RESERVE_DAYS = 1

@app.route('/reserveworkflow/doit', methods=['POST'])
@auth_required
def doit():
    distro_trees = []
    for id in request.form.getlist('distro_tree_id'):
        try:
            distro_trees.append(DistroTree.by_id(id))
        except NoResultFound:
            raise BadRequest400('Distro tree %r does not exist' % id)
    job_details = {}
    job_details['pick'] = request.form.get('pick') or 'auto'
    if job_details['pick'] == 'fqdn':
        try:
            job_details['system'] = System.by_fqdn(request.form.get('system'),
                    identity.current.user)
        except NoResultFound:
            raise BadRequest400('System %s not found' % request.form.get('system'))
    elif job_details['pick'] == 'lab':
        try:
            job_details['lab'] = LabController.by_name(request.form.get('lab'))
        except NoResultFound:
            raise BadRequest400('Lab controller %s not found' % request.form.get('lab'))
    days = int(request.form.get('reserve_days') or DEFAULT_RESERVE_DAYS)
    days = min(days, MAX_DAYS_PROVISION)
    job_details['reservetime'] = days * 24 * 60 * 60
    job_details['whiteboard'] = request.form.get('whiteboard')
    job_details['ks_meta'] = request.form.get('ks_meta')
    job_details['koptions'] = request.form.get('koptions')
    job_details['koptions_post'] = request.form.get('koptions_post')
    with convert_internal_errors():
        job = Job.provision_system_job(distro_trees, **job_details)
    return 'Created %s' % job.t_id, 201, [('Location', url('/jobs/%s' % job.id))]

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
        return dict(title=_(u'Reserve Workflow'),
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
            except NoResultFound:
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
        distro = Distro.by_name(distro)
        if not distro:
            return []
        trees = distro.dyn_trees.join(DistroTree.arch)\
                .filter(DistroTree.lab_controller_assocs.any())\
                .order_by(DistroTree.variant, Arch.arch)
        if system:
            try:
                system = System.by_fqdn(system, identity.current.user)
            except NoResultFound:
                return []
            trees = system.distro_trees(query=trees)
        return [(tree.id, unicode(tree)) for tree in trees]
