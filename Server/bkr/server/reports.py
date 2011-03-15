from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from sqlalchemy.sql import func
from sqlalchemy.orm import contains_eager
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import SearchBar, myPaginateDataGrid
from bkr.server.controller_utilities import SearchOptions
from bkr.server import search_utility
from distro import Distros

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string
import pkg_resources

# Validation Schemas

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
    @paginate('list',limit=50, default_order='start_time')
    def index(self, *args, **kw):
        return self.reserve(*args, **kw)

    def reserve(self, action='.', *args, **kw): 
        searchvalue = None 
        reserves = System.all(identity.current.user).join('open_reservation')\
                .options(contains_eager(System.open_reservation))
        reserves_return = self._reserves(reserves, **kw)
        search_options = {}
        if reserves_return:
            if 'reserves_found' in reserves_return:
                reserves = reserves_return['reserves_found']
            if 'searchvalue' in reserves_return:
                searchvalue = reserves_return['searchvalue']
            if 'simplesearch' in reserves_return:
                search_options['simplesearch'] = reserves_return['simplesearch']

        search_bar = SearchBar(name='reservesearch',
                               label=_(u'Reserve Search'),
                               table = search_utility.SystemReserve.search.create_search_table(),
                               search_controller=url("./get_search_options_reserve"),
                               )
        reservations = [system.open_reservation for system in reserves]
                               
        reserve_grid = myPaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='system.fqdn', getter=lambda x: make_link(url  = '/view/%s' % x.system.fqdn, text = x.system), title='System', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='start_time', getter=lambda x: x.start_time, title='Reserved Since', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='user', getter=lambda x: x.user, title='Current User', options=dict(sortable=True)),
                              ])

        return dict(title="Reserve Report", 
                    grid = reserve_grid,
                    search_bar = search_bar,
                    options = search_options,
                    action=action, 
                    searchvalue = searchvalue,
                    object_count=len(reservations),
                    list=reservations)

    def _reserves(self,reserve,**kw):
        return_dict = {} 
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['reservesearch'] = [{'table' : 'Name',   
                                   'operation' : 'contains', 
                                   'value' : kw['simplesearch']}]                    
        else:
            simplesearch = None

        return_dict.update({'simplesearch':simplesearch}) 
        if kw.get("reservesearch"):
            searchvalue = kw['reservesearch']  
            reserves_found = self._reserve_search(reserve,**kw)
            return_dict.update({'reserves_found':reserves_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _reserve_search(self,reserve,**kw):
        reserve_search = search_utility.SystemReserve.search(reserve)
        for search in kw['reservesearch']:
            col = search['table'] 
            reserve_search.append_results(search['value'],col,search['operation'],**kw)
        return reserve_search.return_results()

    @expose(format='json')
    def get_search_options_reserve(self,table_field,**kw):
        field = table_field
        search = search_utility.SystemReserve.search.search_on(field)
        col_type = search_utility.SystemReserve.search.field_type(field)
        return SearchOptions.get_search_options_worker(search,col_type)

    default = index
