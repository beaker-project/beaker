# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, config
from turbogears.database import session
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from flask import jsonify, request, redirect as flask_redirect
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import BX
from bkr.server.app import app
from bkr.server import mail, identity

from bkr.server.model import (Group, GroupMembershipType, Permission, User,
                              UserGroup, Activity, GroupActivity,
                              SystemPool)
from bkr.server.util import absolute_url
from bkr.server.flask_util import auth_required, \
    convert_internal_errors, read_json_request, BadRequest400, \
    Forbidden403, MethodNotAllowed405, NotFound404, Conflict409, \
    request_wants_json, render_tg_template, admin_auth_required, \
    json_collection

import logging
log = logging.getLogger(__name__)

class GroupOwnerModificationForbidden(BX):

    def __init__(self, message):
        # XXX: Call base class __init__?
        self._message = message
        self.args = [message]

class Groups(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    def revoke_owner(self, group_id=None, id=None, **kw):

        if group_id is not None and id is not None:
            group = Group.by_id(group_id)
            user = User.by_id(id)
            service = 'WEBUI'
        else:
            group = Group.by_name(kw['group_name'])
            user = User.by_user_name(kw['member_name'])
            service = 'XMLRPC'

        if group.membership_type == GroupMembershipType.ldap:
            raise GroupOwnerModificationForbidden('An LDAP group does not have an owner')

        if not group.can_edit(identity.current.user):
            raise GroupOwnerModificationForbidden('You are not an owner of group %s' % group)

        if user not in group.users:
            raise GroupOwnerModificationForbidden('User is not a group member')

        if len(group.owners())==1 and not identity.current.user.is_admin():
            raise GroupOwnerModificationForbidden('Cannot remove the only owner')
        else:
            group.revoke_ownership(user=user, agent=identity.current.user, service=service)
            # hack to return the user removing this owner
            # so that if the user was logged in as a group
            # owner, he/she can be redirected appropriately
            return str(identity.current.user.user_id)

    #XML-RPC interface
    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def revoke_ownership(self, group, kw):
        """
        Revoke group ownership from an existing group member

        :param group: An existing group name
        :type group: string

        The *kw* argument must be an XML-RPC structure (dict)
        specifying the following keys:

            'member_name'
                 Group member's username to revoke ownership
        """

        return self.revoke_owner(group_name=group,
                                 member_name=kw['member_name'])

    def grant_owner(self, group_id=None, id=None, **kw):

        if group_id is not None and id is not None:
            group = Group.by_id(group_id)
            user = User.by_id(id)
            service = 'WEBUI'
        else:
            group = Group.by_name(kw['group_name'])
            user = User.by_user_name(kw['member_name'])
            service = 'XMLRPC'

        if group.membership_type == GroupMembershipType.ldap:
            raise GroupOwnerModificationForbidden('An LDAP group does not have an owner')

        if not group.can_edit(identity.current.user):
            raise GroupOwnerModificationForbidden('You are not an owner of the group %s' % group)

        if user not in group.users:
            raise GroupOwnerModificationForbidden('User is not a group member')
        else:
            group.grant_ownership(user=user, agent=identity.current.user, service=service)
            return ''

    #XML-RPC interface
    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def grant_ownership(self, group, kw):
        """
        Grant group ownership to an existing group member

        :param group: An existing group name
        :type group: string

        The *kw* argument must be an XML-RPC structure (dict)
        specifying the following keys:

            'member_name'
                 Group member's username to grant ownership
        """
        return self.grant_owner(group_name=group,
                           member_name=kw['member_name'])

    # XML-RPC method for creating a group
    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def create(self, kw):
        """
        Creates a new group.

        The *kw* argument must be an XML-RPC structure (dict)
        specifying the following keys:

            'group_name'
                 Group name (maximum 16 characters)
            'display_name'
                 Group display name
            'description'
                 Group description
            'ldap'
                 Populate users from LDAP (True/False)

        Returns a message whether the group was successfully created or
        raises an exception on failure.

        """
        display_name = kw.get('display_name')
        group_name = kw.get('group_name')
        description = kw.get('description')
        ldap = kw.get('ldap')
        password = kw.get('root_password')

        if ldap and not identity.current.user.is_admin():
            raise BX(_(u'Only admins can create LDAP groups'))
        if ldap and not config.get("identity.ldap.enabled", False):
            raise BX(_(u'LDAP is not enabled'))
        try:
            group = Group.by_name(group_name)
        except NoResultFound:
            group = Group()
            session.add(group)
            group.record_activity(user=identity.current.user, service=u'XMLRPC',
                    field=u'Group', action=u'Created')
            group.display_name = display_name
            group.group_name = group_name
            group.description = description
            group.root_password = password
            if ldap:
                group.membership_type = GroupMembershipType.ldap
                group.refresh_ldap_members()
            else:
                group.add_member(identity.current.user, is_owner=True,
                        service=u'XMLRPC', agent=identity.current.user)
            return 'Group created: %s.' % group_name
        else:
            raise BX(_(u'Group already exists: %s.' % group_name))

    # XML-RPC method for modifying a group
    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def modify(self, group_name, kw):
        """
        Modifies an existing group. You must be an owner of a group to modify any details.

        :param group_name: An existing group name
        :type group_name: string

        The *kw* argument must be an XML-RPC structure (dict)
        specifying the following keys:

            'group_name'
                 New group name (maximum 16 characters)
            'display_name'
                 New group display name
            'add_member'
                 Add user (username) to the group
            'remove_member'
                 Remove an existing user (username) from the group
            'root_password'
                 Change the root password of this group.

        Returns a message whether the group was successfully modified or
        raises an exception on failure.

        """
        # if not called from the bkr group-modify
        if not kw:
            raise BX(_('Please specify an attribute to modify.'))

        try:
            group = Group.by_name(group_name)
        except NoResultFound:
            raise BX(_(u'Group does not exist: %s.' % group_name))

        if group.membership_type == GroupMembershipType.ldap:
            if not identity.current.user.is_admin():
                raise BX(_(u'Only admins can modify LDAP groups'))
            if kw.get('add_member', None) or kw.get('remove_member', None):
                raise BX(_(u'Cannot edit membership of an LDAP group'))

        user = identity.current.user
        if not group.can_edit(user):
            raise BX(_('You are not an owner of group %s' % group_name))

        group_name = kw.get('group_name', None)
        if group_name:
            try:
                Group.by_name(group_name)
            except NoResultFound:
                pass
            else:
                if group_name != group.group_name:
                    raise BX(_(u'Failed to update group %s: Group name already exists: %s' %
                               (group.group_name, group_name)))

            group.set_name(user, u'XMLRPC', kw.get('group_name', None))

        display_name = kw.get('display_name', None)
        if display_name:
            group.set_display_name(user, u'XMLRPC', display_name)

        root_password = kw.get('root_password', None)
        if root_password:
            group.set_root_password(user, u'XMLRPC', root_password)

        if kw.get('add_member', None):
            username = kw.get('add_member')
            user = User.by_user_name(username)
            if user is None:
                raise BX(_(u'User does not exist %s' % username))
            if user.removed:
                raise BX(_(u'Cannot add deleted user %s to group' % user.user_name))

            if user not in group.users:
                group.add_member(user, service=u'XMLRPC',
                        agent=identity.current.user)
                mail.group_membership_notify(user, group,
                                                agent = identity.current.user,
                                                action='Added')
            else:
                raise BX(_(u'User %s is already in group %s' % (username, group.group_name)))

        if kw.get('remove_member', None):
            username = kw.get('remove_member')
            user = User.by_user_name(username)

            if user is None:
                raise BX(_(u'User does not exist %s' % username))

            if user not in group.users:
                raise BX(_(u'No user %s in group %s' % (username, group.group_name)))
            else:
                if not group.can_remove_member(identity.current.user, user.user_id):
                    raise BX(_(u'Cannot remove member'))

                groupUsers = group.users
                for usr in groupUsers:
                    if usr.user_id == user.user_id:
                        group.remove_member(user, service=u'XMLRPC',
                                agent=identity.current.user)
                        removed = user
                        mail.group_membership_notify(user, group,
                                                        agent=identity.current.user,
                                                        action='Removed')
                        break

        #dummy success return value
        return ['1']

    # XML-RPC method for listing a group's members
    @expose(format='json')
    def members(self, group_name):
        """
        List the members of an existing group.

        :param group_name: An existing group name
        :type group_name: string

        Returns a list of the members (a dictionary containing each
        member's username, email, and whether the member is an owner
        or not).

        """
        try:
            group = Group.by_name(group_name)
        except NoResultFound:
            raise BX(_(u'Group does not exist: %s.' % group_name))

        users=[]
        for u in group.users:
            user={}
            user['username']=u.user_name
            user['email'] = u.email_address
            if group.has_owner(u):
                user['owner'] = True
            else:
                user['owner'] = False
            users.append(user)

        return users

@app.route('/groups/', methods=['GET'])
def get_groups():
    """
    Returns a pageable JSON collection of Beaker groups.

    The following fields are supported for filtering and sorting:

    ``id``
        ID of the group.
    ``group_name``
        Symbolic name of the group.
    ``display_name``
        Human-friendly display name of the group.
    ``created``
        Timestamp at which the group was created.
    """
    query = Group.query.order_by(Group.group_name)
    # Eager load all group members as an optimisation to avoid N database roundtrips
    query = query.options(joinedload('user_group_assocs'),
            joinedload('user_group_assocs.user'))
    json_result = json_collection(query, columns={
        'id': Group.id,
        'group_name': Group.group_name,
        'display_name': Group.display_name,
        'created': Group.created,
        'member.user_name': (Group.dyn_users, User.user_name),
        'member.display_name': (Group.dyn_users, User.display_name),
        'member.email_address': (Group.dyn_users, User.email_address),
        'owner.user_name': (Group.dyn_owners, User.user_name),
        'owner.display_name': (Group.dyn_owners, User.display_name),
        'owner.email_address': (Group.dyn_owners, User.email_address),
    })
    # Need to call .to_json() on the groups because the default __json__ 
    # representation is the minimal cut-down one, we want the complete 
    # representation here (including members and owners etc).
    json_result['entries'] = [g.to_json() for g in json_result['entries']]
    if request_wants_json():
        return jsonify(json_result)
    if identity.current.user:
        grid_add_view_type = 'GroupCreateModal',
        grid_add_view_options = {
            'can_create_ldap': Group.can_create_ldap(identity.current.user),
        }
    else:
        grid_add_view_type = 'null'
        grid_add_view_options = {}
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Groups',
        'grid_collection_type': 'Groups',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'GroupsView',
        'grid_add_label': 'Create',
        'grid_add_view_type': grid_add_view_type,
        'grid_add_view_options': grid_add_view_options,
    })

