from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot
from medusa.helpers import *
from medusa.needpropertyxml import *

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

# Validation Schemas

class Distros(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @expose(template="medusa.templates.grid")
    @paginate('list',default_order='-date_created', limit=50,allow_limit_override=True)
    def index(self):
        distros = session.query(Distro)
        distros_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='install_name', getter=lambda x: x.install_name, title='Install Name', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='name', getter=lambda x: x.name, title='Name', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='breed', getter=lambda x: x.breed, title='Breed', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='osversion', getter=lambda x: x.osversion, title='OS Version', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='variant', getter=lambda x: x.variant, title='Variant', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='virt', getter=lambda x: x.virt, title='Virt', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='arch', getter=lambda x: x.arch, title='Arch', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='method', getter=lambda x: x.method, title='Method', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='date_created', getter=lambda x: x.date_created, title='Date Created', options=dict(sortable=True)),
                              ])
        return dict(title="Distros", grid = distros_grid,
                                         search_bar = None,
                                         list = distros)

    @cherrypy.expose
    def pick(self, xml):
        """
        Based on XML passed in filter distro selection
        """
        #FIXME Should validate XML before proceeding.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(xml)):
            if callable(getattr(child, 'filter')):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        distros = Distro.query()
        if joins:
            distros = distros.filter(and_(*joins))
        if queries:
            distros = distros.filter(and_(*queries))
        distro = distros.first()
        return dict(distro    = distro.install_name,
                    family    = '%s' % distro.osversion,
                    variant   = distro.variant,
                    tree_path = distro.install_name)

    default = index
