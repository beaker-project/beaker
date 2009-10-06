from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *
from distro import Distros

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from beaker.server import json
# import logging
# log = logging.getLogger("beaker.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class Reports(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @expose(template="beaker.server.templates.grid")
    @paginate('list',default_order='created',limit=50,allow_limit_override=True)
    def reserve(self):
        activity = []
        for system in System.all(identity.current.user).filter(System.user!=None):
            # Build a list of the last Reserve entry for each system
            try:
                activity.append(SystemActivity.query().filter(
                     and_(SystemActivity.object==system,
                          SystemActivity.field_name=='User',
                          SystemActivity.action=='Reserved'
                         )).order_by(SystemActivity.created.desc())[0])
            except IndexError:
                # due to an old bug, we may not have a Reserved action
                pass  

        reserve_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='object.fqdn', getter=lambda x: make_link(url  = '/view/%s' % x.object,
                                  text = x.object), title='System', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='created', getter=lambda x: x.created, 
                                  title='Reserved Since', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='user', getter=lambda x: x.user, 
                                  title='Current User', options=dict(sortable=True)),
                              ])
        return dict(title="Reserve Report", grid = reserve_grid,
                                         search_bar = None,
                                         list = activity)

    default = reserve