@app.route('/groups/mine', methods=['GET'])
@auth_required
def groups_mine():
    """
    Redirect for compatibility.
    """
    return flask_redirect(absolute_url('/groups/',
            q='member.user_name:%s' % identity.current.user.user_name))

@app.route('/groups/', methods=['POST'])
@auth_required
def create_group():
    """
    Creates a new user group in Beaker. The request must be 
    :mimetype:`application/json`.

    :jsonparam string group_name: Symbolic name for the group.
    :jsonparam string display_name: Human-friendly display name for the group.
    :jsonparam string description: Description of the group.
    :jsonparam string root_password: Optional root password for group jobs.
      If this is not set, group jobs will use the root password preferences of 
      the job submitter.
    :jsonparam string membership_type: Specifies how group membership is populated.
      Possible values are:

      * normal: Group is initially empty, members are explicitly added and removed by
        group owner.
      * ldap: Membership is populated from the LDAP group with the same group name.
      * inverted: Group contains all Beaker users *except* users who have been explicitly
        excluded by the group owner.

    :status 201: The group was successfully created.
    """
    user = identity.current.user
    data = read_json_request(request)
    if 'group_name' not in data:
        raise BadRequest400('Missing group_name key')
    if 'display_name' not in data:
        raise BadRequest400('Missing display_name key')
    # for backwards compatibility
    if data.pop('ldap', False):
        data['membership_type'] = 'ldap'
    if data.get('membership_type') == 'ldap':
        if not config.get("identity.ldap.enabled", False):
            raise BadRequest400('LDAP is not enabled')
        if not identity.current.user.is_admin():
            raise BadRequest400('Only admins can create LDAP groups')
    try:
        Group.by_name(data['group_name'])
    except NoResultFound:
        pass
    else:
        raise Conflict409("Group already exists: %s" % data['group_name'])
    with convert_internal_errors():
        group = Group.lazy_create(group_name=data['group_name'])
        group.display_name = data['display_name']
        group.description = data.get('description')
        group.root_password = data.get('root_password')
        session.add(group)
        group.record_activity(user=user, service=u'HTTP',
                field=u'Group', action=u'Created')
        if data.get('membership_type'):
            group.membership_type = GroupMembershipType.from_string(
                data['membership_type'])
        if group.membership_type == GroupMembershipType.ldap:
            group.refresh_ldap_members()
        else: # LDAP groups don't have any owners
            group.add_member(user, is_owner=True, agent=identity.current.user)
    response = jsonify(group.__json__())
    response.status_code = 201
    response.headers.add('Location', absolute_url(group.href))
    return response

