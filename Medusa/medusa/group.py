from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot
from medusa.helpers import *

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

# Validation Schemas

class GroupFormSchema(validators.Schema):
    display_name = validators.UnicodeString(not_empty=True, max=256, strip=True)
    group_name = validators.UnicodeString(not_empty=True, max=256, strip=True)

class Groups(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    group_id     = widgets.HiddenField(name='group_id')
    display_name = widgets.TextField(name='display_name', label=_(u'Display Name'))
    group_name   = widgets.TextField(name='group_name', label=_(u'Group Name'))
    autoUsers    = AutoCompleteField(name='user', 
                                     search_controller = "/users/by_name",
                                     search_param = "input",
                                     result_name = "matches")
    autoSystems  = AutoCompleteField(name='system', 
                                     search_controller = "/by_fqdn",
                                     search_param = "input",
                                     result_name = "matches")

    group_form = widgets.TableForm(
        'Group',
        fields = [group_id, display_name, group_name],
        action = 'save_data',
        submit_text = _(u'Save'),
        validator = GroupFormSchema()
    )

    group_user_form = widgets.TableForm(
        'GroupUser',
        fields = [group_id, autoUsers],
        action = 'save_data',
        submit_text = _(u'Add'),
    )

    group_system_form = widgets.TableForm(
        'GroupSystem',
        fields = [group_id, autoSystems],
        action = 'save_data',
        submit_text = _(u'Add'),
    )

    @expose(format='json')
    def by_name(self, name):
        name = name.lower()
        search = Group.list_by_name(name)
        groups =  [match.group_name for match in search]
        return dict(groups=groups)
    
    @expose(template='medusa.templates.form')
    def new(self, **kw):
        return dict(
            form = self.group_form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='medusa.templates.group_form')
    def edit(self, id, **kw):
        group = Group.by_id(id)
        
        usergrid = widgets.DataGrid(fields=[
                                  ('User Members', lambda x: x.display_name),
                                  (' ', lambda x: make_link('removeUser?group_id=%s&id=%s' % (id, x.user_id), 'Remove (-)')),
                              ])
        systemgrid = widgets.DataGrid(fields=[
                                  ('System Members', lambda x: x.fqdn),
                                  (' ', lambda x: make_link('removeSystem?group_id=%s&id=%s' % (id, x.id), 'Remove (-)')),
                              ])
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
            disabled_fields = []
        )
    
    @expose()
    @validate(form=group_form)
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('group_id'):
            group = Group.by_id(kw['group_id'])
        else:
            group = Group()
        group.display_name = kw['display_name']
        group.group_name = kw['group_name']

        flash( _(u"OK") )
        redirect(".")

    @expose()
    @error_handler(edit)
    def save_system(self, **kw):
        system = System.by_fqdn(kw['system']['text'],identity.current.user)
        group = Group.by_id(kw['group_id'])
        group.systems.append(system)
        flash( _(u"OK") )
        redirect("./edit?id=%s" % kw['group_id'])

    @expose()
    @error_handler(edit)
    def save_user(self, **kw):
        user = User.by_user_name(kw['user']['text'])
        group = Group.by_id(kw['group_id'])
        group.users.append(user)
        flash( _(u"OK") )
        redirect("./edit?id=%s" % kw['group_id'])

    @expose(template="medusa.templates.grid")
    @paginate('list')
    def index(self):
        groups = session.query(Group)
        groups_grid = widgets.PaginateDataGrid(fields=[
                                  ('Group Name', lambda x: make_edit_link(x.group_name,x.group_id)),
                                  ('Display Name', lambda x: x.display_name),
                                  (' ', lambda x: make_remove_link(x.group_id)),
                              ])
        return dict(title="Groups", grid = groups_grid,
                                         search_bar = None,
                                         list = groups)

    @expose()
    def removeUser(self, group_id=None, id=None, **kw):
        group = Group.by_id(group_id)
        groupUsers = group.users
        for user in groupUsers:
            if user.user_id == int(id):
                group.users.remove(user)
                removed = user
        flash( _(u"%s Removed" % removed.display_name))
        raise redirect("./edit?id=%s" % group_id)

    @expose()
    def removeSystem(self, group_id=None, id=None, **kw):
        group = Group.by_id(group_id)
        groupSystems = group.systems
        for system in groupSystems:
            if system.id == int(id):
                group.systems.remove(system)
                removed = system
        flash( _(u"%s Removed" % removed.fqdn))
        raise redirect("./edit?id=%s" % group_id)

    @expose()
    def remove(self, **kw):
        group = Group.by_id(kw['id'])
        session.delete(group)
        flash( _(u"%s Deleted") % group.display_name )
        raise redirect(".")

    @expose(format='json')
    def get_group_users(self, group_id=None, *args, **kw):
        users = Group.by_id(group_id).users
        return [(user.user_id, user.display_name) for user in users]

    @expose(format='json')
    def get_group_systems(self, group_id=None, *args, **kw):
        systems = Group.by_id(group_id).systems
        return [(system.id, system.fqdn) for system in systems]
