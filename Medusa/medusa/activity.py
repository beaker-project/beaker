from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
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

# Validation Schemas

class Activities(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    @expose(template="medusa.templates.grid")
    @paginate('list',default_order='-created', max_limit=50, limit=50,allow_limit_override=True)
    def index(self):
        activity = Activity.all().outerjoin('user')
        activity_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='user.user_name', getter=lambda x: x.user, title='User', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='service', getter=lambda x: x.service, title='Via', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='created', getter=lambda x: x.created, title='Date', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='object_name', getter=lambda x: x.object_name(), title='Object', options=dict(sortable=False)),
                                  widgets.PaginateDataGrid.Column(name='field_name', getter=lambda x: x.field_name, title='Property', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='action', getter=lambda x: x.action, title='Action', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='old_value', getter=lambda x: x.old_value, title='Old Value', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='new_value', getter=lambda x: x.new_value, title='New Value', options=dict(sortable=True)),
                              ])
        return dict(title="Activity", grid = activity_grid,
                                         search_bar = None,
                                         list = activity)
    default = index