def _get_group_by_name(group_name, lockmode=False):
    """Get group by name, reporting HTTP 404 if the group is not found"""
    try:
        return Group.by_name(group_name, lockmode)
    except NoResultFound:
        raise NotFound404('Group %s does not exist' % group_name)

@app.route('/groups/<group_name>', methods=['GET'])
def get_group(group_name):
    """
    Provides detailed information about a group in JSON format.

    :param group_name: Group's name.
    """
    group = _get_group_by_name(group_name)
    if request_wants_json():
        return jsonify(group.to_json())
    return render_tg_template('bkr.server.templates.group', {
        'title': group.group_name,
        'group': group,
    })

# To support the old urls that look like groups/edit?group_id=13 or
# groups/edit?group_name=abc
@app.route('/groups/edit', methods=['GET'])
def get_group_by_id_or_name():
    """
    Created for backwards compatibility. Will redirect to /groups/<group_name>.

    :queryparam group_id: Group's id.
    :queryparam group_name: Group's name.
    """
    if 'group_id' in request.args:
        with convert_internal_errors():
            group = Group.by_id(request.args['group_id'])
    elif 'group_name' in request.args:
        group = _get_group_by_name(request.args['group_name'])
    else:
        raise NotFound404
    return flask_redirect(absolute_url(group.href))

