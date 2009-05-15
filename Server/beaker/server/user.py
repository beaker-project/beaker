from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *

import cherrypy

# from beaker.server import json
# import logging
# log = logging.getLogger("beaker.server.controllers")
#import model
from model import *
import string

class Users(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    user_id     = widgets.HiddenField(name='user_id')
    user_name   = widgets.TextField(name='user_name', label=_(u'Login'))
    display_name = widgets.TextField(name='display_name', label=_(u'Display Name'))
    email_address = widgets.TextField(name='email_address', label=_(u'Email Address'))
    password     = widgets.PasswordField(name='password', label=_(u'Password'))

    user_form = widgets.TableForm(
        'User',
        fields = [user_id, user_name, display_name, email_address, password],
        action = 'save_data',
        submit_text = _(u'Save'),
    )

    @expose(template='beaker.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.user_form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='beaker.server.templates.form')
    def edit(self, id, **kw):
        user = User.by_id(id)
        return dict(
            form = self.user_form,
            action = './save',
            options = {},
            value = user,
        )

    @expose()
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('user_id'):
            user = User.by_id(kw['user_id'])
        else:
            user =  User()
        user.display_name = kw['display_name']
        user.user_name = kw['user_name']
        user.email_address = kw['email_address']
        if kw['password'] != user.password:
            user.password = kw['password']

        flash( _(u"%s saved" % user.display_name) )
        redirect(".")

    @expose(template="beaker.server.templates.grid_add")
    @paginate('list', default_order='user_name')
    def index(self):
        users = session.query(User)
        users_grid = widgets.PaginateDataGrid(fields=[
                                  ('Login', lambda x: make_edit_link(x.user_name,x.user_id)),
                                  ('Display Name', lambda x: x.display_name),
                                  (' ', lambda x: make_remove_link(x.user_id)),
                              ])
        return dict(title="Users", grid = users_grid,
                                         search_bar = None,
                                         list = users)

    @expose()
    def remove(self, id, **kw):
        user = User.by_id(id)
        flash( _(u"%s Deleted") % user.display_name )
        session.delete(user)
        raise redirect(".")

    @expose(format='json')
    def by_name(self, input):
        input = input.lower()
        return dict(matches=User.list_by_name(input))
