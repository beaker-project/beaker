from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from cherrypy import request, response
from kid import Element, XML
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import myPaginateDataGrid, AlphaNavBar, \
    BeakerDataGrid, AutoCompleteField, HorizontalForm
from bkr.server.admin_page import AdminPage
from bkr.server import validators as beaker_validators

import cherrypy

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string


class UserFormSchema(validators.Schema):
    user_id = validators.Int()
    user_name = validators.String(not_empty=True)
    display_name = validators.String(not_empty=True)
    disabled = validators.StringBool(if_empty=False)
    email_address = validators.Email(not_empty=True)
    chained_validators = [beaker_validators.UniqueFormEmail('user_id',
                            'email_address'),
                          beaker_validators.UniqueUserName('user_id',
                            'user_name')]


class Users(AdminPage):
    # For XMLRPC methods in this class.
    exposed = False

    user_id     = widgets.HiddenField(name='user_id')
    user_name   = widgets.TextField(name='user_name', label=_(u'Login'))
    display_name = widgets.TextField(name='display_name', label=_(u'Display Name'))
    email_address = widgets.TextField(name='email_address', label=_(u'Email Address'))
    password     = widgets.PasswordField(name='password', label=_(u'Password'))
    disabled = widgets.CheckBox(name='disabled', label=_(u'Disabled'))
    user_form = HorizontalForm(
        'User',
        fields = [user_id, user_name, display_name,
                  email_address, password, disabled
                 ],
        action = 'save_data',
        submit_text = _(u'Save'),
    )

    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/users/by_name?anywhere=1&ldap=0")
        kw['search_name'] = 'user'
        super(Users,self).__init__(*args,**kw)

        self.search_col = User.user_name
        self.search_mapper = User

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
    @expose(template='bkr.server.templates.user_edit_form')
    def edit(self, id=None, **kw):
        if id:
            user = User.by_id(id)
            title = _(u'User %s') % user.user_name
            value = user
        else:
            user = None
            title = _(u'New user')
            value = kw
        return_vals = dict(form=self.user_form,
                           action='./save',
                           title=title,
                           options={},
                           value=value)
        if id:
            return_vals['groupsgrid'] = self.show_groups()
        else:
            return_vals['groupsgrid'] = None
        return return_vals

    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(user_form, validators=UserFormSchema())
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('user_id'):
            user = User.by_id(kw['user_id'])
        else:
            user =  User()
        user.display_name = kw['display_name']
        user.user_name = kw['user_name']
        user.email_address = kw['email_address']
        if kw.get('disabled') != user.disabled:
            user.disabled = kw.get('disabled')
            if user.disabled:
                self._disable(user, method="WEBUI")
        if kw['password'] != user.password:
            user.password = kw['password']

        flash( _(u"%s saved" % user.display_name) )
        redirect(".")

    def make_remove_link(self, user):
        if user.removed is not None:
            return XML('<a class="btn" href="unremove?id=%s">'
                    '<i class="icon-plus"/> Re-Add</a>' % user.user_id)
        else:
            return XML('<a class="btn" href="remove?id=%s">'
                    '<i class="icon-remove"/> Remove</a>' % user.user_id)

    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list', default_order='user_name',limit=20)
    def index(self,*args,**kw): 
        users = session.query(User) 
        list_by_letters = set([elem.user_name[0].capitalize() for elem in users]) 
        result = self.process_search(**kw)
        if result:
            users = result
        
       
        users_grid = myPaginateDataGrid(fields=[
                                  ('Login', lambda x: make_edit_link(x.user_name,
                                                                     x.user_id)),
                                  ('Display Name', lambda x: x.display_name),
                                  ('Disabled', lambda x: x.disabled),
                                  ('', lambda x: self.make_remove_link(x)),
                              ],
                              add_action='./new')
        return dict(title="Users",
                    grid = users_grid,
                    object_count = users.count(),
                    alpha_nav_bar = AlphaNavBar(list_by_letters,'user'),
                    search_widget = self.search_widget_form,
                    list = users)

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, id, **kw):
        try:
            user = User.by_id(id)
        except InvalidRequestError:
            flash(_(u'Invalid user id %s' % id))
            raise redirect('.')
        flash( _(u'%s Removed') % user.display_name )
        try:
            self._remove(user=user, method='WEBUI')
        except BX, e:
            flash( _(u'Failed to Remove User %s, due to %s' % (user.user_name,
                                                               e
                                                              )
                    )
                 )
        raise redirect('.')

    @identity.require(identity.in_group("admin"))
    @expose()
    def unremove(self, id, **kw):
        try:
            user = User.by_id(id)
        except InvalidRequestError:
            flash(_(u'Invalid user id %s' % id))
            raise redirect('.')
        flash( _(u'%s Re-Added') % user.display_name )
        try:
            self._unremove(user=user)
        except BX, e:
            flash( _(u'Failed to Re-Add User %s, due to %s' % e))
        raise redirect('.')

    @cherrypy.expose
    @identity.require(identity.in_group('admin'))
    def close_account(self, username):
        try:
            user = User.by_user_name(username)
        except InvalidRequestError:
            raise BX(_('Invalid User %s ' % username))
        self._remove(user=user, method='XMLRPC')

    def _disable(self, user, method, 
                 msg='Your account has been temporarily disabled'):
        # cancel all queued and running jobs
        jobs = Job.query.filter(and_(Job.owner==user,
                                    or_(Job.status==TaskStatus.queued,
                                        Job.status==TaskStatus.running
                                           ),
                                       ),
                                  )
        for job in jobs:
            job.cancel(msg=msg)

    def _remove(self, user, method, **kw):
        # Return all systems in use by this user
        if user == identity.current.user:
            raise BX(_('You can''t remove yourself'))
        for system in System.query.filter(System.user==user):
            msg = ''
            try:
                reservation = system.open_reservation
                system.unreserve(reservation=reservation,
                    service=method, user=user)
            except BX, error_msg:
                msg = 'Error: %s Action: %s' % (error_msg,system.release_action)
                system.activity.append(SystemActivity(identity.current.user, method, '%s' % system.release_action, 'Return', '', msg))
                system.activity.append(SystemActivity(identity.current.user, method, 'Returned', 'User', '%s' % user, ''))
        # Return all loaned systems in use by this user
        for system in System.query.filter(System.loaned==user):
            system.activity.append(SystemActivity(identity.current.user, method, 'Changed', 'Loaned To', '%s' % system.loaned, 'None'))
            system.loaned = None
        # Change the owner to the caller
        for system in System.query.filter(System.owner==user):
            system.owner = identity.current.user
            system.activity.append(SystemActivity(identity.current.user, method, 'Changed', 'Owner', '%s' % user, '%s' % identity.current.user))
        # Finally remove the user
        user.removed=datetime.utcnow()

    def _unremove(self, user):
        user.removed = None
        return

    @expose(format='json')
    def by_name(self, input,anywhere=False,ldap=True):
        input = input.lower()
        return dict(matches=User.list_by_name(input,anywhere,ldap))

    def show_groups(self):
        group = ('Group', lambda x: x.display_name)
        return BeakerDataGrid(fields=[group])