@app.route('/groups/<group_name>', methods=['PATCH'])
@auth_required
def update_group(group_name):
    """
    Updates attributes of an existing group. The request body must be a JSON
    object containing one or more of the following keys.

    :jsonparam string group_name: New name for the group.
    :jsonparam string display_name: Display name of the group.
    :jsonparam string description: Description of the group.
    :jsonparam string root_password: Optional password. Can be an empty string.
      If empty, group jobs will use the root password preferences of the job submitter.
    :jsonparam string membership_type: New membership type for the group.
      See `POST /groups/` for more information.

    :status 200: Group was updated.
    :status 400: Invalid data was given.
    """
    group = _get_group_by_name(group_name)
    if not group.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit group')
    data = read_json_request(request)
    with convert_internal_errors():
        user = identity.current.user
        renamed = False
        if 'group_name' in data:
            new_name = data['group_name']
            if new_name != group.group_name:
                if Group.query.filter(Group.group_name == new_name).count():
                    raise Conflict409('Group %s already exists' % new_name)
                group.set_name(user, u'HTTP', new_name)
                renamed = True
        if 'display_name' in data:
            new_display_name = data['display_name']
            if new_display_name != group.display_name:
                group.set_display_name(user, u'HTTP', new_display_name)
        if 'description' in data:
            new_description = data['description']
            if new_description != group.description:
                group.set_description(user, u'HTTP', new_description)
        if 'root_password' in data:
            new_root_password = data['root_password']
            if new_root_password != group.root_password:
                group.set_root_password(user, u'HTTP', new_root_password)
        # for backwards compatibility
        if data.pop('ldap', False):
            data['membership_type'] = 'ldap'
        if 'membership_type' in data:
            new_type = GroupMembershipType.from_string(
                    data['membership_type'])
            if (new_type == GroupMembershipType.ldap and not
                group.can_edit_ldap(user)):
                raise BadRequest400('Cannot edit LDAP group %s' % group)
            if new_type != group.membership_type:
                group.membership_type = new_type
    response = jsonify(group.to_json())
    if renamed:
        response.headers.add('Location', absolute_url(group.href))
    return response

@app.route('/groups/<group_name>', methods=['DELETE'])
@auth_required
def delete_group(group_name):
    """
    Deletes a group.

    :status 204: Group was successfully deleted.
    :status 400: Group cannot be deleted because it is a predefined group, or
      because it has associated jobs.
    """
    group = _get_group_by_name(group_name)
    if not group.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit group')
    if group.is_protected_group():
        raise BadRequest400("Group '%s' is predefined and cannot be deleted"
                % group.group_name)
    if group.jobs:
        raise BadRequest400('Cannot delete a group which has associated jobs')
    # Record the access policy rules that will be removed
    for rule in group.system_access_policy_rules:
        rule.record_deletion()
    # For any system pool owned by this group, unset owning_group
    # and set owning_user to the user deleting this group
    pools = SystemPool.query.filter_by(owning_group=group)
    for pool in pools:
        pool.change_owner(user=identity.current.user, service=u'HTTP')
    session.delete(group)
    activity = Activity(identity.current.user, u'HTTP', u'Removed', u'Group', group.display_name)
    session.add(activity)
    return '', 204

