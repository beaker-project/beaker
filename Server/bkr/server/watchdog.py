
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, paginate
from sqlalchemy.orm import contains_eager, joinedload_all
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.model import Watchdog, Recipe, RecipeSet, Job, System, RecipeTask
from bkr.server.widgets import myPaginateDataGrid
from datetime import timedelta
import cherrypy

import logging
log = logging.getLogger(__name__)

class Watchdogs(RPCRoot):
    exposed = True

    @expose('bkr.server.templates.grid')
    @paginate('list', limit=50, max_limit=None)
    def index(self, *args, **kw):
        query = Watchdog.by_status(status=u'active')\
                .join(Watchdog.recipe).join(Recipe.recipeset).join(RecipeSet.job)\
                .order_by(Job.id)\
                .options(
                    joinedload_all(Watchdog.recipe, Recipe.recipeset, RecipeSet.job),
                    joinedload_all(Watchdog.recipe, Recipe.recipeset, RecipeSet.lab_controller),
                    joinedload_all(Watchdog.recipetask, RecipeTask.task))

        col = myPaginateDataGrid.Column
        fields = [col(name='job_id', getter=lambda x: x.recipe.recipeset.job.link, title="Job ID"),
                  col(name='system_name', getter=lambda x: x.recipe.resource.link, title="System"),
                  col(name='lab_controller', getter=lambda x: x.recipe.recipeset.lab_controller, title="Lab Controller"),
                  col(name='task_name', getter=lambda x: x.recipetask.name_markup
                        if x.recipetask is not None else None, title="Task Name"),
                  col(name='kill_time', getter=lambda x: x.kill_time,
                      title="Kill Time", options=dict(datetime=True))]

        watchdog_grid = myPaginateDataGrid(fields=fields)
        return dict(title="Watchdogs",
                grid=watchdog_grid,
                search_bar=None,
                list=query)


    # TODO: future cleanup so that the correct error message
    # is given to the client code.
    @identity.require(identity.in_group('admin'))
    @cherrypy.expose
    def extend(self, time):
        '''Allow admins to push watchdog times out after an outage'''

        watchdogs = []
        for w in Watchdog.by_status(status=u'active'):
            n_kill_time = w.kill_time + timedelta(seconds=time)
            watchdogs.append("R:%s watchdog moved from %s to %s" % (
                              w.recipe_id, w.kill_time, n_kill_time))
            w.kill_time = n_kill_time

        if watchdogs:
            return "\n".join(watchdogs)
        else:
            return 'No active watchdogs found'
