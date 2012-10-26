from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from sqlalchemy.orm.exc import NoResultFound
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import BeakerDataGrid, myPaginateDataGrid, \
    GroupPermissions, DeleteLinkWidgetForm
from bkr.server.admin_page import AdminPage
from bkr.server.controller_utilities import restrict_http_method
import cherrypy

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

class GroupFormSchema(validators.Schema):
    display_name = validators.UnicodeString(not_empty=True, max=256, strip=True)
    group_name = validators.UnicodeString(not_empty=True, max=256, strip=True)


class Groups(AdminPage):
    # For XMLRPC methods in this class.
    exposed = False

    group_id     = widgets.HiddenField(name='group_id')
    display_name = widgets.TextField(name='display_name', label=_(u'Display Name'))
    group_name   = widgets.TextField(name='group_name', label=_(u'Group Name'))
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

    group_form = widgets.TableForm(
        'Group',
        fields = [group_id, display_name, group_name],
        action = 'save_data',
        submit_text = _(u'Save'),
        validator = GroupFormSchema()
    )

    permissions_form = widgets.RemoteForm(
        'Permissions',
        fields = [search_permissions, group_id],
        submit_text = _(u'Add'),
        validator = GroupFormSchema(),
        on_success = 'add_group_permission_success(http_request.responseText)',
        on_failure = 'add_group_permission_failure(http_request.responseText)',
        before = 'before_group_permission_submit()',
        after = 'after_group_permission_submit()',
    )

    group_user_form = widgets.TableForm(
        'GroupUser',
        fields = [group_id, auto_users],
        action = 'save_data',
        submit_text = _(u'Add'),
    )

    group_system_form = widgets.TableForm(
        'GroupSystem',
        fields = [group_id, auto_systems],
        action = 'save_data',
        submit_text = _(u'Add'),
    )

    delete_link = DeleteLinkWidgetForm()

    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/groups/by_name?anywhere=1")
        kw['search_name'] = 'group'
        kw['widget_action'] = './admin'
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
    @identity.require(identity.in_group('admin'))
    def remove_group_permission(self, group_id, permission_id):
        try:
            group = Group.by_id(group_id)
        except NoResultFound:
            log.exception('Group id %s is not a valid Group to remove' % group_id)
            return ['0']
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

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.group_form,
            action = './save',
            options = {},
            value = kw,
        )
    
    def show_members(self,id): 
        user_member = ('User Members', lambda x: x.display_name)
        
        if identity.in_group('admin'):
            remove_link = (' ', lambda x: make_link('removeUser?group_id=%s&id=%s' % (id, x.user_id), u'Remove (-)'))
        
        user_fields = [user_member]
        if 'remove_link' in locals(): 
            user_fields.append(remove_link)

        return widgets.DataGrid(fields=user_fields)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def systems(self,group_id=None,*args,**kw):
        try:
            group = Group.by_id(group_id)
        except NoResultFound:
            log.exception('Group id %s is not a valid group id' % group_id)
            flash(_(u'Need a valid group to search on'))
            redirect('../groups/mine')

        systems = System.all(identity.current.user).filter(System.groups.contains(group))
        title = 'Systems in Group %s' % group.group_name
        from bkr.server.controllers import Root
        return Root()._systems(systems,title, group_id = group_id,**kw)

    @expose(template='bkr.server.templates.group_users')
    def group_members(self,id, **kw):
        try:
            group = Group.by_id(id)
        except NoResultFound:
            log.exception('Group id %s is not a valid group id' % id)
            flash(_(u'Need a valid group to search on'))
            redirect('../groups/')

        usergrid = self.show_members(id)
        return dict(value = group,grid = usergrid)

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.group_form')
    def edit(self, id, **kw):
        try:
            group = Group.by_id(id)
        except NoResultFound:
            log.exception('Group id %s is not a valid group id' % id)
            flash(_(u'Need a valid group to search on'))
            redirect('../groups/mine')

        usergrid = self.show_members(id)
        systemgrid = widgets.DataGrid(fields=[
                                  ('System Members', lambda x: x.fqdn),
                                  (' ', lambda x: make_link('removeSystem?group_id=%s&id=%s' % (id, x.id), u'Remove (-)')),
                              ])
        group_permissions_grid = self.show_permissions()
        group_permissions = GroupPermissions()
        return dict(
            form = self.group_form,
            system_form = self.group_system_form,
            user_form = self.group_user_form,
            action = './save',
            system_action = './save_system',
            user_action = './save_user',
            options = {},
            value = group,
            usergrid = usergrid,
            systemgrid = systemgrid,
            disabled_fields = ['System Members'],
            group_permissions = group_permissions,
            group_form = self.permissions_form,
            group_permissions_grid = group_permissions_grid,
        )
    
    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(form=group_form)
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('group_id'):
            group = Group.by_id(kw['group_id'])
        else:
            group = Group()
            activity = Activity(identity.current.user, u'WEBUI', u'Added', u'Group', u"", kw['display_name'] )
        group.display_name = kw['display_name']
        group.group_name = kw['group_name']
        flash( _(u"OK") )
        redirect(".")

    @identity.require(identity.in_group("admin"))
    @expose()
    @error_handler(edit)
    def save_system(self, **kw):
        system = System.by_fqdn(kw['system']['text'],identity.current.user)
        group = Group.by_id(kw['group_id'])
        group.systems.append(system)
        activity = GroupActivity(identity.current.user, u'WEBUI', u'Added', u'System', u"", system.fqdn)
        sactivity = SystemActivity(identity.current.user, u'WEBUI', u'Added', u'Group', u"", group.display_name)
        group.activity.append(activity)
        system.activity.append(sactivity)
        flash( _(u"OK") )
        redirect("./edit?id=%s" % kw['group_id'])

    @identity.require(identity.in_group("admin"))
    @expose(format='json')
    def save_group_permissions(self, **kw):
        try:
            permission_name = kw['permissions']['text']
        except KeyError, e:
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

    @identity.require(identity.in_group("admin"))
    @expose()
    @error_handler(edit)
    def save_user(self, **kw):
        user = User.by_user_name(kw['user']['text'])
        if user is None: 
            flash(_(u"Invalid user %s" % kw['user']['text']))
            redirect("./edit?id=%s" % kw['group_id'])
        group = Group.by_id(kw['group_id'])
        group.users.append(user)
        activity = GroupActivity(identity.current.user, u'WEBUI', u'Added', u'User', u"", user.user_name)
        group.activity.append(activity)
        flash( _(u"OK") )
        redirect("./edit?id=%s" % kw['group_id'])


    @expose(template="bkr.server.templates.grid")
    @paginate('list', default_order='group_name', limit=20)
    def index(self, *args, **kw):
        template_data = self.groups(user=identity.current.user, *args, **kw)
        template_data['grid'] = myPaginateDataGrid(fields=template_data['grid_fields'])
        return template_data
   
    @expose(template="bkr.server.templates.admin_grid")
    @identity.require(identity.in_group('admin'))
    @paginate('list', default_order='group_name', limit=20)
    def admin(self, *args, **kw):
        groups = self.process_search(*args, **kw)
        template_data = self.groups(groups, identity.current.user, *args, **kw)
        template_data['grid_fields'].append((' ',
            lambda x: self.delete_link.display(dict(id=x.group_id),
                                               action=url('remove'),
                                               action_text='Remove (-)')))
        groups_grid = myPaginateDataGrid(fields=template_data['grid_fields'])
        template_data['grid'] = groups_grid

        alpha_nav_data = set([elem.group_name[0].capitalize() for elem in groups])
        nav_bar = self._build_nav_bar(alpha_nav_data,'group')
        template_data['alpha_nav_bar'] = nav_bar
        template_data['addable'] = True
        return template_data


    @expose(template="bkr.server.templates.grid")
    @identity.require(identity.not_anonymous()) 
    @paginate('list', default_order='group_name', limit=20)
    def mine(self,*args,**kw):
        current_user = identity.current.user
        my_groups = Group.by_user(current_user)
        template_data = self.groups(my_groups,current_user,*args,**kw)
        template_data['title'] = 'My Groups'
        template_data['grid'] = myPaginateDataGrid(template_data['grid_fields'])
        return template_data

    def show_permissions(self):
        grid = widgets.DataGrid(fields=[('Permissions', lambda x: x.permission_name),
            (' ', lambda x: make_fake_link('','remove_permission_%s' % x.permission_id, 'Remove (-)'))])
        grid.name = 'group_permission_grid'
        return grid

    def groups(self, groups=None, user=None, *args,**kw):
        if groups is None:
            groups = session.query(Group)
        try:
            if user.is_admin(): #Raise if no user, then give default columns
                group_name = ('Group Name', lambda x: make_edit_link(x.group_name,x.group_id))
            else:
                raise AttributeError() #If we aren't admin, the except block will assign our columns below
        except AttributeError, e: 
            group_name = ('Group Name', lambda x: make_link('group_members?id=%s' % x.group_id,x.group_name))
     
        def f(x):
            if len(x.systems):
                return make_link('systems?group_id=%s' % x.group_id, u'System count: %s' % len(x.systems))
            else:
                return 'System count: 0' 

        systems = ('Systems', lambda x: f(x))
        display_name = ('Display Name', lambda x: x.display_name)
        grid_fields =  [group_name, display_name, systems]
        return_dict = dict(title=u"Groups",
                           grid_fields = grid_fields,
                           object_count = groups.count(), 
                           search_bar = None,
                           search_widget = self.search_widget_form, 
                           list = groups)

        return return_dict
  
    @identity.require(identity.in_group("admin"))
    @expose()
    def removeUser(self, group_id=None, id=None, **kw):
        group = Group.by_id(group_id)
        groupUsers = group.users
        for user in groupUsers:
            if user.user_id == int(id):
                group.users.remove(user)
                removed = user
                activity = GroupActivity(identity.current.user, u'WEBUI', u'Removed', u'User', removed.user_name, u"")
                group.activity.append(activity)
        flash( _(u"%s Removed" % removed.display_name))
        raise redirect("./edit?id=%s" % group_id)

    @identity.require(identity.in_group("admin"))
    @expose()
    @restrict_http_method('post')
    def removeSystem(self, group_id=None, id=None, **kw):
        group = Group.by_id(group_id)
        groupSystems = group.systems
        for system in groupSystems:
            if system.id == int(id):
                group.systems.remove(system)
                removed = system
                activity = GroupActivity(identity.current.user, u'WEBUI', u'Removed', u'System', removed.fqdn, u"")
                sactivity = SystemActivity(identity.current.user, u'WEBUI', u'Removed', u'Group', group.display_name, u"")
                group.activity.append(activity)
                system.activity.append(sactivity)
        flash( _(u"%s Removed" % removed.fqdn))
        raise redirect("./edit?id=%s" % group_id)

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, **kw):
        group = Group.by_id(kw['id'])
        session.delete(group)
        activity = Activity(identity.current.user, u'WEBUI', u'Removed', u'Group', group.display_name, u"")
        session.add(activity)
        for system in group.systems:
            SystemActivity(identity.current.user, u'WEBUI', u'Removed', u'Group', group.display_name, u"", object=system)
        flash( _(u"%s deleted") % group.display_name )
        raise redirect(".")

    @expose(format='json')
    def get_group_users(self, group_id=None, *args, **kw):
        try:
            group = Group.by_id(group_id)
        except NoResultFound:
            log.exception('Group id %s is not a valid group id' % group_id)
            response.status = 403
            return ['Invalid Group Id']

        users = group.users
        return [(user.user_id, user.display_name) for user in users]

    @expose(format='json')
    def get_group_systems(self, group_id=None, *args, **kw):
        try:
            group = Group.by_id(group_id)
        except NoResultFound:
            log.exception('Group id %s is not a valid group id' % group_id)
            response.status = 403
            return ['Invalid Group Id']

        systems = group.systems
        return [(system.id, system.fqdn) for system in systems]
