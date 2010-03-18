from turbogears import expose, paginate
from turbogears.database import mapper
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import and_, or_
from beaker.server import model
from beaker.server.widgets import TaskList as TaskListWidget

import logging
log = logging.getLogger(__name__)

class TaskList:

    widget = TaskListWidget() 
    @expose(template='beaker.server.templates.generic')
    @paginate('widget_options') #Ideally I want to find out how to paginate elements of the return dict
    def index(self,**kw):
     
        my_exp = [] 
        if 'task_name' in kw:
            if kw['task_name']:
                log.debug('Task name: %s' % kw['task_name'])
                my_exp.append(model.task_table.c.name == kw['task_name']) 
        if 'result' in kw:
            if kw['result']: 
                log.debug('Result: %s' % kw['result'])
                my_exp.append(model.task_result_table.c.result == kw['result'])
        if 'whiteboard' in kw:
            if kw['whiteboard']:
                log.debug('Whiteboard: %s' % kw['whiteboard'])
                my_exp.append(model.recipe_table.c.whiteboard == kw['whiteboard']) 
            else:
                log.debug('Whiteboard: %s' % kw['whiteboard'])
                my_exp.append(or_(model.recipe_table.c.whiteboard ==  None,model.recipe_table.c.whiteboard == '')) 
        if 'arch' in kw:
            if kw['arch']:  
                my_exp.append(model.arch_table.c.arch == kw['arch'])
        if 'job_id' in kw:
            if kw['job_id']: 
                my_exp.append(model.recipe_set_table.c.job_id.in_(kw['job_id']))
            
        my_select   = [model.recipe_task_table.c.id,
                       model.recipe_task_table.c.recipe_id,
                       model.recipe_set_table.c.job_id, 
                       model.distro_table.c.name.label('distro_name'),
                       model.osmajor_table.c.osmajor.label('family'),
                       model.distro_table.c.variant,
                       model.arch_table.c.arch,
                       model.system_table.c.fqdn.label('system_name'),
                       model.task_table.c.name.label('task_name'),
                       model.task_table.c.path.label('task_path'),
                       model.task_table.c.avg_time,
                       func.timediff(model.recipe_task_table.c.finish_time,model.recipe_task_table.c.start_time).label('duration'),
                       model.recipe_task_table.c.start_time,                       
                       model.task_status_table.c.status,
                       model.task_result_table.c.result] 
        my_from = [model.recipe_table.join(model.recipe_set_table).
                                 join(model.recipe_task_table, model.recipe_table.c.id == model.recipe_task_table.c.recipe_id).
                                 join(model.task_table, model.recipe_task_table.c.task_id == model.task_table.c.id).
                                 join(model.distro_table, model.recipe_table.c.distro_id == model.distro_table.c.id).
                                 join(model.osversion_table.join(model.osmajor_table)).
                                 outerjoin(model.system_table, model.recipe_table.c.system_id == model.system_table.c.id). 
                                 join(model.arch_table, model.distro_table.c.arch_id == model.arch_table.c.id).
                                 join(model.task_status_table, model.recipe_table.c.status_id == model.task_status_table.c.id).
                                 join(model.task_result_table, model.recipe_task_table.c.result_id == model.task_result_table.c.id)]             
            
        s1 = select(my_select, from_obj=my_from,whereclause=and_(*my_exp))
       
        class Mappable(object):
            pass
        mapper(Mappable,s1)
        dyn = Mappable.query()
        return_data = () 
        for d in dyn: 
            recipe_result = model.RecipeTaskResult.query().filter(model.RecipeTaskResult.recipe_task_id == d.id)    
            return_data += ((d,recipe_result),)
       
        return dict(widget=self.widget, title='Task List', widget_options=return_data )


