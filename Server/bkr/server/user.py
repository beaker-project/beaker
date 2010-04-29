from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import myPaginateDataGrid, UserAlphaNavBar

import cherrypy

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
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

    search_users = AutoCompleteField(name='user', 
                                     search_controller = url("/users/by_name?anywhere=1&ldap=0"),
                                     search_param = "input",
                                     result_name = "matches")
    user_form = widgets.TableForm(
        'User',
        fields = [user_id, user_name, display_name, email_address, password],
        action = 'save_data',
        submit_text = _(u'Save'),
    )


    search_user_form = widgets.TableForm(
        'SearchUser',
        fields = [search_users],
        action = '.',
        submit_text = _(u'Search'),
    )

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.user_form,
            action = './save',
            options = {},
            value = kw,
        )

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def edit(self, id, **kw):
        user = User.by_id(id)
        return dict(
            form = self.user_form,
            action = './save',
            options = {},
            value = user,
        )

    @identity.require(identity.in_group("admin"))
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

    @expose(template="bkr.server.templates.users")
    @paginate('list', default_order='user_name', allow_limit_override=True)
    def index(self,*args,**kw):
        users = session.query(User)
        list_by_letters = []
        for elem in users:
            first_letter = elem.user_name[0]
            list_by_letters.append(first_letter.capitalize()) 
        list_by_letters = set(list_by_letters) 
        if 'user' in kw:
            if 'text' in kw['user']:
                if 'starts_with' in kw['user']['text']:
                    users = session.query(User).filter(User.user_name.like('%s%%' % kw['user']['text']['starts_with']))
                else:
                    users = session.query(User).filter_by(user_name = kw['user']['text'])
        
       
        users_grid = myPaginateDataGrid(fields=[
                                  ('Login', lambda x: make_edit_link(x.user_name,x.user_id)),
                                  ('Display Name', lambda x: x.display_name),
                                  (' ', lambda x: make_remove_link(x.user_id)),
                              ])
        return dict(title="Users",
                    grid = users_grid,
                    object_count = users.count(),
                    alpha_nav_bar = UserAlphaNavBar(list_by_letters),
                    search_users = self.search_user_form,
                    search_bar = None,
                    list = users)

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, id, **kw):
        try:
            user = User.by_id(id)
        except InvalidRequestError:
            flash(_(u'Invalid user id %s' % id))
            raise redirect('.')
        flash( _(u'%s Deleted') % user.display_name )
        self._remove(user=user, method='WEBUI')
        raise redirect('.')

    @cherrypy.expose
    @identity.require(identity.in_group('admin'))
    def close_account(self, username):
        try:
            user = User.by_user_name(username)
        except InvalidRequestError:
            raise BX(_('Invalid User %s ' % username))
        self._remove(user=user, method='XMLRPC')

    def _remove(self, user, method, **kw):
        # Return all systems in use by this user
        for system in System.query().filter(System.user==user):
            msg = ''
            try:
                system.action_release()
            except BX, error_msg:
                msg = 'Error: %s Action: %s' % (error_msg,system.release_action)
                system.activity.append(SystemActivity(identity.current.user, method, '%s' % system.release_action, 'Return', '', msg))
                system.activity.append(SystemActivity(identity.current.user, method, 'Returned', 'User', '%s' % user, ''))
        # Return all loaned systems in use by this user
        for system in System.query().filter(System.loaned==user):
            system.activity.append(SystemActivity(identity.current.user, method, 'Changed', 'Loaned To', '%s' % system.loaned, 'None'))
            system.loaned = None
        # Change the owner to the caller
        for system in System.query().filter(System.owner==user):
            system.owner = identity.current.user
            system.activity.append(SystemActivity(identity.current.user, method, 'Changed', 'Owner', '%s' % user, '%s' % identity.current.user))
        # Finally delete the user
        session.delete(user)

    @expose(format='json')
    def by_name(self, input,anywhere=False,ldap=True):
        input = input.lower()
        return dict(matches=User.list_by_name(input,anywhere,ldap))
