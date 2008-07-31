from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from logan.widgets import myPaginateDataGrid
from logan.xmlrpccontroller import RPCRoot

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

class Recipes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @expose(format='json')
    def to_xml(self, id):
        recipexml = Recipe.by_id(id).to_xml().toxml()
        return dict(xml=recipexml)

    @expose(template='logan.templates.grid')
    @paginate('list',default_order='id')
    def index(self, *args, **kw):
        recipes = session.query(MachineRecipe)
        recipes_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='id', getter=lambda x:x.id, title='ID', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
                    ])
        return dict(title="Recipes", grid=recipes_grid, list=recipes, search_bar=None)
