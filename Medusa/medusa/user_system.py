from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
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

class UserSystems(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    id           = widgets.HiddenField(name='id')
    system_name   = widgets.TextField(name='system_name', label=_(u'Login'))
    display_name = widgets.TextField(name='display_name', label=_(u'Display Name'))
    password     = widgets.PasswordField(name='password', label=_(u'Password'))

    user_system_form = widgets.TableForm(
        'User System',
        fields = [id, system_name, display_name, password],
        action = 'save_data',
        submit_text = _(u'Save'),
    )

    @expose(template='medusa.templates.form')
    def new(self, **kw):
        return dict(
            form = self.user_system_form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='medusa.templates.form')
    def edit(self, id, **kw):
        user_system = UserSystem.by_id(id)
        return dict(
            form = self.user_system_form,
            action = './save',
            options = {},
            value = user_system,
        )

    @expose()
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('id'):
            user_system = UserSystem.by_id(kw['id'])
        else:
            user_system =  UserSystem()
        user_system.display_name = kw['display_name']
        user_system.system_name = kw['system_name']
        if kw['password'] != user_system.password:
            user_system.password = kw['password']

        flash( _(u"%s saved" % user_system.display_name) )
        redirect(".")

    @expose(template="medusa.templates.grid_add")
    @paginate('list')
    def index(self):
        user_systems = session.query(UserSystem)
        user_systems_grid = widgets.PaginateDataGrid(fields=[
                                  ('Login', lambda x: make_edit_link(x.system_name,x.id)),
                                  ('Display Name', lambda x: x.display_name),
                                  (' ', lambda x: make_remove_link(x.id)),
                              ])
        return dict(title="User Systems", grid = user_systems_grid,
                                         search_bar = None,
                                         list = user_systems)

    @expose()
    def remove(self, **kw):
        user_system = UserSystem.by_id(kw['id'])
        session.delete(user_system)
        flash( _(u"%s Deleted") % user_system.display_name )
        raise redirect(".")
