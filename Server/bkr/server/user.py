
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import validators
from sqlalchemy import and_, or_, not_
from sqlalchemy.exc import InvalidRequestError
from formencode.api import Invalid
from bkr.common.bexceptions import BX
from flask import request, jsonify, redirect as flask_redirect
from bkr.server import identity
from bkr.server.flask_util import request_wants_json, auth_required, \
        admin_auth_required, read_json_request, convert_internal_errors, \
        json_collection, Forbidden403, NotFound404, Conflict409, \
        render_tg_template
from bkr.server.util import absolute_url
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.app import app

import cherrypy
from datetime import datetime

from bkr.server.model import User, Job, System, SystemActivity, TaskStatus, \
    SystemAccessPolicyRule, GroupMembershipType, SystemStatus


class Users(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @cherrypy.expose
    @identity.require(identity.in_group('admin'))
    def remove_account(self, username, newowner=None):
        """
        Removes a Beaker user account. When the account is removed:

        * it is removed from all groups and access policies
        * any running jobs owned by the account are cancelled
        * any systems reserved by or loaned to the account are returned
        * any systems owned by the account are transferred to the admin running this 
          command, or some other user if specified using the *newowner* parameter
        * the account is disabled for further login

        :param username: An existing username
        :param newowner: An optional username to assign all systems to.
        :type username: string
        """
        kwargs = {}

        try:
            user = User.by_user_name(username)
        except InvalidRequestError:
            raise BX(_('Invalid User %s ' % username))

        if newowner:
            owner = User.by_user_name(newowner)
            if owner is None:
                raise BX(_('Invalid user name for owner %s' % newowner))
            kwargs['newowner'] = owner

        if user.removed:
            raise BX(_('User already removed %s' % username))

        _remove(user=user, method='XMLRPC', **kwargs)

def _disable(user, method,
             msg='Your account has been temporarily disabled'):

    # cancel all queued and running jobs
    Job.cancel_jobs_by_user(user, msg)

def _remove(user, method, **kw):
    if user == identity.current.user:
        raise BX(_('You cannot remove yourself'))

    # cancel all running and queued jobs
    Job.cancel_jobs_by_user(user, 'User %s removed' % user.user_name)

    # Return all systems in use by this user
    for system in System.query.filter(System.user==user):
        reservation = system.open_reservation
        system.unreserve(reservation=reservation, service=method)
    # Return all loaned systems in use by this user
    for system in System.query.filter(System.loaned==user):
        system.record_activity(user=identity.current.user, service=method,
                action=u'Changed', field=u'Loaned To',
                old=u'%s' % system.loaned, new=None)
        system.loaned = None
    # Remove the user from all system access policies
    for rule in SystemAccessPolicyRule.query.filter_by(user=user):
        rule.record_deletion(service=method)
        session.delete(rule)
    # Change the owner to the caller
    newowner = kw.get('newowner', identity.current.user)
    for system in System.query.filter(System.owner==user):
        system.owner = newowner
        system.record_activity(user=identity.current.user, service=method,
                action=u'Changed', field=u'Owner',
                               old=u'%s' % user, new=u'%s' % newowner)
    # Remove the user from all groups
    for group in user.groups:
        if not group.membership_type == GroupMembershipType.inverted:
            group.remove_member(user=user,
                    agent=identity.current.user, service=method)
    # Finally remove the user
    user.removed=datetime.utcnow()

def _unremove(user):
    user.removed = None
    user.disabled = False

@app.route('/users/', methods=['GET'])
@auth_required
def get_users():
    """
    Returns a pageable JSON collection of all users accounts in Beaker.
    Refer to :ref:`pageable-json-collections`.

    The following fields are supported for filtering and sorting:

    ``user_name``
        The user's username.
    ``display_name``
        Full display name of the user.
    ``email_address``
        The user's email address.
    ``disabled``
        A boolean field which is true if the user has been temporarily disabled 
        by the Beaker administrator (preventing them from logging in or running 
        jobs).
    ``removed``
        Timestamp when the user account was deleted, or null for a user account 
        which has not been deleted.
    """
    query = User.query.order_by(User.user_name)
    json_result = json_collection(query, columns={
        'user_name': User.user_name,
        'display_name': User.display_name,
        'email_address': User.email_address,
        'disabled': User.disabled,
        'removed': User.removed,
    })
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Users',
        'grid_collection_type': 'Users',
        'grid_collection_data': json_result,
        'grid_collection_url': request.base_url,
        'grid_view_type': 'UsersView',
        'grid_add_label': 'Create',
        'grid_add_view_type': 'UserCreateModal' if identity.current.user.is_admin() else 'null',
    })

@app.route('/users/+typeahead')
def users_typeahead():
    if 'q' in request.args:
        ldap = (len(request.args['q']) >= 3) # be nice to the LDAP server
        users = User.list_by_name(request.args['q'],
                find_anywhere=False, find_ldap_users=ldap)
    else:
        # not sure if this is wise, the response may be several hundred KB...
        users = User.query.filter(User.removed == None)\
                .values(User.user_name, User.display_name)
    data = [{'user_name': user_name, 'display_name': display_name,
             'tokens': [user_name]}
            for user_name, display_name in users]
    return jsonify(data=data)

