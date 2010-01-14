from turbogears.database import session
from sqlalchemy import select, distinct
from sqlalchemy.sql.expression import case
from turbogears import controllers, identity, expose
from beaker.server.widgets import JobMatrixReport as JobMatrixWidget
import model

import logging
log = logging.getLogger(__name__)

class JobMatrix: 
    @expose(template='beaker.server.templates.generic')
    def index(self,**kw): 
        jobs = model.Job.query().group_by([model.Job.whiteboard]).distinct()
        new_whiteboard_options = [(job.whiteboard,job.whiteboard) for job in jobs] 
        return dict(widget = JobMatrixWidget(whiteboard_options = new_whiteboard_options), title="Job Matrix Report")

    @expose() 
    def generate(self,**kw): 
        whiteboard_data = {} 
        if 'job_ids' in kw:
            jobs = kw['job_ids'].split()
            recipes = model.Recipe.query().join(['recipeset']).filter(model.RecipeSet.job_id.in_(jobs))
            for recipe in recipes:
                whiteboard_data[recipe.architecture] = recipe.whiteboard 
        elif 'whiteboard' in kw:
            pass
        elif 'project' in kw:
           pass
        else:
           raise BeakerException('Incorrect or no filter passed to job matrix report generator')

        states = { 'Pass' : 0,
                   'Warn' : 1,
                   'Fail' : 2,
                   'Panic' : 3 }
        id_states = {}
        case_states = [] 
        for counter,state in states.iteritems(): 
            case_states.append(case([(model.task_result_table.c.result == state,1)],else_=0).label('rc%s' % counter))
               
            #s = select([model.recipe_task_table.c.id],
            #           from_obj = [model.recipe_task_table.join(model.task_result_table)])                   
          
            #res = s.execute() 
            #result_ids = []
            #for row in res:
            #    result_ids.append(row[0])
            #id_states[state] = result_ids
                        

        #result_pass = model.RecipeTaskResult.query().outerjoin(['result']).filter(model.TaskResult.result == 'Pass') 
        #result_warn = model.RecipeTaskResult.query().outerjoin(['result']).filter(model.TaskResult.result == 'Warn')
        #result_fail = model.RecipeTaskResult.query().outerjoin(['result']).filter(model.TaskResult.result == 'Fail')
        #result_panic = model.RecipeTaskResult.query().outerjoin(['result']).filter(model.RecipeTask.result == 'Panic')
       
