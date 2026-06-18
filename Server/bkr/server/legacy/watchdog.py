
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, paginate
from sqlalchemy.orm import joinedload_all
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.model import Watchdog, Recipe, RecipeSet, Job, RecipeTask
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.rpc.watchdogs import Watchdogs as WatchdogsRPC

import logging
log = logging.getLogger(__name__)

class Watchdogs(RPCRoot, WatchdogsRPC):
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
