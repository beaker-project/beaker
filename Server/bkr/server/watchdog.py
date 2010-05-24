from turbogears import expose,paginate
from turbogears.database import mapper
from sqlalchemy import select
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.model import Watchdog, LabController, watchdog_table, job_table, task_table, lab_controller_table, system_table, recipe_table, recipe_set_table, recipe_table,recipe_task_table
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.helpers import *

import logging
log = logging.getLogger(__name__)

class Watchdogs(RPCRoot):

    @expose('bkr.server.templates.grid')
    @paginate('list', default_order='job_id', limit=50, allow_limit_override=True)
    def index(self,*args,**kw): 
        s = select([watchdog_table.c.kill_time,
                watchdog_table.c.id,
                job_table.c.id.label('job_id'),
                lab_controller_table.c.fqdn.label('lab_controller'),
                task_table.c.name.label('task_name'),
                task_table.c.id.label('task_id'),
                system_table.c.fqdn.label('system_name')],from_obj=[watchdog_table.join(system_table,watchdog_table.c.system_id == system_table.c.id).
                                                join(lab_controller_table,lab_controller_table.c.id == system_table.c.lab_controller_id).
                                                join(recipe_task_table,recipe_task_table.c.id == watchdog_table.c.recipetask_id).
                                                join(recipe_table, recipe_table.c.id == recipe_task_table.c.recipe_id).
                                                join(recipe_set_table, recipe_set_table.c.id == recipe_table.c.recipe_set_id).
                                                join(job_table, job_table.c.id == recipe_set_table.c.job_id).
                                                join(task_table, task_table.c.id == recipe_task_table.c.task_id)])

        class WatchdogDetails(object):
            pass
        mapper(WatchdogDetails,s)

        queri = WatchdogDetails.query()    
        watchdog = Watchdog.by_status(status='active').join(['recipe','recipeset','job'])
        ids = [elem.id for elem in watchdog]
        queri = queri.filter(WatchdogDetails.id.in_(ids))
        log.debug(queri)  
       
            

        col = myPaginateDataGrid.Column
        fields = [col(name='job_id', getter=lambda x: make_link(url='/jobs/%s' % x.job_id,text=x.job_id), title="Job ID"),
                  col(name='system_name', getter=lambda x: make_link(url= '/view/%s' % x.system_name,text=x.system_name), title="System"),
                  col(name='lab_controller', getter=lambda x: x.lab_controller, title="Lab Controller"),
                  col(name='task_name', getter=lambda x: make_link(url='/tasks/%s' % x.task_id, text=x.task_name), title="Task Name"),
                  col(name='kill_time', getter=lambda x: x.kill_time,title="Kill Time")]
                 

        watchdog_grid = myPaginateDataGrid(fields=fields)
        return dict(title="Watchdog",
                grid=watchdog_grid,
                search_bar=None,
                object_count = queri.count(),
                list=queri)

