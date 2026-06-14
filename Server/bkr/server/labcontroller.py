
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.database import session
from bkr.server import config
from bkr.server import identity
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime, timedelta

from flask import request, jsonify
from bkr.server.app import app
from bkr.server.flask_util import auth_required, read_json_request, \
    BadRequest400, Forbidden403, NotFound404, request_wants_json, \
    render_tg_template, convert_internal_errors, Conflict409
from bkr.server.util import absolute_url
from bkr.server.model import \
    LabController, User, Group, DistroTree, \
    LabControllerDistroTree, System, Watchdog

import logging

import six
from six.moves import urllib


log = logging.getLogger(__name__)


def find_labcontroller_or_raise404(fqdn):
    """Returns a lab controller object or raises a NotFound404 error if the lab
    controller does not exist in the database."""
    try:
        labcontroller = LabController.by_name(fqdn)
    except NoResultFound:
        raise NotFound404('Lab controller %s does not exist' % fqdn)
    return labcontroller

def restore_labcontroller(labcontroller):
    """
    Restores a disabled and removed lab controller.
    """
    labcontroller.removed = None
    labcontroller.disabled = False

    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Disabled', action=u'Changed', old=six.text_type(True), new=six.text_type(False))
    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Removed', action=u'Changed', old=six.text_type(True), new=six.text_type(False))

def remove_labcontroller(labcontroller):
    """
    Disables and marks a lab controller as removed.
    """
    labcontroller.removed = datetime.utcnow()
    systems = System.query.filter(System.lab_controller == labcontroller)

    # Record systems set to status=broken. Trigger any event listener listening
    # for status changes.
    for sys in systems:
        sys.mark_broken('Lab controller de-associated')
        sys.abort_queued_commands("System disassociated from lab controller")
    # de-associate systems
    System.record_bulk_activity(systems, user=identity.current.user,
                                service=u'HTTP', action=u'Changed', field=u'Lab Controller',
                                old=labcontroller.fqdn, new=None)
    systems.update({'lab_controller_id': None},
                   synchronize_session=False)

    # cancel running recipes
    watchdogs = Watchdog.by_status(labcontroller=labcontroller,
                                   status='active')
    for w in watchdogs:
        w.recipe.recipeset.job.cancel(msg='Lab controller %s has been deleted' % labcontroller.fqdn)

    # remove distro trees
    distro_tree_assocs = LabControllerDistroTree.query\
        .filter(LabControllerDistroTree.lab_controller == labcontroller)
    DistroTree.record_bulk_activity(
        distro_tree_assocs.join(LabControllerDistroTree.distro_tree),
        user=identity.current.user, service=u'HTTP',
        action=u'Removed', field=u'lab_controller_assocs',
        old=labcontroller.fqdn, new=None)
    distro_tree_assocs.delete(synchronize_session=False)
    labcontroller.disabled = True
    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Disabled', action=u'Changed', old=six.text_type(False), new=six.text_type(True))
    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Removed', action=u'Changed', old=six.text_type(False), new=six.text_type(True))

def find_user_or_create(user_name):
    user = User.by_user_name(user_name)
    if user is None:
        user = User(user_name=user_name)
        user.user_name = user_name
        session.add(user)
    return user

def update_user(user, display_name=None, email_address=None, password=''):
    if user.lab_controller:
        raise BadRequest400(
            'User %s is already associated with lab controller %s' % (
                user, user.lab_controller))
    user.display_name = display_name
    user.email_address = email_address
    if password:
        user.password = password

    group = Group.by_name(u'lab_controller')
    if group not in user.groups:
        group.add_member(user, agent=identity.current.user)
    return user

