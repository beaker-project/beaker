
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, widgets, paginate
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import SearchBar, myPaginateDataGrid
from bkr.server import search_utility

from bkr.server.model import (Activity,
                              DistroActivity, DistroTreeActivity,
                              LabControllerActivity, SystemActivity,
                              GroupActivity)


class Activities(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    def activities(self, activity_search, **kw):
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
            activities_found = self._activity_search(activity_search, **kw)
            return_dict.update({'activities_found':activities_found})
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _activity_search(self, activity_search, **kw):
        for search in kw['activitysearch']:
            col = search['table']
            activity_search.append_results(search['value'], col, search['operation'], **kw)
        return activity_search.return_results()

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-created', limit=50)
    def distrotree(self, **kw):
        activities = DistroTreeActivity.all()
        activity_search = search_utility.DistroTreeActivity.search
        search_bar = SearchBar(activity_search.create_search_table(),
                               name='activitysearch',
                               complete_data=activity_search. \
                                             create_complete_search_table(),)
        return self._activities_grid(activities, search_bar, 'distrotree',
            search_utility.DistroTreeActivity, title='Distro Tree Activity', **kw)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-created', limit=50)
    def labcontroller(self, **kw):
        activities = LabControllerActivity.all()
        activity_search = search_utility.LabControllerActivity.search
        search_bar = SearchBar(activity_search.create_search_table(),
                               name='activitysearch',
                               complete_data = activity_search. \
                                               create_complete_search_table(),)
        return self._activities_grid(activities, search_bar, 'labcontroller',
            search_utility.LabControllerActivity,
            title='Lab Controller Activity', **kw)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-created', limit=50)
    def group(self, **kw):
        activities = GroupActivity.all()
        activity_search = search_utility.GroupActivity.search
        search_bar = SearchBar(activity_search.create_search_table(),
                               name='activitysearch',
                               complete_data = activity_search. \
                                               create_complete_search_table(),)
        return self._activities_grid(activities, search_bar, 'group',
            search_utility.GroupActivity, title='Group Activity', **kw)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-created', limit=50)
    def system(self, **kw):
        activities = SystemActivity.all()
        activity_search = search_utility.SystemActivity.search
        search_bar = SearchBar(activity_search.create_search_table(),
                               name='activitysearch',
                               complete_data = activity_search. \
                                               create_complete_search_table(),)
        return self._activities_grid(activities, search_bar, 'system',
            search_utility.SystemActivity, title='System Activity', **kw)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-created', limit=50)
    def distro(self, **kw):
        activities = DistroActivity.all()
        activity_search = search_utility.DistroActivity.search
        search_bar = SearchBar(activity_search.create_search_table(),
                               name='activitysearch',
                               complete_data = activity_search. \
                                               create_complete_search_table(),)
        return self._activities_grid(activities, search_bar, 'distro',
            search_utility.DistroActivity, title='Distro Activity', **kw)

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-created', limit=50)
    def index(self, **kw):
        activities = Activity.all()
        activity_search = search_utility.Activity.search
        search_bar = SearchBar(activity_search.create_search_table(),
                               name='activitysearch',
                               complete_data = activity_search. \
                                               create_complete_search_table(),)
        return self._activities_grid(activities, search_bar, '.',
            search_utility.Activity, **kw)

    def _activities_grid(self, activities, search_bar, action, searcher, \
        title='Activity', **kw):
        activity_search = searcher.search(activities)
        activities_return = self.activities(activity_search, **kw)
        searchvalue = None
        search_options = {}
        if activities_return:
            if 'activities_found' in activities_return:
                activities = activities_return['activities_found']
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

        return dict(title=title,
                    grid = activity_grid,
                    search_bar = search_bar,
                    searchvalue = searchvalue,
                    action = action,
                    options = search_options,
                    list = activities)
    default = index
