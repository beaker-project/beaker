
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.model import User
from bkr.common.bexceptions import BX, BeakerException
from bkr.server.rpc import expose, register


@register('prefs')
class Preferences(object):
    # For XMLRPC methods in this class.
    exposed = True

    # XMLRPC interface
    @expose
    @identity.require(identity.not_anonymous())
    def remove_submission_delegate_by_name(self, delegate_name, service=u'XMLRPC'):
        user = identity.current.user
        try:
            submission_delegate = User.by_user_name(delegate_name)
        except NoResultFound:
            raise BX(u'%s is not a valid user name' % delegate_name)
        try:
            user.remove_submission_delegate(submission_delegate, service=service)
        except ValueError:
            raise BX(u'%s is not a submission delegate of %s' % \
                (delegate_name, user))
        return delegate_name

    # XMLRPC Interface
    @expose
    @identity.require(identity.not_anonymous())
    def add_submission_delegate_by_name(self, new_delegate_name,
        service=u'XMLRPC'):
        user = identity.current.user
        new_delegate = User.by_user_name(new_delegate_name)
        if not new_delegate:
            raise BX(u'%s is not a valid user' % new_delegate_name)
        user.add_submission_delegate(new_delegate, service)
        return new_delegate_name

    #XMLRPC method for updating user preferences
    @expose
    @identity.require(identity.not_anonymous())
    def update(self, email_address=None):
        """
        Update user preferences

        :param email_address: email address
        :type email_address: string
        """
        if email_address:
            if email_address == identity.current.user.email_address:
                raise BeakerException("Email address not changed: new address is same as before")
            else:
                identity.current.user.email_address = email_address