@app.route('/labcontrollers/<fqdn>', methods=['PATCH'])
@auth_required
def update_labcontroller(fqdn):
    """
    Updates attributes of the lab controller identified by it's FQDN. The
    request body must be a json object or only the FQDN if
    that is the only value to be updated.

    :param string fqdn: Lab controller's new fully-qualified domain name.
    :jsonparam string user_name: User name associated with the lab controller.
    :jsonparam string email_address: Email of the user account associated with the lab controller.
    :jsonparam string password: Optional password for the user account used to login.
    :jsonparam string removed: If True, detaches all systems, cancels all
        running recipes and removes associated distro trees. If False, restores
        the lab controller.
    :jsonparam bool disabled: Whether the lab controller should be disabled. New
        recipes are not scheduled on a lab controller while it is disabled.
    :status 200: LabController updated.
    :status 400: Invalid data was given.
    """
    labcontroller = find_labcontroller_or_raise404(fqdn)
    if not labcontroller.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit lab controller')
    data = read_json_request(request)
    with convert_internal_errors():
        # should the lab controller be removed?
        if data.get('removed', False) and not labcontroller.removed:
            remove_labcontroller(labcontroller)

        # should the controller be restored?
        if data.get('removed') is False and labcontroller.removed:
            restore_labcontroller(labcontroller)
        fqdn_changed = False
        new_fqdn = data.get('fqdn', fqdn)
        if labcontroller.fqdn != new_fqdn:
            lc = None
            try:
                lc = LabController.by_name(new_fqdn)
            except NoResultFound:
                pass
            if lc is not None:
                raise BadRequest400('FQDN %s already in use' % new_fqdn)

            labcontroller.record_activity(
                user=identity.current.user, service=u'HTTP',
                field=u'fqdn', action=u'Changed', old=labcontroller.fqdn, new=new_fqdn)
            labcontroller.fqdn = new_fqdn
            labcontroller.user.display_name = new_fqdn
            fqdn_changed = True
        if 'user_name' in data:
            user = find_user_or_create(data['user_name'])
            if labcontroller.user != user:
                user = update_user(
                    user,
                    display_name=new_fqdn,
                    email_address=data.get('email_address', user.email_address),
                    password=data.get('password', user.password)
                )
                labcontroller.record_activity(
                    user=identity.current.user, service=u'HTTP',
                    field=u'User', action=u'Changed',
                    old=labcontroller.user.user_name, new=user.user_name)
                labcontroller.user = user
        if 'email_address' in data:
            new_email_address = data.get('email_address')
            if labcontroller.user.email_address != new_email_address:
                labcontroller.user.email_address = new_email_address
        if data.get('password') is not None:
            labcontroller.user.password = data.get('password')
        if labcontroller.disabled != data.get('disabled', labcontroller.disabled):
            labcontroller.record_activity(
                user=identity.current.user, service=u'HTTP',
                field=u'disabled', action=u'Changed',
                old=six.text_type(labcontroller.disabled), new=data['disabled'])
            labcontroller.disabled = data['disabled']

    response = jsonify(labcontroller.__json__())
    if fqdn_changed:
        response.headers.add('Location', absolute_url(labcontroller.href))
    return response

@app.route('/labcontrollers/<fqdn>', methods=['GET'])
def get_labcontroller(fqdn):
    """Returns detailed information about a lab controller in JSON.

    :param fqdn: The lab controllers FQDN
    """
    labcontroller = find_labcontroller_or_raise404(fqdn)
    return jsonify(labcontroller.__json__())

@app.route('/labcontrollers/', methods=['GET'])
def get_labcontrollers():
    """Returns a JSON collection of all labcontrollers defined in Beaker."""
    labcontrollers = LabController.query.order_by(LabController.fqdn).all()
    if request_wants_json():
        return jsonify(entries=labcontrollers)
    can_edit = identity.current.user is not None and identity.current.user.is_admin()
    return render_tg_template('bkr.server.templates.labcontrollers', {
        'title': 'Lab Controllers',
        'labcontrollers': labcontrollers,
        'labcontrollers_url': absolute_url('/labcontrollers/'),
        'can_edit': can_edit,
    })

@app.route('/labcontrollers/', methods=['POST'])
@auth_required
def create_labcontroller():
    """
    Creates a new lab controller. The request must be :mimetype:`application/json`.

    :jsonparam string fqdn: Lab controller's new fully-qualified domain name.
    :jsonparam string user_name: User name associated with the lab controller.
    :jsonparam string email_address: Email of the user account associated with the lab controller.
    :jsonparam string password: Optional password for the user account used to login.
    :status 201: The lab controller was successfully created.
    :status 400: Invalid data was given.
    """
    data = read_json_request(request)
    return _create_labcontroller_helper(data)

def _create_labcontroller_helper(data):
    with convert_internal_errors():
        if LabController.query.filter_by(fqdn=data['fqdn']).count():
            raise Conflict409('Lab Controller %s already exists' % data['fqdn'])

        user = find_user_or_create(data['user_name'])
        user = update_user(
            user=user,
            display_name=data['fqdn'],
            email_address=data.get('email_address', user.email_address),
            password=data.get('password', user.password)
        )
        labcontroller = LabController(fqdn=data['fqdn'], disabled=False)
        labcontroller.record_activity(
            user=identity.current.user, service=u'HTTP',
            action=u'Changed', field=u'FQDN', old=u'', new=data['fqdn'])

        labcontroller.user = user
        labcontroller.record_activity(
            user=identity.current.user, service=u'HTTP',
            action=u'Changed', field=u'User', old=u'', new=user.user_name)

        # For backwards compatibility
        labcontroller.record_activity(
            user=identity.current.user, service=u'HTTP',
            action=u'Changed', field=u'Disabled', old=u'', new=six.text_type(labcontroller.disabled))

        session.add(labcontroller)
        # flush it so we return an id, otherwise we'll end up back in here from
        # the edit form
        session.flush()

    response = jsonify(labcontroller.__json__())
    response.status_code = 201
    return response

# backwards compatibility
# Remove me once https://bugzilla.redhat.com/show_bug.cgi?id=1211119 is fixed
@app.route('/labcontrollers/save', methods=['POST'])
@auth_required
def save_labcontroller():
    data = request.form
    return _create_labcontroller_helper(dict(user_name=data['lusername'],
                                             email_address=data['email'],
                                             password=data['lpassword'],
                                             fqdn=data['fqdn']))
