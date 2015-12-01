
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import (expose, widgets, flash, error_handler,
                        validate, validators, redirect, paginate, url)
from sqlalchemy import and_, or_
from sqlalchemy.exc import InvalidRequestError
from kid import XML
from bkr.common.bexceptions import BX
from flask import request, jsonify
from bkr.server import identity
from bkr.server.helpers import make_edit_link
from bkr.server.widgets import myPaginateDataGrid, AlphaNavBar, \
    BeakerDataGrid, HorizontalForm
from bkr.server.admin_page import AdminPage
from bkr.server.app import app
from bkr.server import validators as beaker_validators
from sqlalchemy import and_

import cherrypy
from datetime import datetime

from bkr.server.model import User, Job, System, SystemActivity, TaskStatus, \
    SystemAccessPolicyRule


class UserFormSchema(validators.Schema):
    user_id = validators.Int()
    user_name = validators.UnicodeString(not_empty=True, strip=True)
    display_name = validators.UnicodeString(not_empty=True, strip=True)
    disabled = validators.StringBool(if_empty=False)
    email_address = validators.Email(not_empty=True, strip=True)
    chained_validators = [beaker_validators.UniqueUserName('user_id',
                            'user_name')]


class Users(AdminPage):
    # For XMLRPC methods in this class.
    exposed = True

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
            session.add(user)
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
                    '<i class="fa fa-plus"/> Re-Add</a>' % user.user_id)
        else:
            return XML('<a class="btn" href="remove?id=%s">'
                    '<i class="fa fa-times"/> Remove</a>' % user.user_id)

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
        try:
            self._remove(user=user, method='WEBUI')
        except BX, e:
            flash( _(u'Failed to remove User %s, due to %s' % (user.user_name, e)))
            raise redirect('.')
        else:
            flash( _(u'User %s removed') % user.user_name )
            redirect('.')

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
    def remove_account(self, username, newowner=None):
        """
        Removes a Beaker user account. When the account is removed:

        * it is removed from all groups and access policies
        * any running jobs owned by the account are cancelled
        * any systems reserved by or loaned to the account are returned
        * any systems owned by the account are transferred to the admin running this 
          command, or some other user if specified using the *newowner* parameter
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

        self._remove(user=user, method='XMLRPC', **kwargs)

    def _disable(self, user, method,
                 msg='Your account has been temporarily disabled'):

        # cancel all queued and running jobs
        Job.cancel_jobs_by_user(user, msg)

    def _remove(self, user, method, **kw):
        if user == identity.current.user:
            raise BX(_('You cannot remove yourself'))

        # cancel all running and queued jobs
        Job.cancel_jobs_by_user(user, 'User %s removed' % user.user_name)

        # Return all systems in use by this user
        for system in System.query.filter(System.user==user):
            reservation = system.open_reservation
            system.unreserve(reservation=reservation, service=method, user=user)
        # Return all loaned systems in use by this user
        for system in System.query.filter(System.loaned==user):
            system.record_activity(user=identity.current.user, service=method,
                    action=u'Changed', field=u'Loaned To',
                    old=u'%s' % system.loaned, new=u'None')
            system.loaned = None
        # Remove the user from all system access policies
        for rule in SystemAccessPolicyRule.query.filter_by(user=user):
            rule.record_deletion(service=method)
            session.delete(rule)
        # Change the owner to the caller
        newowner = kw.get('newowner', identity.current.user)
        for system in System.query.filter(System.owner==user):
            system.owner = newowner
            system.record_activity(user=identity.current.user, service=method,
                    action=u'Changed', field=u'Owner',
                                   old=u'%s' % user, new=u'%s' % newowner)
        # Remove the user from all groups
        for group in user.groups:
            group.remove_member(user=user,
                    agent=identity.current.user, service=method)
        # Finally remove the user
        user.removed=datetime.utcnow()

    def _unremove(self, user):
        user.removed = None
        return

    @expose(format='json')
    def by_name(self, input,anywhere=False,ldap=True):
        input = input.lower()
        matches = [user_name for user_name, display_name
                in User.list_by_name(input, anywhere, ldap)]
        return dict(matches=matches)

    def show_groups(self):
        group = ('Group', lambda x: x.display_name)
        return BeakerDataGrid(fields=[group])

@app.route('/users/+typeahead')
def users_typeahead():
    if 'q' in request.args:
        ldap = (len(request.args['q']) >= 3) # be nice to the LDAP server
        users = User.list_by_name(request.args['q'],
                find_anywhere=False, find_ldap_users=ldap)
    else:
        # not sure if this is wise, the response may be several hundred KB...
        users = User.query.filter(User.removed == None)\
                .values(User.user_name, User.display_name)
    data = [{'user_name': user_name, 'display_name': display_name,
             'tokens': [user_name]}
            for user_name, display_name in users]
    return jsonify(data=data)

# for sphinx
users = Users
