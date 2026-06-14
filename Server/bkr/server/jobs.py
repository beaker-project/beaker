
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import logging

import lxml.etree
from formencode.api import Invalid
from formencode import validators
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.junitxml import job_to_junit_xml
from bkr.server import identity
from bkr.server.app import app
from bkr.server.model import Job, RetentionTag, Product, System, TaskStatus
from bkr.server.flask_util import auth_required, convert_internal_errors, \
    BadRequest400, NotFound404, Forbidden403, Conflict409, request_wants_json, \
    read_json_request, render_tg_template, stringbool
from flask import request, jsonify, make_response
from bkr.server.bexceptions import DatabaseLookupError

import six


log = logging.getLogger(__name__)


def _get_job_by_id(id):
    """Get job by ID, reporting HTTP 404 if the job is not found"""
    try:
        return Job.by_id(id)
    except NoResultFound:
        raise NotFound404('Job not found')

@app.route('/jobs/<int:id>', methods=['GET'])
def get_job(id):
    """
    Provides detailed information about a job in JSON format.

    :param id: ID of the job.
    """
    job = _get_job_by_id(id)
    if request_wants_json():
        return jsonify(job.__json__())
    if identity.current.user and identity.current.user.use_old_job_page:
        return NotFound404('Fall back to old job page')
    return render_tg_template('bkr.server.templates.job', {
        'title': job.t_id, # N.B. JobHeaderView in JS updates the page title
        'job': job,
    })

@app.route('/jobs/<int:id>.xml', methods=['GET'])
def job_xml(id):
    """
    Returns the job in Beaker results XML format.

    :status 200: The job xml file was successfully generated.
    """
    job = _get_job_by_id(id)
    include_logs = request.args.get('include_logs', type=stringbool, default=True)
    xmlstr = lxml.etree.tostring(
            job.to_xml(clone=False, include_logs=include_logs),
            pretty_print=True, encoding='utf8')
    response = make_response(xmlstr)
    response.status_code = 200
    response.headers.add('Content-Type', 'text/xml; charset=utf-8')
    return response

@app.route('/jobs/<int:id>.junit.xml', methods=['GET'])
def job_junit_xml(id):
    """
    Returns the job in JUnit-compatible XML format.
    """
    job = _get_job_by_id(id)
    response = make_response(job_to_junit_xml(job))
    response.status_code = 200
    response.headers.add('Content-Type', 'text/xml; charset=utf-8')
    return response

@app.route('/jobs/<int:id>', methods=['PATCH'])
@auth_required
def update_job(id):
    """
    Updates metadata of an existing job including retention settings and comments.
    The request body must be a JSON object containing one or more of the following
    keys.

    :param id: Job's id.
    :jsonparam string retention_tag: Retention tag of the job.
    :jsonparam string product: Product of the job.
    :jsonparam string whiteboard: Whiteboard of the job.
    :status 200: Job was updated.
    :status 400: Invalid data was given.
    """
    job = _get_job_by_id(id)
    if not job.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit job %s' % job.id)
    data = read_json_request(request)
    def record_activity(field, old, new, action=u'Changed'):
        job.record_activity(user=identity.current.user, service=u'HTTP',
                action=action, field=field, old=old, new=new)
    with convert_internal_errors():
        if 'whiteboard' in data:
            new_whiteboard = data['whiteboard']
            if new_whiteboard != job.whiteboard:
                record_activity(u'Whiteboard', job.whiteboard, new_whiteboard)
                job.whiteboard = new_whiteboard
        if 'retention_tag' in data:
            retention_tag = RetentionTag.by_name(data['retention_tag'])
            if retention_tag.requires_product() and not data.get('product') and not job.product:
                raise BadRequest400('Cannot change retention tag as it requires a product')
            if not retention_tag.requires_product() and (data.get('product') or
                    'product' not in data and job.product):
                raise BadRequest400('Cannot change retention tag as it does not support a product')
            if retention_tag != job.retention_tag:
                record_activity(u'Retention Tag', job.retention_tag, retention_tag)
                job.retention_tag = retention_tag
        if 'product' in data:
            if data['product'] is None:
                product = None
                if job.retention_tag.requires_product():
                    raise BadRequest400('Cannot change product as the current '
                            'retention tag requires a product')
            else:
                product = Product.by_name(data['product'])
                if not job.retention_tag.requires_product():
                    raise BadRequest400('Cannot change product as the current '
                            'retention tag does not support a product')
            if product != job.product:
                record_activity(u'Product', job.product, product)
                job.product = product
        if 'cc' in data:
            if isinstance(data['cc'], six.string_types):
                # Supposed to be a list, fix it up for them.
                data['cc'] = [data['cc']]
            email_validator = validators.Email(not_empty=True)
            for addr in data['cc']:
                try:
                    email_validator.to_python(addr)
                except Invalid as e:
                    raise BadRequest400('Invalid email address %r in cc: %s'
                            % (addr, str(e)))
            new_addrs = set(data['cc'])
            existing_addrs = set(job.cc)
            for addr in new_addrs.difference(existing_addrs):
                record_activity(u'Cc', None, addr, action=u'Added')
            for addr in existing_addrs.difference(new_addrs):
                record_activity(u'Cc', addr, None, action=u'Removed')
            job.cc[:] = list(new_addrs)
    return jsonify(job.__json__())