def user_full_json(user):
    # Users have a minimal JSON representation which is embedded in many other 
    # objects (system owner, system user, etc) but we need more info here on 
    # the user page.
    attributes = user.__json__()
    attributes['id'] = user.user_id
    attributes['job_count'] = Job.query.filter(not_(Job.is_finished()))\
            .filter(Job.owner == user).count()
    attributes['reservation_count'] = System.query.filter(System.user == user).count()
    attributes['loan_count'] = System.query\
            .filter(System.status != SystemStatus.removed)\
            .filter(System.loaned == user).count()
    attributes['owned_system_count'] = System.query\
            .filter(System.status != SystemStatus.removed)\
            .filter(System.owner == user).count()
    # Intentionally not counting membership in inverted groups because everyone 
    # is always in those
    attributes['group_membership_count'] = len(user.group_user_assocs)
    if identity.current.user:
        attributes['can_edit'] = user.can_edit(identity.current.user)
        attributes['can_change_password'] = \
            user.can_change_password(identity.current.user)
    else:
        attributes['can_edit'] = False
        attributes['can_change_password'] = False
    return attributes

@app.route('/users/', methods=['POST'])
@admin_auth_required
def create_user():
    """
    Creates a new user account in Beaker.
    """
    data = read_json_request(request)
    with convert_internal_errors():
        new_user_name = data.get('user_name', '').strip()
        if not new_user_name:
            raise ValueError('Username must not be empty')
        existing_user = User.by_user_name(new_user_name)
        if existing_user is not None:
            raise Conflict409('User %s already exists' % new_user_name)
        new_display_name = data.get('display_name', '').strip()
        if not new_display_name:
            raise ValueError('Display name must not be empty')
        email_validator = validators.Email(not_empty=True)
        try:
            new_email_address = email_validator.to_python(
                    data.get('email_address', '').strip())
        except Invalid as e:
            raise ValueError('Invalid email address: %s' % e)
        user = User(user_name=new_user_name,
                    display_name=new_display_name,
                    email_address=new_email_address)
        session.add(user)
        session.flush() # to populate id
    response = jsonify(user_full_json(user))
    response.status_code = 201
    response.headers.add('Location', absolute_url(user.href))
    return response

# For backwards compatibility with old TurboGears URLs.
@app.route('/users/edit', methods=['GET'])
def old_get_group():
    if 'id' in request.args:
        user = User.by_id(request.args['id'])
        if user is not None:
            return flask_redirect(absolute_url(user.href))
    raise NotFound404()

# Note that usernames can contain /, for example Kerberos service principals,
# so we have to use a path match in our route patterns
@app.route('/users/<path:username>', methods=['GET'])
@auth_required
def get_user(username):
    """
    Returns details about a Beaker user account.

    :param username: The user's username.
    """
    user = User.by_user_name(username)
    if user is None:
        raise NotFound404('User %s does not exist' % username)
    attributes = user_full_json(user)
    if request_wants_json():
        return jsonify(attributes)
    return render_tg_template('bkr.server.templates.user_edit_form', {
        'attributes': attributes,
        'url': user.href,
    })

@app.route('/users/<path:username>', methods=['PATCH'])
@auth_required
def update_user(username):
    """
    Updates a Beaker user account.

    :param username: The user's username.
    :jsonparam string user_name: New username. If the username is changed, the 
      response will include a Location header referring to the new URL for newly 
      renamed user resource.
    :jsonparam string display_name: New display name.
    :jsonparam string email_address: New email address.
    :jsonparam string password: New password. Only valid when Beaker is not 
      using external authentication for this account.
    :jsonparam boolean disabled: Whether the user should be temporarily 
      disabled. Disabled users cannot log in or submit jobs, and any running jobs 
      are cancelled when their account is disabled.
    :jsonparam string removed: Pass the string 'now' to remove a user account. 
      Pass null to un-remove a removed user account.
    """
    user = User.by_user_name(username)
    if user is None:
        raise NotFound404('User %s does not exist' % username)
    data = read_json_request(request)
    renamed = False
    if data.get('password') is not None:
        if not user.can_change_password(identity.current.user):
            raise Forbidden403('Cannot change password for user %s' % user)
        with convert_internal_errors():
            user.password = data.pop('password')
    if data:
        if not user.can_edit(identity.current.user):
            raise Forbidden403('Cannot edit user %s' % user)
        with convert_internal_errors():
            if 'user_name' in data:
                new_user_name = data['user_name'].strip()
                if not new_user_name:
                    raise ValueError('Username must not be empty')
                if user.user_name != new_user_name:
                    if not user.can_rename(identity.current.user):
                        raise Forbidden403('Cannot rename user %s to %s'
                                % (user, new_user_name))
                    if User.by_user_name(new_user_name) is not None:
                        raise Conflict409('User %s already exists' % new_user_name)
                    user.user_name = new_user_name
                    renamed = True
            if 'display_name' in data:
                new_display_name = data['display_name'].strip()
                if not new_display_name:
                    raise ValueError('Display name must not be empty')
                user.display_name = new_display_name
            if 'email_address' in data:
                validator = validators.Email(not_empty=True)
                try:
                    new_email_address = validator.to_python(data['email_address'].strip())
                except Invalid as e:
                    raise ValueError('Invalid email address: %s' % e)
                user.email_address = new_email_address
            if 'disabled' in data:
                user.disabled = data['disabled']
                if user.disabled:
                    _disable(user, method=u'HTTP')
            if 'removed' in data:
                if data['removed'] is None:
                    _unremove(user)
                elif data['removed'] == 'now':
                    _remove(user, method=u'HTTP')
                else:
                    raise ValueError('"removed" value must be "now" or null')
    response = jsonify(user_full_json(user))
    if renamed:
        response.headers.add('Location', absolute_url(user.href))
    return response

# for sphinx
users = Users
