from turbogears.database import session
from sqlalchemy import select, distinct
from turbogears import controllers, identity, expose
from beaker.server.widgets import JobMatrixReport as JobMatrixWidget
from beaker.server.model import Job
class JobMatrix: 
    @expose(template='beaker.server.templates.generic')
    def index(self,**kw): 
        jobs = Job.query().group_by([Job.whiteboard]).distinct()
        new_whiteboard_options = [(job.whiteboard,job.whiteboard) for job in jobs] 
        return dict(widget = JobMatrixWidget(whiteboard_options = new_whiteboard_options), title="Job Matrix Report")
   
    def generate(self,**kw):
        if 'job_ids' in kw:
            jobs = job_ids.split("\n")
        elif 'whiteboard' in kw:
            pass
        elif 'project' in kw:
           pass
        else:
           raise BeakerException('Incorrect or no filter passed to job matrix report generator')
     
       
        
    

