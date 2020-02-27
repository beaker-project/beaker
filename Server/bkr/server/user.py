
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging

import cherrypy
from datetime import datetime
from flask import request, jsonify, redirect as flask_redirect
from sqlalchemy import not_
from sqlalchemy.exc import InvalidRequestError
from turbogears import config
from turbogears.database import session

from bkr.common.bexceptions import BX
from bkr.server import identity, dynamic_virt
from bkr.server.app import app
from bkr.server.bexceptions import NoChangeException
from bkr.server.flask_util import (
    request_wants_json, auth_required, admin_auth_required, read_json_request,
    convert_internal_errors, json_collection, Forbidden403, NotFound404,
    Conflict409, render_tg_template, UnsupportedMediaType415,
    MethodNotAllowed405, BadRequest400
)
from bkr.server.model import (
    User, Job, System, SystemAccessPolicyRule, GroupMembershipType, SystemStatus,
    ConfigItem, SSHPubKey, SystemPool
)
from bkr.server.util import absolute_url
from bkr.server.xmlrpccontroller import RPCRoot

log = logging.getLogger(__name__)


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
        * any systems and system pools owned by the account are transferred to
          the admin running this command, or some other user if specified using
          the *newowner* parameter
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
    for system in System.query.filter(System.user == user):
        reservation = system.open_reservation
        system.unreserve(reservation=reservation, service=method)
    # Return all loaned systems in use by this user
    for system in System.query.filter(System.loaned == user):
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
    for system in System.query.filter(System.owner == user):
        system.owner = newowner
        system.record_activity(user=identity.current.user, service=method,
                               action=u'Changed', field=u'Owner',
                               old=u'%s' % user, new=u'%s' % newowner)
    for pool in SystemPool.query.filter(SystemPool.owning_user == user):
        pool.change_owner(user=newowner, service=method)
    # Remove the user from all groups
    for group in user.groups:
        if not group.membership_type == GroupMembershipType.inverted:
            group.remove_member(user=user,
                                agent=identity.current.user, service=method)
    # Finally remove the user
    user.removed = datetime.utcnow()


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

    ``id``
        ID of the user.
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
        'id': User.id,
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
        'grid_collection_url': request.path,
        'grid_view_type': 'UsersView',
        'grid_add_label': 'Create',
        'grid_add_view_type': 'UserCreateModal' if identity.current.user.is_admin() else 'null',
    })


@app.route('/users/+typeahead')
def users_typeahead():
    if 'q' in request.args:
        ldap = (len(request.args['q']) >= 3)  # be nice to the LDAP server
        users = User.list_by_name(request.args['q'],
                                  find_anywhere=False, find_ldap_users=ldap)
    else:
        # not sure if this is wise, the response may be several hundred KB...
        users = User.query.filter(User.removed == None) \
            .values(User.user_name, User.display_name)
    data = [{'user_name': user_name, 'display_name': display_name,
             'tokens': [user_name]}
            for user_name, display_name in users]
    return jsonify(data=data)


def user_full_json(user):
    # Users have a minimal JSON representation which is embedded in many other
    # objects (system owner, system user, etc) but we need more info here on
    # the user page.
    attributes = user.to_json()
    attributes['job_count'] = Job.query.filter(not_(Job.is_finished())) \
        .filter(Job.owner == user).count()
    attributes['reservation_count'] = System.query.filter(System.user == user).count()
    attributes['loan_count'] = System.query \
        .filter(System.status != SystemStatus.removed) \
        .filter(System.loaned == user).count()
    attributes['owned_system_count'] = System.query \
        .filter(System.status != SystemStatus.removed) \
        .filter(System.owner == user).count()
    attributes['owned_pool_count'] = SystemPool.query \
        .filter(SystemPool.owning_user == user).count()
    # Intentionally not counting membership in inverted groups because everyone
    # is always in those
    attributes['group_membership_count'] = len(user.group_user_assocs)
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
        existing_user = User.by_user_name(new_user_name)
        if existing_user is not None:
            raise Conflict409('User %s already exists' % new_user_name)
        new_display_name = data.get('display_name', '').strip()
        new_email_address = data.get('email_address', '').strip()
        user = User(user_name=new_user_name,
                    display_name=new_display_name,
                    email_address=new_email_address)
        session.add(user)
        session.flush()  # to populate id
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