def _get_user_by_username(user_name):
    user = User.by_user_name(user_name)
    if not user:
        raise NotFound404('User %s does not exist' % user_name)
    return user

@app.route('/groups/<group_name>/members/', methods=['POST'])
@auth_required
def add_group_membership(group_name):
    """
    Add a user to a group.

    :param group_name: Group's name.
    :jsonparam string user_name: User's username.
    :jsonparam boolean is_owner: If true, the given user will become one of the
      group owners.

    """
    u = identity.current.user
    data = read_json_request(request)
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_modify_membership(identity.current.user):
        raise Forbidden403('Cannot edit membership of group %s' % group_name)
    if 'user_name' not in data:
        raise BadRequest400('User not specified')
    user = _get_user_by_username(data['user_name'])
    if user.removed:
        raise BadRequest400('Cannot add deleted user %s to group' % user.user_name)
    is_owner = data.get('is_owner', False)
    if user not in group.users:
        group.add_member(user, is_owner=is_owner, agent=identity.current.user)
        mail.group_membership_notify(user, group, agent=u, action='Added')
    else:
        raise Conflict409('User %s is already a member of group %s' % (user.user_name, group_name))
    return '', 204

@app.route('/groups/<group_name>/members/', methods=['DELETE'])
@auth_required
def remove_group_membership(group_name):
    """
    Remove a user from a group. If the user has the group ownership, it will be
    revoked.

    :param group_name: Group's name.
    :jsonparam string user_name: User's username.

    """
    u = identity.current.user
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_modify_membership(identity.current.user):
        raise Forbidden403('Cannot edit membership of group %s' % group_name)
    if 'user_name' not in request.args:
        raise MethodNotAllowed405
    user = _get_user_by_username(request.args['user_name'])
    if not group.can_remove_member(u, user.id):
        raise Forbidden403('Cannot remove user %s from group %s' % (user, group_name))
    if user in group.users:
        group.remove_member(user, agent=identity.current.user)
        mail.group_membership_notify(user, group, agent=identity.current.user,
                                     action='Removed')
    else:
        raise Conflict409('User %s is not a member of group %s' % (user.user_name, group_name))
    return '', 204

@app.route('/groups/<group_name>/excluded-users/', methods=['POST'])
@auth_required
def exclude_user(group_name):
    """
    Exclude a user from an inverted group. Then the user will not have the group
    membership.

    :param group_name: Group's name.
    :jsonparam string user_name: User's username.

    """
    u = identity.current.user
    data = read_json_request(request)
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_modify_membership(identity.current.user):
        raise Forbidden403('Cannot edit membership of group %s' % group_name)
    if group.membership_type == GroupMembershipType.normal:
        raise NotFound404('Normal group %s do not have excluded users' % group_name)
    if 'user_name' not in data:
        raise BadRequest400('User not specified')
    user = _get_user_by_username(data['user_name'])
    if user in group.users:
        if not group.can_exclude_member(u, user.id):
            raise Forbidden403('Cannot exclude user %s from group %s' % (user, group_name))
        with convert_internal_errors():
            group.exclude_user(user, agent=identity.current.user)
    else:
        raise Conflict409('User %s is already excluded from group %s' %
                (user.user_name, group_name))
    return '', 204

@app.route('/groups/<group_name>/excluded-users/', methods=['DELETE'])
@auth_required
def readd_user(group_name):
    """
    Re-add a user who has been excluded from the group.

    :param group_name: Group's name.
    :queryparam string user_name: User's username.

    """
    u = identity.current.user
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_modify_membership(identity.current.user):
        raise Forbidden403('Cannot edit membership of group %s' % group_name)
    if 'user_name' not in request.args:
        raise MethodNotAllowed405
    user = _get_user_by_username(request.args['user_name'])
    if user not in group.users:
        with convert_internal_errors():
            group.readd_user(user, agent=identity.current.user)
    else:
        raise Conflict409('User %s is not excluded from group %s' %
                (user.user_name, group_name))
    return '', 204

