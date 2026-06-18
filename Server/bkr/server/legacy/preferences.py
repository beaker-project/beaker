
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import cherrypy
from turbogears import validators, validate
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.common.bexceptions import BeakerException
from bkr.server.rpc.prefs import Preferences as PreferencesRPC

__all__ = ['Preferences']

# This is just old XMLRPC methods, see user.py for the /prefs/ UI and its HTTP APIs.

class Preferences(RPCRoot, PreferencesRPC):

    exposed = True

    #XMLRPC method for updating user preferences
    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    @validate(validators=dict(email_address=validators.Email()))
    def update(self, email_address=None, tg_errors=None):
        """
        Update user preferences

        :param email_address: email address
        :type email_address: string
        """
        if tg_errors:
            raise BeakerException(', '.join(str(item) for item in tg_errors.values()))
        if email_address:
            if email_address == identity.current.user.email_address:
                raise BeakerException("Email address not changed: new address is same as before")
            else:
                identity.current.user.email_address = email_address

# for sphinx
prefs = Preferences
