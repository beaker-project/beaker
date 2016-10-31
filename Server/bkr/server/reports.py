
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from turbogears import expose, paginate
from sqlalchemy.orm import contains_eager
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.controller_utilities import SearchOptions
from bkr.server.model import System
from bkr.server import search_utility, identity

import pkg_resources
import logging

log = logging.getLogger(__name__)

class Reports(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    extension_controllers = []
    for entry_point in pkg_resources.iter_entry_points('bkr.controllers.reports'):
        controller = entry_point.load()
        log.info('Attaching reports extension controller %s as %s',
                controller, entry_point.name)
        extension_controllers.append(controller)
        locals()[entry_point.name] = controller

    @expose(template="bkr.server.templates.grid")
    @paginate('list', limit=50, default_order='open_reservation.start_time')
    def index(self, *args, **kw):
        return self.reserve(*args, **kw)

    def reserve(self, action='.', *args, **kw):
        from bkr.server.controllers import Root
        default_columns = ('System/Name',
                           'System/Reserved',
                           'System/User',
                           'System/Pools',
                           'System/LoanedTo',)
        return Root()._systems(systems=System.all(identity.current.user)
                               .join('open_reservation')
                               .options(contains_eager(System.open_reservation)),
                               title=u'Reserve Report',
                               default_result_columns=default_columns,
                               *args, **kw)