@app.route('/jobs/<int:id>', methods=['DELETE'])
@auth_required
def delete_job(id):
    """
    Delete a job.

    :param id: Job's id
    """
    job = _get_job_by_id(id)
    if not job.can_delete(identity.current.user):
        raise Forbidden403('Cannot delete job')
    if not job.is_finished():
        raise BadRequest400('Cannot delete running job')
    if job.is_deleted:
        raise Conflict409('Job has already been deleted')
    job.deleted = datetime.datetime.utcnow()
    return '', 204

@app.route('/jobs/<int:id>/activity/', methods=['GET'])
def get_job_activity(id):
    """
    Returns a JSON array of the historical activity records for a job.
    """
    # Not a "pageable JSON collection" like other activity APIs, because there 
    # is typically zero or a very small number of activity entries for any 
    # given job.
    # Also note this returns both JobActivity as well as RecipeSetActivity for 
    # the recipe sets in the job.
    job = _get_job_by_id(id)
    return jsonify({'entries': job.all_activity})

@app.route('/jobs/<int:id>/status', methods=['POST'])
@auth_required
def update_job_status(id):
    """
    Updates the status of a job. The request must be :mimetype:`application/json`.

    Currently the only allowed value for status is 'Cancelled', which has the 
    effect of cancelling all recipes in the job that have not finished yet.

    :param id: Job's id
    :jsonparam string status: The new status. Must be 'Cancelled'.
    :jsonparam string msg: A message describing the reason for updating the status.
    """
    job = _get_job_by_id(id)
    if not job.can_cancel(identity.current.user):
        raise Forbidden403('Cannot update job status')
    data = read_json_request(request)
    if 'status' not in data:
        raise BadRequest400('Missing status')
    status = TaskStatus.from_string(data['status'])
    msg = data.get('msg', None) or None
    if status != TaskStatus.cancelled:
        raise BadRequest400('Status must be "Cancelled"')
    with convert_internal_errors():
        job.record_activity(user=identity.current.user, service=u'HTTP',
                field=u'Status', action=u'Cancelled')
        job.cancel(msg=msg)
    return '', 204

@app.route('/jobs/+inventory', methods=['POST'])
@auth_required
def submit_inventory_job():
    """
    Submit a inventory job with the most suitable distro selected automatically.

    Returns a dictionary consisting of the job_id, recipe_id, status (recipe status) 
    and the job XML. If ``dryrun`` is set to ``True`` in the request, the first three 
    are set to ``None``.

    :jsonparam string fqdn: Fully-qualified domain name for the system.
    :jsonparam bool dryrun: If True, do not submit the job
    """
    if 'fqdn' not in request.json:
        raise BadRequest400('Missing the fqdn parameter')
    fqdn = request.json['fqdn']
    if 'dryrun' in request.json:
        dryrun = request.json['dryrun']
    else:
        dryrun = False
    try:
        system = System.by_fqdn(fqdn, identity.current.user)
    except DatabaseLookupError:
        raise BadRequest400('System not found: %s' % fqdn)
    if not dryrun and system.find_current_hardware_scan_recipe():
        raise Conflict409('Hardware scanning already in progress')
    distro = system.distro_tree_for_inventory()
    if not distro:
        raise BadRequest400('Could not find a compatible distro for hardware scanning available to this system')
    job_details = {}
    job_details['system'] = system
    job_details['whiteboard'] = 'Update Inventory for %s' % fqdn
    with convert_internal_errors():
        job_xml = Job.inventory_system_job(distro, dryrun=dryrun, **job_details)
    r = {}
    if not dryrun:
        r = system.find_current_hardware_scan_recipe().__json__()
    else:
        r = {'recipe_id': None,
             'status': None,
             'job_id': None,
        }
    r['job_xml'] = job_xml
    r = jsonify(r)
    return r
