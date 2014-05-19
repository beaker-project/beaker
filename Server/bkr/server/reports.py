
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from turbogears import expose, widgets, paginate, url
from sqlalchemy.orm import contains_eager
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link
from bkr.server.widgets import SearchBar, myPaginateDataGrid
from bkr.server.controller_utilities import SearchOptions
from bkr.server.model import System
from bkr.server import search_utility, identity
from bkr.server.external_reports import ExternalReportsController

import pkg_resources
import logging

log = logging.getLogger(__name__)

def datetime_range(start, stop, step):
    dt = start
    while dt < stop:
        yield dt
        dt += step

def js_datetime(dt):
    """
    Returns the given datetime in so-called JavaScript datetime format (ms 
    since epoch).
    """
    return int(dt.strftime('%s')) * 1000 + dt.microsecond // 1000

def datetime_from_js(s):
    """
    Takes ms since epoch and returns a datetime.
    """
    if isinstance(s, basestring):
        s = float(s)
    return datetime.datetime.fromtimestamp(s / 1000)

class Reports(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True
    external = ExternalReportsController()

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
                               table = search_utility.SystemReserve.search.create_complete_search_table(),
                               search_controller=url("./get_search_options_reserve"),
                               )
        reservations = [system.open_reservation for system in reserves]
                               
        reserve_grid = myPaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='system.fqdn', getter=lambda x: make_link(url  = '/view/%s' % x.system.fqdn, text = x.system), title=u'System', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='start_time',
                                    getter=lambda x: x.start_time,
                                    title=u'Reserved Since',
                                    options=dict(sortable=True, datetime=True)),
                                  widgets.PaginateDataGrid.Column(name='user', getter=lambda x: x.user, title=u'Current User', options=dict(sortable=True)),
                              ])

        return dict(title=u"Reserve Report",
                    grid = reserve_grid,
                    search_bar = search_bar,
                    options = search_options,
                    action=action, 
                    searchvalue = searchvalue,
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