@app.route('/users/+self', methods=['GET'])
@auth_required
def get_self():
    """
    Returns details about the currently authenticated user account.
    """
    attributes = user_full_json(identity.current.user)
    if identity.current.proxied_by_user is not None:
        attributes['proxied_by_user'] = user_full_json(identity.current.proxied_by_user)
    return jsonify(attributes)


def _get_user(username):
    user = User.by_user_name(username)
    if user is None:
        raise NotFound404('User %s does not exist' % username)
    return user


# Note that usernames can contain /, for example Kerberos service principals,
# so we have to use a path match in our route patterns
@app.route('/users/<path:username>', methods=['GET'])
@auth_required
def get_user(username):
    """
    Returns details about a Beaker user account.

    :param username: The user's username.
    """
    user = _get_user(username)
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
    :jsonparam string root_password: Root password to be set on systems
      provisioned by Beaker.
    :jsonparam boolean use_old_job_page: True if the user has opted to use the
      old, deprecated pre-Beaker-23 job page.
    :jsonparam boolean notify_job_completion: True if the user receives
      notifications upon the completion of an owned job.
    :jsonparam boolean notify_broken_system: True if the user receives
      notifications upon a system being automatically marked broken.
    :jsonparam boolean notify_system_loan: True if the user receives
      notifications when their systems are loaned or loans are returned.
    :jsonparam boolean notify_group_membership: True if the user receives
      notifications of modifications to the groups the user belongs to.
    :jsonparam boolean notify_reservesys: True if the user receives
      notifications upon reservesys being ready.
    :jsonparam boolean disabled: Whether the user should be temporarily
      disabled. Disabled users cannot log in or submit jobs, and any running jobs
      are cancelled when their account is disabled.
    :jsonparam string removed: Pass the string 'now' to remove a user account.
      Pass null to un-remove a removed user account.
    """
    user = _get_user(username)
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
                if user.user_name != new_user_name:
                    if not user.can_rename(identity.current.user):
                        raise Forbidden403('Cannot rename user %s to %s'
                                           % (user, new_user_name))
                    if User.by_user_name(new_user_name) is not None:
                        raise Conflict409('User %s already exists' % new_user_name)
                    user.user_name = new_user_name
                    renamed = True
            if 'display_name' in data:
                user.display_name = data['display_name'].strip()
            if 'email_address' in data:
                user.email_address = data['email_address'].strip()
            if 'root_password' in data:
                new_root_password = data['root_password']
                if user.root_password != new_root_password:
                    user.root_password = new_root_password
            if 'use_old_job_page' in data:
                user.use_old_job_page = data['use_old_job_page']
            if 'notify_job_completion' in data:
                user.notify_job_completion = data['notify_job_completion']
            if 'notify_broken_system' in data:
                user.notify_broken_system = data['notify_broken_system']
            if 'notify_system_loan' in data:
                user.notify_system_loan = data['notify_system_loan']
            if 'notify_group_membership' in data:
                user.notify_group_membership = data['notify_group_membership']
            if 'notify_reservesys' in data:
                user.notify_reservesys = data['notify_reservesys']
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
    session.flush()
    response = jsonify(user_full_json(user))
    if renamed:
        response.headers.add('Location', absolute_url(user.href))
    return response


@app.route('/prefs/', methods=['GET'])
@auth_required
def prefs():
    user = identity.current.user
    attributes = user_full_json(user)
    # Show all future root passwords, and the previous five
    rootpw = ConfigItem.by_name('root_password')
    rootpw_values = rootpw.values().filter(rootpw.value_class.valid_from > datetime.utcnow()) \
                        .order_by(rootpw.value_class.valid_from.desc()).all() \
                    + rootpw.values().filter(rootpw.value_class.valid_from <= datetime.utcnow()) \
                          .order_by(rootpw.value_class.valid_from.desc())[:5]
    return render_tg_template('bkr.server.templates.prefs', {
        'user': user,
        'attributes': attributes,
        'default_root_password': rootpw.current_value(),
        'default_root_passwords': rootpw_values,
    })


@app.route('/users/<path:username>/ssh-public-keys/', methods=['POST'])
@auth_required
def add_ssh_public_key(username):
    """
    Adds a new SSH public key for the given user account.

    Accepts mimetype:`text/plain` request bodies containing the SSH public key
    in the conventional OpenSSH format: <keytype> <key> <ident>.

    :param username: The user's username.
    """
    user = _get_user(username)
    if not user.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit user %s' % user)
    if request.mimetype != 'text/plain':
        raise UnsupportedMediaType415('Request content type must be text/plain')
    with convert_internal_errors():
        keytext = request.data.strip()
        if '\n' in keytext:
            raise ValueError('SSH public keys may not contain newlines')
        elements = keytext.split(None, 2)
        if len(elements) != 3:
            raise ValueError('Invalid SSH public key')
        # 0 - key type; 1 - key; 2 - identity
        if elements[1] in [ssh_key.pubkey for ssh_key in user.sshpubkeys]:
            raise ValueError('Duplicate SSH public key')
        key = SSHPubKey(*elements)
        user.sshpubkeys.append(key)
        session.flush()  # to populate id
    return jsonify(key.__json__())


@app.route('/users/<path:username>/ssh-public-keys/<int:id>', methods=['DELETE'])
@auth_required
def delete_ssh_public_key(username, id):
    """
    Deletes a public SSH public key belonging to the given user account.

    :param username: The user's username.
    :param id: Database id of the SSH public key to be deleted.
    """
    user = _get_user(username)
    if not user.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit user %s' % user)
    matching_keys = [k for k in user.sshpubkeys if k.id == id]
    if not matching_keys:
        raise NotFound404('SSH public key id %s does not belong to user %s' % (id, user))
    key = matching_keys[0]
    session.delete(key)
    return '', 204


@app.route('/users/<path:username>/submission-delegates/', methods=['POST'])
@auth_required
def add_submission_delegate(username):
    """
    Adds a submission delegate for a user account. Submission delegates are
    other users who are allowed to submit jobs on behalf of this user.

    :param username: The user's username.
    :jsonparam string user_name: The submission delegate's username.
    """
    user = _get_user(username)
    if not user.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit user %s' % user)
    data = read_json_request(request)
    if 'user_name' not in data:
        raise BadRequest400('Missing "user_name" key to specify submission delegate')
    submission_delegate = User.by_user_name(data['user_name'])
    if submission_delegate is None:
        raise BadRequest400('Submission delegate %s does not exist' % data['user_name'])
    try:
        user.add_submission_delegate(submission_delegate, service=u'HTTP')
    except NoChangeException as e:
        raise Conflict409(unicode(e))
    return 'Added', 201


@app.route('/users/<path:username>/submission-delegates/', methods=['DELETE'])
@auth_required
def delete_submission_delegate(username):
    """
    Deletes a submission delegate for a user account.

    :param username: The user's username.
    :query string user_name: The submission delegate's username.
    """
    user = _get_user(username)
    if not user.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit user %s' % user)
    if 'user_name' not in request.args:
        raise MethodNotAllowed405
    submission_delegate = User.by_user_name(request.args['user_name'])
    if submission_delegate is None:
        raise NotFound404('Submission delegate %s does not exist' % request.args['user_name'])
    if not submission_delegate.is_delegate_for(user):
        raise Conflict409('User %s is not a submission delegate for %s'
                          % (submission_delegate, user))
    user.remove_submission_delegate(submission_delegate)
    return '', 204


@app.route('/users/+self/keystone-trust', methods=['PUT'])
@auth_required
def create_keystone_trust_for_self():
    """
    Creates a Keystone trust between the Beaker Keystone account and the
    currently authenticated user. This allows the Beaker Keystone account to
    represent the delegated authority of this user when creating virtual
    machines on OpenStack.

    :jsonparam string openstack_username: OpenStack username.
    :jsonparam string openstack_password: OpenStack password.
    :jsonparam string openstack_project_name: OpenStack project name.
    :jsonparam string openstack_project_domain_name: OpenStack project domain name.
        Optional parameter. [Default: "Default"].
    :jsonparam string openstack_user_domain_name: OpenStack user domain name.
        Optional parameter. [Default: "Default"].
    :status 200: Keystone trust created.
    :status 400: Invalid data was given/OpenStack is not enabled.
    :status 403: Cannot edit Keystone trust.
    """
    return _create_keystone_trust(identity.current.user)


@app.route('/users/<path:username>/keystone-trust', methods=['PUT'])
@auth_required
def create_keystone_trust(username):
    """
    Creates a Keystone trust between the Beaker Keystone account and this user.
    This allows the Beaker Keystone account to represent the delegated
    authority of this user when creating virtual machines on OpenStack.

    :param username: The user's username.
    :jsonparam string openstack_username: OpenStack username.
    :jsonparam string openstack_password: OpenStack password.
    :jsonparam string openstack_project_name: OpenStack project name.
    :jsonparam string openstack_project_domain_name: OpenStack project domain name.
        Optional parameter. [Default value: "Default"].
    :jsonparam string openstack_user_domain_name: OpenStack user domain name.
        Optional parameter. [Default value: "Default"].
    :status 200: Keystone trust created.
    :status 400: Invalid data was given/OpenStack is not enabled.
    :status 403: Cannot edit Keystone trust.

    """
    user = _get_user(username)
    return _create_keystone_trust(user)


def _create_keystone_trust(user):
    if not config.get('openstack.identity_api_url'):
        raise BadRequest400("OpenStack Integration is not enabled")
    if not user.can_edit_keystone_trust(identity.current.user):
        raise Forbidden403('Cannot edit Keystone trust of user %s' % user.user_name)

    data = read_json_request(request)
    if 'openstack_username' not in data:
        raise BadRequest400('No OpenStack username specified')
    if 'openstack_password' not in data:
        raise BadRequest400('No OpenStack password specified')
    if 'openstack_project_name' not in data:
        raise BadRequest400('No OpenStack project name specified')

    try:
        trust_id = dynamic_virt.create_keystone_trust(
            trustor_username=data['openstack_username'],
            trustor_password=data['openstack_password'],
            trustor_project_name=data['openstack_project_name'],
            trustor_user_domain_name=data.get('openstack_user_domain_name'),
            trustor_project_domain_name=data.get('openstack_project_domain_name'))
    except ValueError as err:
        raise BadRequest400(
            u'Could not authenticate with OpenStack using your credentials: %s' % unicode(err))
    user.openstack_trust_id = trust_id
    user.record_activity(user=identity.current.user, service=u'HTTP',
                         field=u'OpenStack Trust ID', action=u'Changed')
    return jsonify({'openstack_trust_id': trust_id})


@app.route('/users/<path:username>/keystone-trust', methods=['DELETE'])
@auth_required
def delete_keystone_trust(username):
    """
    Deletes the Keystone trust for a user account.

    :param username: The user's username.
    """
    user = _get_user(username)

    if not user.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit Keystone trust of user %s' % username)
    if not user.openstack_trust_id:
        raise BadRequest400('No Keystone trust created by user %s' % username)
    try:
        manager = dynamic_virt.VirtManager(user)
        manager.delete_keystone_trust()
    except ValueError as e:
        # If we can't create a VirtManager we presume that the trust has been
        # invalidated by different means.
        log.debug(e.message)
    except RuntimeError as e:
        # Sanity check failed. Because OpenStack is not configured.
        log.debug(e.message)
    old_trust_id = user.openstack_trust_id
    user.openstack_trust_id = None
    user.record_activity(user=identity.current.user, service=u'HTTP',
                         field=u'OpenStack Trust ID', action=u'Deleted',
                         old=old_trust_id)
    return '', 204


# for sphinx
users = Users
