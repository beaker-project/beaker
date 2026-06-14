# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose
from bkr.server import config, mail, identity
from bkr.server.database import session
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import BX
from bkr.server.model import Group, GroupMembershipType, User


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
            raise BX(u'Only admins can create LDAP groups')
        if ldap and not config.get("identity.ldap.enabled", False):
            raise BX(u'LDAP is not enabled')
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
            raise BX(u'Group already exists: %s.' % group_name)

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
            raise BX('Please specify an attribute to modify.')

        try:
            group = Group.by_name(group_name)
        except NoResultFound:
            raise BX(u'Group does not exist: %s.' % group_name)

        if group.membership_type == GroupMembershipType.ldap:
            if not identity.current.user.is_admin():
                raise BX(u'Only admins can modify LDAP groups')
            if kw.get('add_member', None) or kw.get('remove_member', None):
                raise BX(u'Cannot edit membership of an LDAP group')

        user = identity.current.user
        if not group.can_edit(user):
            raise BX('You are not an owner of group %s' % group_name)

        group_name = kw.get('group_name', None)
        if group_name:
            try:
                Group.by_name(group_name)
            except NoResultFound:
                pass
            else:
                if group_name != group.group_name:
                    raise BX(u'Failed to update group %s: Group name already exists: %s' %
                               (group.group_name, group_name))

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
                raise BX(u'User does not exist %s' % username)
            if user.removed:
                raise BX(u'Cannot add deleted user %s to group' % user.user_name)

            if user not in group.users:
                group.add_member(user, service=u'XMLRPC',
                        agent=identity.current.user)
                mail.group_membership_notify(user, group,
                                                agent = identity.current.user,
                                                action='Added')
            else:
                raise BX(u'User %s is already in group %s' % (username, group.group_name))

        if kw.get('remove_member', None):
            username = kw.get('remove_member')
            user = User.by_user_name(username)

            if user is None:
                raise BX(u'User does not exist %s' % username)

            if user not in group.users:
                raise BX(u'No user %s in group %s' % (username, group.group_name))
            else:
                if not group.can_remove_member(identity.current.user, user.user_id):
                    raise BX(u'Cannot remove member')

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
            raise BX(u'Group does not exist: %s.' % group_name)

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
