
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import redirect, config, expose, \
        flash, widgets, validate, error_handler, validators, redirect, \
        paginate, url
from turbogears.database import session
from sqlalchemy.orm.exc import NoResultFound
import cherrypy
from cherrypy import response
from kid import XML
from flask import jsonify, request
from bkr.server.validators import StrongPassword
from bkr.server.helpers import make_link
from bkr.server.widgets import BeakerDataGrid, myPaginateDataGrid, \
    GroupPermissions, DeleteLinkWidgetForm, LocalJSLink, AutoCompleteField, \
    HorizontalForm, InlineForm, InlineRemoteForm
from bkr.server.admin_page import AdminPage
from bkr.server.bexceptions import BX, BeakerException
from bkr.server.controller_utilities import restrict_http_method
from bkr.server.app import app
from bkr.server import mail, identity

from bkr.server.model import (Group, Permission, System, User, UserGroup,
                              Activity, GroupActivity, SystemActivity, 
                              SystemStatus)
from bkr.server.util import convert_db_lookup_error
from bkr.server.bexceptions import DatabaseLookupError

import logging
log = logging.getLogger(__name__)

class GroupOwnerModificationForbidden(BX, cherrypy.HTTPError):

    def __init__(self, message):
        # XXX: Call base class __init__?
        self._message = message
        self.args = [message]

    def set_response(self):
        response.status = 403
        response.body = self._message
        response.headers['content-type'] = 'application/json'

class GroupFormSchema(validators.Schema):
    display_name = validators.UnicodeString(not_empty=True,
                                            max=Group.display_name.property.columns[0].type.length,
                                            strip=True)
    group_name = validators.UnicodeString(not_empty=True,
                                          max=Group.group_name.property.columns[0].type.length,
                                          strip=True)
    root_password = StrongPassword()
    ldap = validators.StringBool(if_empty=False)

class GroupForm(HorizontalForm):
    fields = [
        widgets.HiddenField(name='group_id'),
        widgets.TextField(name='group_name', label=_(u'Group Name')),
        widgets.TextField(name='display_name', label=_(u'Display Name')),
        widgets.PasswordField(name='root_password', label=_(u'Root Password'),
            validator=StrongPassword()),
        widgets.CheckBox(name='ldap', label=_(u'LDAP'),
                help_text=_(u'Populate group membership from LDAP?')),
    ]
    name = 'Group'
    action = 'save_data'
    submit_text = _(u'Save')
    validator = GroupFormSchema()

    def update_params(self, d):
        if not identity.current.user.is_admin() or \
                not config.get('identity.ldap.enabled', False):
            d['disabled_fields'] = ['ldap']
        super(GroupForm, self).update_params(d)

