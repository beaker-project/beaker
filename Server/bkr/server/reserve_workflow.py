
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from flask import request, jsonify
from sqlalchemy import and_, not_
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.app import app
from bkr.server.flask_util import BadRequest400, \
        convert_internal_errors, auth_required
from bkr.server.model import (Job, System, DistroTree,
        LabControllerDistroTree, LabController)
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.util import absolute_url

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
