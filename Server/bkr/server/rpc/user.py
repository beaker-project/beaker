
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import cherrypy
from sqlalchemy.exc import InvalidRequestError
from bkr.common.bexceptions import BX
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.model import User
from bkr.server.user import _remove


class Users(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @cherrypy.expose
    @identity.require(identity.in_group('admin'))
    def remove_account(self, username, newowner=None):
        """
        Removes a Beaker user account. When the account is removed:

        * it is removed from all groups and access policies
        * any running jobs owned by the account are cancelled
        * any systems reserved by or loaned to the account are returned
        * any systems and system pools owned by the account are transferred to
          the admin running this command, or some other user if specified using
          the *newowner* parameter
        * the account is disabled for further login

        :param username: An existing username
        :param newowner: An optional username to assign all systems to.
        :type username: string
        """
        kwargs = {}

        try:
            user = User.by_user_name(username)
        except InvalidRequestError:
            raise BX('Invalid User %s ' % username)

        if newowner:
            owner = User.by_user_name(newowner)
            if owner is None:
                raise BX('Invalid user name for owner %s' % newowner)
            kwargs['newowner'] = owner

        if user.removed:
            raise BX('User already removed %s' % username)

        _remove(user=user, method='XMLRPC', **kwargs)