class Groups(AdminPage):
    # For XMLRPC methods in this class.
    exposed = True
    group_id     = widgets.HiddenField(name='group_id')
    auto_users    = AutoCompleteField(name='user',
                                     search_controller = url("/users/by_name"),
                                     search_param = "input",
                                     result_name = "matches")
    auto_systems  = AutoCompleteField(name='system',
                                     search_controller = url("/by_fqdn"),
                                     search_param = "input",
                                     result_name = "matches")

    search_groups = AutoCompleteField(name='group',
                                     search_controller = url("/groups/by_name?anywhere=1"),
                                     search_param = "name",
                                     result_name = "groups")

    search_permissions = AutoCompleteField(name='permissions',
                                     search_controller = url("/groups/get_permissions"),
                                     search_param = "input",
                                     result_name = "matches")

    group_form = GroupForm()

    permissions_form = InlineRemoteForm(
        'Permissions',
        fields = [search_permissions, group_id],
        submit_text = _(u'Add'),
        on_success = 'add_group_permission_success(http_request.responseText)',
        on_failure = 'add_group_permission_failure(http_request.responseText)',
        before = 'before_group_permission_submit()',
        after = 'after_group_permission_submit()',
    )

    group_user_form = InlineForm(
        'GroupUser',
        fields = [group_id, auto_users],
        action = 'save_data',
        submit_text = _(u'Add'),
    )

    group_system_form = InlineForm(
        'GroupSystem',
        fields = [group_id, auto_systems],
        action = 'save_data',
        submit_text = _(u'Add'),
    )

    delete_link = DeleteLinkWidgetForm()

    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/groups/by_name?anywhere=1")
        kw['search_name'] = 'group'
        kw['widget_action'] = ''
        super(Groups,self).__init__(*args,**kw)

        self.search_col = Group.group_name
        self.search_mapper = Group

    @expose(format='json')
    def by_name(self, input,*args,**kw):
        input = input.lower()
        if 'anywhere' in kw:
            search = Group.list_by_name(input, find_anywhere=True)
        else:
            search = Group.list_by_name(input)

        groups =  [match.group_name for match in search]
        return dict(matches=groups)

    @expose(format='json')
    @identity.require(identity.not_anonymous())
    def remove_group_permission(self, group_id, permission_id):
        try:
            group = Group.by_id(group_id)
        except DatabaseLookupError:
            log.exception('Group id %s is not a valid Group to remove' % group_id)
            return ['0']

        if not group.can_edit(identity.current.user):
            log.exception('User %d does not have edit permissions for Group id %s'
                          % (identity.current.user.user_id, group_id))
            response.status = 403
            return ['You are not an owner of group %s' % group]

        try:
            permission = Permission.by_id(permission_id)
        except NoResultFound:
            log.exception('Permission id %s is not a valid Permission to remove' % permission_id)
            return ['0']
        group.permissions.remove(permission)
        return ['1']

    @expose(format='json')
    def get_permissions(self, input):
        results = Permission.by_name(input, anywhere=True)
        permission_names = [result.permission_name for result in results]
        return dict(matches=permission_names)

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.group_form,
            title = 'New Group',
            action = './save_new',
            options = {},
            value = kw,
        )

    def show_members(self, group):
        can_edit = False
        if identity.current.user:
            can_edit = group.can_modify_membership(identity.current.user)

        def show_ownership_status(member):
            is_owner = member.is_owner
            if can_edit:
                if is_owner:
                    return XML('<a class="btn change_ownership_remove" '
                            'href="revoke_owner?group_id=%s&amp;id=%s">'
                            '<i class="icon-remove"/> Remove</a>'
                            % (group.group_id, member.user_id))
                else:
                    return XML('<a class="btn change_ownership_add" '
                            'href="grant_owner?group_id=%s&amp;id=%s">'
                            '<i class="icon-plus"/> Add</a>'
                            % (group.group_id, member.user_id))
            else:
                is_owner = 'Yes' if is_owner else 'No'
                return is_owner

        def remove_button(member):
            return XML('<a class="btn" href="removeUser?group_id=%s&amp;id=%s">'
                    '<i class="icon-remove"/> Remove</a>' % (group.group_id, member.user_id))

        user_fields = [
            ('User', lambda x: x.user.user_name)
        ]

        user_fields.append(('Group Ownership', show_ownership_status))
        if can_edit:
            user_fields.append(('Group Membership', remove_button))

        return BeakerDataGrid(name='group_members_grid', fields=user_fields)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def systems(self,group_id=None,*args,**kw):
        try:
            group = Group.by_id(group_id)
        except DatabaseLookupError:
            log.exception('Group id %s is not a valid group id' % group_id)
            flash(_(u'Need a valid group to search on'))
            redirect('../groups/mine')

        systems = System.all(identity.current.user). \
                  filter(System.groups.contains(group)). \
                  filter(System.status != SystemStatus.removed)
        title = 'Systems in Group %s' % group.group_name
        from bkr.server.controllers import Root
        return Root()._systems(systems, title, group_id = group_id,**kw)

    @expose(template='bkr.server.templates.group_form')
    def edit(self, group_id=None, group_name=None, **kw):
        # Not just for editing, also provides a read-only view
        if group_id is not None:
            try:
                group = Group.by_id(group_id)
            except DatabaseLookupError:
                log.exception('Group id %s is not a valid group id' % group_id)
                flash(_(u'Need a valid group to search on'))
                redirect('../groups/mine')
        elif group_name is not None:
            try:
                group = Group.by_name(group_name)
            except NoResultFound:
                log.exception('Group name %s is not a valid group name' % group_name)
                flash(_(u'Need a valid group to search on'))
                redirect('../groups/mine')
        else:
            redirect('../groups/mine')

        usergrid = self.show_members(group)

        can_edit = False
        if identity.current.user:
            can_edit = group.can_edit(identity.current.user)

        systems_fields = [('System', lambda x: x.link)]
        if can_edit:
            system_remove_widget = DeleteLinkWidgetForm(action='removeSystem',
                    hidden_fields=[widgets.HiddenField(name='group_id'),
                        widgets.HiddenField(name='id')],
                    action_text=u'Remove')
            systems_fields.append((' ', lambda x: system_remove_widget.display(
                dict(group_id=group_id, id=x.id))))
        systemgrid = BeakerDataGrid(fields=systems_fields)

        permissions_fields = [('Permission', lambda x: x.permission_name)]
        if can_edit:
            permissions_fields.append((' ', lambda x: XML(
                    '<a class="btn" href="#" id="remove_permission_%s">'
                    '<i class="icon-remove"/> Remove</a>' % x.permission_id)))
        group_permissions_grid = BeakerDataGrid(name='group_permission_grid',
                fields=permissions_fields)
        group_permissions = GroupPermissions()

        return dict(
            form = self.group_form,
            system_form = self.group_system_form,
            user_form = self.group_user_form,
            group_edit_js = LocalJSLink('bkr', '/static/javascript/group_users_v2.js'),
            action = './save',
            system_action = './save_system',
            user_action = './save_user',
            options = {},
            value = group,
            group_pw = group.root_password,
            usergrid = usergrid,
            systemgrid = systemgrid,
            disabled_fields=[],
            group_permissions = group_permissions,
            group_form = self.permissions_form,
            group_permissions_grid = group_permissions_grid,
        )

    def _new_group(self, group_id, display_name, group_name, ldap,
        root_password):
        user = identity.current.user
        if ldap and not user.is_admin():
            flash(_(u'Only admins can create LDAP groups'))
            redirect('.')
        try:
            Group.by_name(group_name)
        except NoResultFound:
            pass
        else:
            flash( _(u"Group %s already exists." % group_name) )
            redirect(".")

        group = Group()
        session.add(group)
        group.record_activity(user=user, service=u'WEBUI', field=u'Group',
                action=u'Created')
        group.display_name = display_name
        group.group_name = group_name
        group.ldap = ldap
        if group.ldap:
            group.refresh_ldap_members()
        group.root_password = root_password
        if not ldap: # LDAP groups don't have owners
            group.user_group_assocs.append(UserGroup(user=user, is_owner=True))
            group.activity.append(GroupActivity(user, service=u'WEBUI',
                action=u'Added', field_name=u'User',
                old_value=None, new_value=user.user_name))
            group.activity.append(GroupActivity(user, service=u'WEBUI',
                action=u'Added', field_name=u'Owner',
                old_value=None, new_value=user.user_name))
        return group

    @expose()
    @validate(form=group_form)
    @error_handler(new)
    @identity.require(identity.not_anonymous())
    def save_new(self, group_id=None, display_name=None, group_name=None,
        ldap=False, root_password=None, **kwargs):
        # save_new() is needed because 'edit' is not a viable
        # error handler for new groups.
        self._new_group(group_id, display_name, group_name, ldap,
            root_password)
        flash( _(u"OK") )
        redirect("mine")

    @expose()
    @validate(form=group_form)
    @error_handler(edit)
    @identity.require(identity.not_anonymous())
    def save(self, group_id=None, display_name=None, group_name=None,
        ldap=False, root_password=None, **kwargs):

        user = identity.current.user

        if ldap and not user.is_admin():
            flash(_(u'Only admins can create LDAP groups'))
            redirect('mine')

        try:
            group = Group.by_id(group_id)
        except DatabaseLookupError:
            flash( _(u"Group %s does not exist." % group_id) )
            redirect('mine')

        try:
            Group.by_name(group_name)
        except NoResultFound:
            pass
        else:
            if group_name != group.group_name:
                flash(_(u'Failed to update group %s: Group name already exists: %s' % 
                        (group.group_name, group_name)))
                redirect('mine')

        if not group.can_edit(user):
            flash(_(u'You are not an owner of group %s' % group))
            redirect('../groups/mine')

        try:
            group.set_name(user, u'WEBUI', group_name)
            group.set_display_name(user, u'WEBUI', display_name)
            group.ldap = ldap
            group.set_root_password(user, u'WEBUI', root_password)
        except BeakerException, err:
            session.rollback()
            flash(_(u'Failed to update group %s: %s' %
                                                    (group.group_name, err)))
            redirect('.')

        flash( _(u"OK") )
        redirect("mine")

    @expose()
    @error_handler(edit)
    @identity.require(identity.not_anonymous())
    def save_system(self, **kw):
        try:
            with convert_db_lookup_error('No such system: %s' % kw['system']['text']):
                system = System.by_fqdn(kw['system']['text'],identity.current.user)
        except DatabaseLookupError, e:
            flash(unicode(e))
            redirect("./edit?group_id=%s" % kw['group_id'])
        # A system owner can add their system to a group, but a group owner 
        # *cannot* add an arbitrary system to their group because that would 
        # grant them extra privileges over it.
        if not system.can_edit(identity.current.user):
            flash(_(u'You do not have permission to edit system %s' % system))
            redirect('edit?group_id=%s' % kw['group_id'])
        group = Group.by_id(kw['group_id'])
        if group in system.groups:
            flash( _(u"System '%s' is already in group '%s'" % (system.fqdn, group.group_name)))
            redirect("./edit?group_id=%s" % kw['group_id'])
        group.systems.append(system)
        activity = GroupActivity(identity.current.user, u'WEBUI', u'Added', u'System', u"", system.fqdn)
        sactivity = SystemActivity(identity.current.user, u'WEBUI', u'Added', u'Group', u"", group.display_name)
        group.activity.append(activity)
        system.activity.append(sactivity)
        flash( _(u"OK") )
        redirect("./edit?group_id=%s" % kw.get('group_id'))

    @identity.require(identity.in_group("admin"))
    @expose(format='json')
    def save_group_permissions(self, **kw):
        try:
            permission_name = kw['permissions']['text']
        except KeyError:
            log.exception('Permission not submitted correctly')
            response.status = 403
            return ['Permission not submitted correctly']
        try:
            permission = Permission.by_name(permission_name)
        except NoResultFound:
            log.exception('Invalid permission: %s' % permission_name)
            response.status = 403
            return ['Invalid permission value']
        try:
            group_id = kw['group_id']
        except KeyError:
            log.exception('Group id not submitted')
            response.status = 403
            return ['No group id given']
        try:
            group = Group.by_id(group_id)
        except NoResultFound:
            log.exception('Group id %s is not a valid group id' % group_id)
            response.status = 403
            return ['Invalid Group Id']

        group = Group.by_id(group_id)
        if permission not in group.permissions:
            group.permissions.append(permission)
        else:
            response.status = 403
            return ['%s already exists in group %s' %
                (permission.permission_name, group.group_name)]

        return {'name':permission_name, 'id':permission.permission_id}

    @expose()
    @error_handler(edit)
    @identity.require(identity.not_anonymous())
    def save_user(self, **kw):
        user = User.by_user_name(kw['user']['text'])
        if user is None:
            flash(_(u"Invalid user %s" % kw['user']['text']))
            redirect("./edit?group_id=%s" % kw['group_id'])
        group = Group.by_id(kw['group_id'])

        if not group.can_modify_membership(identity.current.user):
            flash(_(u'You are not an owner of group %s' % group))
            redirect('../groups/mine')

        if user not in group.users:
            group.users.append(user)
            activity = GroupActivity(identity.current.user, u'WEBUI', u'Added', u'User', u"", user.user_name)
            group.activity.append(activity)
            mail.group_membership_notify(user, group,
                                         agent=identity.current.user,
                                         action='Added')
            flash( _(u"OK") )
            redirect("./edit?group_id=%s" % kw['group_id'])
        else:
            flash( _(u"User %s is already in Group %s" %(user.user_name, group.group_name)))
            redirect("./edit?group_id=%s" % kw['group_id'])

    @expose(template="bkr.server.templates.grid")
    @paginate('list', default_order='group_name', limit=20)
    def index(self, *args, **kw):
        groups = self.process_search(*args, **kw)
        template_data = self.groups(groups, *args, **kw)
        return template_data

    @expose(template="bkr.server.templates.grid")
    @identity.require(identity.not_anonymous())
    @paginate('list', default_order='group_name', limit=20)
    def mine(self,*args,**kw):
        groups = self.process_search(*args, **kw)
        groups = groups.filter(Group.users.contains(identity.current.user))
        template_data = self.groups(groups, *args, **kw)
        template_data['title'] = 'My Groups'
        return template_data

    def groups(self, groups=None, *args,**kw):
        if groups is None:
            groups = session.query(Group)

        def get_sys(x):
            systems = System.all(identity.current.user). \
                      filter(System.groups.contains(x)). \
                      filter(System.status != SystemStatus.removed).all()
            if len(systems):
                return make_link('systems?group_id=%s' % x.group_id, u'System count: %s' % len(systems))
            else:
                return 'System count: 0'

        def get_remove_link(x):
            try:
                if x.can_edit(identity.current.user):
                    return self.delete_link.display(dict(group_id=x.group_id),
                                             action=url('remove'),
                                             action_text='Delete Group')
                else:
                    return ''
            except AttributeError:
                return ''

        group_name = ('Group Name', lambda group: make_link(
                'edit?group_id=%s' % group.group_id, group.group_name))
        systems = ('Systems', get_sys)
        display_name = ('Display Name', lambda x: x.display_name)
        remove_link = ('', get_remove_link)

        grid_fields =  [group_name, display_name, systems, remove_link]
        grid = myPaginateDataGrid(fields=grid_fields,
                add_action='./new' if not identity.current.anonymous else None)
        return_dict = dict(title=u"Groups",
                           grid=grid,
                           search_bar = None,
                           search_widget = self.search_widget_form,
                           list = groups)
        return return_dict

    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def revoke_owner(self, group_id=None, id=None, **kw):

        if group_id is not None and id is not None:
            group = Group.by_id(group_id)
            user = User.by_id(id)
            service = 'WEBUI'
        else:
            group = Group.by_name(kw['group_name'])
            user = User.by_user_name(kw['member_name'])
            service = 'XMLRPC'

        if group.ldap:
            raise GroupOwnerModificationForbidden('An LDAP group does not have an owner')

        if not group.can_edit(identity.current.user):
            raise GroupOwnerModificationForbidden('You are not an owner of group %s' % group)

        if user not in group.users:
            raise GroupOwnerModificationForbidden('User is not a group member')

        if len(group.owners())==1 and not identity.current.user.is_admin():
            raise GroupOwnerModificationForbidden('Cannot remove the only owner')
        else:
            for assoc in group.user_group_assocs:
                if assoc.user == user:
                    if assoc.is_owner:
                        assoc.is_owner = False
                        group.record_activity(user=identity.current.user, service=service,
                                              field=u'Owner', action='Removed',
                                              old=user.user_name, new=u'')
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

    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def grant_owner(self, group_id=None, id=None, **kw):

        if group_id is not None and id is not None:
            group = Group.by_id(group_id)
            user = User.by_id(id)
            service = 'WEBUI'
        else:
            group = Group.by_name(kw['group_name'])
            user = User.by_user_name(kw['member_name'])
            service = 'XMLRPC'

        if group.ldap:
            raise GroupOwnerModificationForbidden('An LDAP group does not have an owner')

        if not group.can_edit(identity.current.user):
            raise GroupOwnerModificationForbidden('You are not an owner of the group %s' % group)

        if user not in group.users:
            raise GroupOwnerModificationForbidden('User is not a group member')
        else:
            for assoc in group.user_group_assocs:
                if assoc.user == user:
                    if not assoc.is_owner:
                        assoc.is_owner = True
                        group.record_activity(user=identity.current.user, service=service,
                                              field=u'Owner', action='Added',
                                              old=u'', new=user.user_name)
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

    @identity.require(identity.not_anonymous())
    @expose()
    def removeUser(self, group_id=None, id=None, **kw):
        group = Group.by_id(group_id)

        if not group.can_modify_membership(identity.current.user):
            flash(_(u'You are not an owner of group %s' % group))
            redirect('../groups/mine')

        if not group.can_remove_member(identity.current.user, id):
            flash(_(u'Cannot remove member'))
            redirect('../groups/edit?group_id=%s' % group_id)

        groupUsers = group.users
        for user in groupUsers:
            if user.user_id == int(id):
                group.users.remove(user)
                removed = user
                activity = GroupActivity(identity.current.user, u'WEBUI', u'Removed', u'User', removed.user_name, u"")
                group.activity.append(activity)
                mail.group_membership_notify(user, group,
                                             agent=identity.current.user,
                                             action='Removed')
                flash(_(u"%s Removed" % removed.display_name))
                redirect("../groups/edit?group_id=%s" % group_id)
        flash( _(u"No user %s in group %s" % (id, removed.display_name)))
        raise redirect("../groups/edit?group_id=%s" % group_id)

    @identity.require(identity.not_anonymous())
    @expose()
    @restrict_http_method('post')
    def removeSystem(self, group_id=None, id=None, **kw):
        group = Group.by_id(group_id)
        system = System.by_id(id, identity.current.user)

        # A group owner can remove a system from their group.
        # A system owner can remove their system from a group.
        # But note this is not symmetrical with adding systems.
        if not (group.can_edit(identity.current.user) or
                system.can_edit(identity.current.user)):
            flash(_(u'Not permitted to remove %s from %s') % (system, group))
            redirect('../groups/mine')

        group.systems.remove(system)
        activity = GroupActivity(identity.current.user, u'WEBUI', u'Removed', u'System', system.fqdn, u"")
        sactivity = SystemActivity(identity.current.user, u'WEBUI', u'Removed', u'Group', group.display_name, u"")
        group.activity.append(activity)
        system.activity.append(sactivity)
        flash( _(u"%s Removed" % system.fqdn))
        raise redirect("./edit?group_id=%s" % group_id)

    @identity.require(identity.not_anonymous())
    @expose()
    @restrict_http_method('post')
    def remove(self, **kw):
        try:
            group = Group.by_id(kw['group_id'])
        except DatabaseLookupError:
            flash(unicode('Invalid group or already removed'))
            redirect('../groups/mine')

        if not group.can_edit(identity.current.user):
            flash(_(u'You are not an owner of group %s' % group))
            redirect('../groups/mine')

        if group.jobs:
            flash(_(u'Cannot delete a group which has associated jobs'))
            redirect('../groups/mine')

        # Record the access policy rules that will be removed
        # before deleting the group
        for rule in group.system_access_policy_rules:
            rule.record_deletion()

        session.delete(group)
        activity = Activity(identity.current.user, u'WEBUI', u'Removed', u'Group', group.display_name, u"")
        session.add(activity)
        for system in group.systems:
            session.add(SystemActivity(identity.current.user, u'WEBUI', u'Removed', u'Group', group.display_name, u"", object=system))
        flash( _(u"%s deleted") % group.display_name )
        raise redirect(".")

    @expose(format='json')
    def get_group_users(self, group_id=None, *args, **kw):
        try:
            group = Group.by_id(group_id)
        except DatabaseLookupError:
            log.exception('Group id %s is not a valid group id' % group_id)
            response.status = 403
            return ['Invalid Group Id']

        users = group.users
        return [(user.user_id, user.display_name) for user in users]

    @expose(format='json')
    def get_group_systems(self, group_id=None, *args, **kw):
        try:
            group = Group.by_id(group_id)
        except DatabaseLookupError:
            log.exception('Group id %s is not a valid group id' % group_id)
            response.status = 403
            return ['Invalid Group Id']

        systems = System.all(identity.current.user).filter(System.groups.contains(group)). \
                  filter(System.status != SystemStatus.removed)

        return [(system.id, system.fqdn) for system in systems]

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
            'ldap'
                 Populate users from LDAP (True/False)

        Returns a message whether the group was successfully created or
        raises an exception on failure.

        """
        display_name = kw.get('display_name')
        group_name = kw.get('group_name')
        ldap = kw.get('ldap')
        password = kw.get('root_password')

        if ldap and not identity.current.user.is_admin():
            raise BX(_(u'Only admins can create LDAP groups'))
        try:
            group = Group.by_name(group_name)
        except NoResultFound:
            #validate
            GroupFormSchema.fields['group_name'].to_python(group_name)
            GroupFormSchema.fields['display_name'].to_python(display_name)

            group = Group()
            session.add(group)
            group.record_activity(user=identity.current.user, service=u'XMLRPC',
                    field=u'Group', action=u'Created')
            group.display_name = display_name
            group.group_name = group_name
            group.ldap = ldap
            group.root_password = password
            user = identity.current.user

            if not ldap:
                group.user_group_assocs.append(UserGroup(user=user, is_owner=True))
                group.activity.append(GroupActivity(user, service=u'XMLRPC',
                    action=u'Added', field_name=u'User',
                    old_value=None, new_value=user.user_name))
                group.activity.append(GroupActivity(user, service=u'XMLRPC',
                    action=u'Added', field_name=u'Owner',
                    old_value=None, new_value=user.user_name))

            if group.ldap:
                group.refresh_ldap_members()
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

        if group.ldap:
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

            GroupFormSchema.fields['group_name'].to_python(group_name)
            group.set_name(user, u'XMLRPC', kw.get('group_name', None))

        display_name = kw.get('display_name', None)
        if display_name:
            GroupFormSchema.fields['display_name'].to_python(display_name)
            group.set_display_name(user, u'XMLRPC', display_name)

        root_password = kw.get('root_password', None)
        if root_password:
            group.set_root_password(user, u'XMLRPC', root_password)

        if kw.get('add_member', None):
            username = kw.get('add_member')
            user = User.by_user_name(username)
            if user is None:
                raise BX(_(u'User does not exist %s' % username))

            if user not in group.users:
                group.users.append(user)
                activity = GroupActivity(identity.current.user, u'XMLRPC',
                                            action=u'Added',
                                            field_name=u'User',
                                            old_value=u"", new_value=username)
                group.activity.append(activity)
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
                        group.users.remove(usr)
                        removed = user
                        activity = GroupActivity(identity.current.user, u'XMLRPC',
                                                    action=u'Removed',
                                                    field_name=u'User',
                                                    old_value=removed.user_name,
                                                    new_value=u"")
                        group.activity.append(activity)
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

# for sphinx
groups = Groups
