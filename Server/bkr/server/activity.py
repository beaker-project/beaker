from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate,url
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import SearchBar, myPaginateDataGrid
from bkr.server import search_utility
from bkr.server.util import any
import cherrypy

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class Activities(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    def activities(self,activity,**kw): 
        return_dict = {}                    
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['activitysearch'] = [{'table' : 'Property',   
                                     'operation' : 'contains', 
                                     'value' : kw['simplesearch']}]                    
        else:
            simplesearch = None

        return_dict.update({'simplesearch':simplesearch})

        if kw.get("activitysearch"):
            searchvalue = kw['activitysearch']  
            activities_found = self._activity_search(activity,**kw)
            return_dict.update({'activities_found':activities_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _activity_search(self,activity,**kw):
        activity_search = search_utility.Activity.search(activity)
        for search in kw['activitysearch']:
            col = search['table'] 
            activity_search.append_results(search['value'],col,search['operation'],**kw)
        return activity_search.return_results()

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='-created', limit=50)
    def index(self,**kw):
        # This seems kind of dodgy...
        if any(search['table'].startswith('System/')
                for search in kw.get('activitysearch', [])):
            activity = SystemActivity.all()
        elif any(search['table'].startswith('Distro/')
                for search in kw.get('activitysearch', [])):
            activity = DistroActivity.all()
        else:
            activity = Activity.all()
        activities_return = self.activities(activity,**kw)
        searchvalue = None
        search_options = {}
        if activities_return:
            if 'activities_found' in activities_return:
                activity = activities_return['activities_found']
            if 'searchvalue' in activities_return:
                searchvalue = activities_return['searchvalue']
            if 'simplesearch' in activities_return:
                search_options['simplesearch'] = activities_return['simplesearch']
          
        activity_grid = myPaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='user.user_name', getter=lambda x: x.user, title='User', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='service', getter=lambda x: x.service, title='Via', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='created',
                                    getter=lambda x: x.created, title='Date',
                                    options=dict(sortable=True, datetime=True)),
                                  widgets.PaginateDataGrid.Column(name='object_name', getter=lambda x: x.object_name(), title='Object', options=dict(sortable=False)),
                                  widgets.PaginateDataGrid.Column(name='field_name', getter=lambda x: x.field_name, title='Property', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='action', getter=lambda x: x.action, title='Action', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='old_value', getter=lambda x: x.old_value, title='Old Value', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='new_value', getter=lambda x: x.new_value, title='New Value', options=dict(sortable=True)),
                              ])
        
        self.search_bar = SearchBar(name='activitysearch',
                           label=_(u'Activity Search'),
                           table = search_utility.Activity.search.create_search_table(),
                           complete_data = search_utility.Activity.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_activity"), 
                           )
       
        return dict(title="Activity", 
                    grid = activity_grid,
                    object_count = activity.count(),
                    search_bar = self.search_bar,
                    searchvalue = searchvalue,
                    action = '.',
                    options = search_options,
                    list = activity)
    default = index