@app.route('/groups/<group_name>/owners/', methods=['POST'])
@auth_required
def grant_ownership(group_name):
    """
    Grant group ownership to a user. The user can either be the group member or
    not. If the user is not the group member, it will be added first.

    :param group_name: Group's name.
    :jsonparam string user_name: User's username.

    """
    u = identity.current.user
    data = read_json_request(request)
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_modify_ownership(identity.current.user):
        raise Forbidden403('Cannot edit ownership of group %s' % group_name)
    if 'user_name' not in data:
        raise BadRequest400('User not specified')
    user_name = data['user_name']
    user = _get_user_by_username(user_name)
    if not group.has_owner(user):
        group.grant_ownership(user, agent=identity.current.user)
    else:
        raise Conflict409('User %s is already an owner of group %s' % (user.user_name, group_name))
    return '', 204

@app.route('/groups/<group_name>/owners/', methods=['DELETE'])
@auth_required
def revoke_ownership(group_name):
    """

    Revoke group ownership from an existing group user.

    :param group_name: Group's name.
    :queryparam user_name: User's username.

    """
    u = identity.current.user
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_modify_ownership(identity.current.user):
        raise Forbidden403('Cannot edit ownership of group %s' % group_name)
    if 'user_name' not in request.args:
        raise MethodNotAllowed405
    user = _get_user_by_username(request.args['user_name'])
    if user not in group.users:
        raise BadRequest400('User is not a member of group %s' % group_name)
    if group.has_owner(user):
        if len(group.owners())==1 and not u.is_admin():
            raise Forbidden403('Cannot remove the only owner')
        group.revoke_ownership(user, agent=identity.current.user)
    else:
        raise Conflict409('User %s is not an owner of group %s' % (user.user_name, group_name))
    return '', 204

def _get_permission_by_name(permission_name):
    try:
        return Permission.by_name(permission_name)
    except NoResultFound:
        # Needs to return 400 as the resource exists but the given parameter is bad.
        raise BadRequest400("Permission '%s' does not exist" % permission_name)

@app.route('/groups/<group_name>/permissions/', methods=['POST'])
@admin_auth_required
def add_permission(group_name):
    """
    Add a permission to a group.

    :param group_name: Group's name.
    :jsonparam permission_name: Permission's name.

    """
    u = identity.current.user
    data = read_json_request(request)
    group = _get_group_by_name(group_name, lockmode='update')
    if 'permission_name' not in data:
        raise BadRequest400('Permission name not specified')
    permission = _get_permission_by_name(data['permission_name'])
    if permission not in group.permissions:
        group.permissions.append(permission)
        group.record_activity(user=u, service=u'HTTP',
                             action=u'Added', field=u'Permission', old=None,
                             new=unicode(permission))
    return '', 204

@app.route('/groups/<group_name>/permissions/', methods=['DELETE'])
@auth_required
def remove_permission(group_name):
    """
    Remove a permission from a group.

    :param group_name: Group's name.
    :queryparam permission_name: Permission's name.

    """
    u = identity.current.user
    group = _get_group_by_name(group_name, lockmode='update')
    if not group.can_edit(u):
        raise Forbidden403('Cannot edit group %s' % group_name)
    if 'permission_name' not in request.args:
        raise MethodNotAllowed405
    permission_name = request.args['permission_name']
    permission = _get_permission_by_name(permission_name)
    if permission in group.permissions:
        group.permissions.remove(permission)
        group.record_activity(user=u, service=u'HTTP',
                             action=u'Removed', field=u'Permission',
                             old=unicode(permission), new=None)
    else:
        raise Conflict409('Group %s does not have permission %s' % (group_name, permission_name))
    return '', 204

@app.route('/groups/+typeahead')
def groups_typeahead():
    if 'q' in request.args:
        groups = Group.list_by_name(request.args['q'], find_anywhere=False)
    else:
        groups = Group.query
    data = [{'group_name': group.group_name, 'display_name': group.display_name,
             'tokens': [group.group_name]}
            for group in groups.values(Group.group_name, Group.display_name)]
    return jsonify(data=data)

@app.route('/permissions/+typeahead')
def permissions_typeahead():
    if 'q' in request.args:
        permissions = Permission.by_name(request.args['q'], anywhere=True)
    else:
        permissions = Permission.query.all()
    data = [{'permission_name': permission.permission_name,
             'tokens': [permission.permission_name]}
            for permission in permissions]
    return jsonify(data=data)

# for sphinx
groups = Groups
