
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose
from flask import request, jsonify
from sqlalchemy import and_, not_
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.app import app
from bkr.server.flask_util import BadRequest400, \
        convert_internal_errors, auth_required
from bkr.server.model import (Distro, Job, System, Arch, OSMajor, DistroTag,
        SystemType, OSVersion, DistroTree, LabControllerDistroTree,
        LabController, MachineRecipe)
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.util import absolute_url
from bkr.server.bexceptions import DatabaseLookupError

import logging
log = logging.getLogger(__name__)

MAX_HOURS_PROVISION = 99
MAX_SECONDS_PROVISION = MAX_HOURS_PROVISION * 60 * 60
DEFAULT_RESERVE_SECONDS = 24 * 60 * 60

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
    system_choice = 'any system'
    if job_details['pick'] == 'fqdn':
        try:
            job_details['system'] = System.by_fqdn(request.form.get('system'),
                    identity.current.user)
            system_choice = 'a specific system'
        except DatabaseLookupError:
            raise BadRequest400('System %s not found' % request.form.get('system'))
    elif job_details['pick'] == 'lab':
        try:
            job_details['lab'] = LabController.by_name(request.form.get('lab'))
            system_choice = 'any lab system'
        except NoResultFound:
            raise BadRequest400('Lab controller %s not found' % request.form.get('lab'))
    reservetime = int(request.form.get('reserve_duration') or DEFAULT_RESERVE_SECONDS)
    if reservetime > MAX_SECONDS_PROVISION:
        raise BadRequest400('Reservation time exceeds maximum time of %s hours' % MAX_HOURS_PROVISION)
    job_details['reservetime'] = reservetime
    job_details['whiteboard'] = request.form.get('whiteboard')
    if not job_details['whiteboard']:
        job_details['whiteboard'] = (
            "Reserve Workflow provision of distro %s on %s for %d seconds" %
            (request.form.get('distro'), system_choice,
            job_details['reservetime']))

    job_details['ks_meta'] = request.form.get('ks_meta')
    job_details['koptions'] = request.form.get('koptions')
    job_details['koptions_post'] = request.form.get('koptions_post')
    with convert_internal_errors():
        job = Job.provision_system_job(distro_trees, **job_details)
    return 'Created %s' % job.t_id, 201, [('Location', absolute_url('/jobs/%s' % job.id))]

@app.route('/reserveworkflow/unsupported-lab-controllers', methods=['GET'])
def get_unsupported_lab_controllers():
    """
    Returns a dict with a list of not supported lab controller for every distro tree provided.
    """
    distro_tree_ids = request.args.getlist('distro_tree_id')
    unsupported_lab_controllers = {}
    for distro_tree_id in distro_tree_ids:
        try:
            name = str(DistroTree.query.filter(DistroTree.id == distro_tree_id).one())
            unsupported_lab_controllers[name] = [lab_controller.fqdn for lab_controller in
                LabController.query.filter(and_(LabController.disabled == 0,
                not_(LabController._distro_trees.any(LabControllerDistroTree.distro_tree_id == distro_tree_id)))).all()]
        except DatabaseLookupError:
            pass

    return  jsonify({'options': unsupported_lab_controllers})

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
        return [(tree.id, unicode(tree)) for tree in trees]
