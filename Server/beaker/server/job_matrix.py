from sqlalchemy import select, distinct, Table, Column, Integer, String
from sqlalchemy.sql.expression import case, func, and_, bindparam
from turbogears import controllers, identity, expose, url, database
from turbogears.database import session, metadata, mapper
from turbogears.widgets import DataGrid, AjaxGrid
from beaker.server.widgets import JobMatrixReport as JobMatrixWidget

import model

import logging
log = logging.getLogger(__name__)

class JobMatrix: 
    job_matrix_widget = JobMatrixWidget()
    @expose(template='beaker.server.templates.generic')
    def index(self,**kw):    
        matrix_options = {} 
        jobs = model.Job.query().group_by([model.Job.whiteboard])
        new_whiteboard_options = [(job.whiteboard,job.whiteboard) for job in jobs]  
        matrix_options['whiteboard_options'] = new_whiteboard_options 
        #log.debug(kw)
        if ('job_ids' in kw) or ('whiteboard' in kw): 
            #log.debug('in if clause')
            gen_results = self.generate(**kw) 
            matrix_options['grid'] = gen_results['grid']
            matrix_options['list'] = gen_results['data'] 
            if 'whiteboard' in kw:
                matrix_options['job_ids_options'] = model.Job.by_whiteboard(kw['whiteboard'])  
        else: 
            pass         
        log.debug('Matrix options is %s ' % matrix_options)
        return dict(widget = self.job_matrix_widget,widget_options=matrix_options, title="Job Matrix Report")
     
    #def _build_grid(self,data,**kw):
    #    all_arch = model.Arch.query()
    #    for arch in all_arch:
    @classmethod
    def arch_stat_getter(cls,x):
      s = 'Pass:%s Fail:%s Warn:%s' % (x.Pass,x.Fail,x.Warn) 
      return s
 
    def _job_grid_fields(self,**kw):
        fields = [DataGrid.Column(name='task', getter=lambda x: x.task_name, title='Task'),
                  DataGrid.Column(name='i386', getter=lambda x: JobMatrix.arch_stat_getter(x), title='i386') ]
        return fields 
 
    
    def generate(self,**kw):
        grid_data = self.generate_data(**kw)
        grid = DataGrid(fields = self._job_grid_fields())
        return {'grid' : grid, 'data' : grid_data }     
      
   
    def generate_data(self,**kw): 
        jobs = []
        whiteboard_data = {} 
        if 'job_ids' in kw:
            jobs = kw['job_ids'].split() 
        elif 'whiteboard' in kw:
            job_query = model.Job.query().filter(model.Job.whiteboard == kw['whiteboard'])
            for job in job_query:
                jobs.append(job.id) 
        else:
           pass
           #raise AssertionError('Incorrect or no filter passed to job matrix report generator')
        recipes = model.MachineRecipe.query().join(['distro','arch']).join(['recipeset','job']).add_column(model.Arch.arch) 
        #recipes = model.MachineRecipe.query().join(['distro','arch']).join(['recipeset','job']).filter(model.RecipeSet.job_id.in_(jobs)).add_column(model.Arch.arch) 
        #log.debug(recipes)
        for recipe,arch in recipes:     
            whiteboard_data[arch] = recipe.whiteboard 

        case0 = case([(model.task_result_table.c.result == 'New',1)],else_=0)
        case1 = case([(model.task_result_table.c.result == 'Pass',1)],else_=0)
        case2 = case([(model.task_result_table.c.result == 'Warn',1)],else_=0)
        case3 = case([(model.task_result_table.c.result == 'Fail',1)],else_=0)
        case4 = case([(model.task_result_table.c.result == 'Panic',1)],else_=0) 
        #need to test for jobs array before adding where clause
        arch_alias = model.arch_table.alias()
        recipe_table_alias = model.recipe_table.alias()
        s2 = select([model.task_table.c.id.label('task_id'),
                     model.task_result_table.c.id.label('result'),
                     recipe_table_alias.c.whiteboard.label('recipe_whiteboard'),
                     arch_alias.c.arch.label('arch_arch'),
                     case0.label('rc0'),
                     case1.label('rc1'),
                     case2.label('rc2'),
                     case3.label('rc3'),
                     case4.label('rc4')],
                   
                     and_(model.recipe_set_table.c.job_id.in_(jobs),
                          model.task_result_table.c.id == recipe_table_alias.c.result_id,
                          recipe_table_alias.c.id == model.recipe_task_table.c.recipe_id,
                          recipe_table_alias.c.distro_id == model.distro_table.c.id), 
                          #arch_alias.c.arch == bindparam('arch'), 
                          #recipe_table_alias.c.whiteboard == bindparam('whiteboard')),
                          
                        
                     from_obj=[model.task_result_table,
                               model.distro_table.join(arch_alias),
                               model.recipe_set_table.join(recipe_table_alias),
                               model.task_table.join(model.recipe_task_table)]).alias('foo')

        #If this query starts to bog down and slow up, we really should create a view for the inner select (s2)
        #SQLAlchemy Select object does not really support this, you would have to use SQLAlchemy text for s2, and then
        #build a specific table for it.

        #eng = database.get_engine()
        #c = s2.compile(eng) 
        #eng.execute("CREATE VIEW foobar AS %s" % s2.compile(eng)) 
       
      
       
      
        s1 = select([func.count(s2.c.result),
                     func.sum(s2.c.rc0).label('New'),
                     func.sum(s2.c.rc1).label('Pass'),
                     func.sum(s2.c.rc2).label('Warn'),
                     func.sum(s2.c.rc3).label('Fail'),
                     func.sum(s2.c.rc4).label('Panic'),
                     model.task_table.c.name.label('task_name'),
                     s2.c.arch_arch,
                     s2.c.recipe_whiteboard,
                     s2.c.task_id.label('task_id_pk')],
                     s2.c.task_id == model.task_table.c.id,
                     
                     from_obj=[model.task_table,s2]).group_by(model.task_table.c.name).order_by(model.task_table.c.name)
       
       

        class InnerDynamo(object):
            
            def __init__(self, new=None, pass_=None, warn=None, fail=None,
                         panic=None, task_name=None, arch_arch=None, recipe_whiteboard=None,
                         task_id_pk=None):
                self.New = new
                self.Pass = pass_
		self.Warn = warn
		self.Fail = fail
		self.Panic = panic
		self.task_name = task_name
		self.arch_arch = arch_arch
	        self.recipe_whiteboard = recipe_whiteboard
	        self.task_id_pk = task_id_pk

        mapper(InnerDynamo,s1)
          
        #mapper(OuterDynamo,
        #log.debug(s1)
        #log.debug(whiteboard_data)
        result_data = []
       
        for arch_val,whiteboard_val in whiteboard_data.iteritems():  
            log.debug('Arch is %s and whiteboard is %s' % (arch_val,whiteboard_val))
            dyn = InnerDynamo.query().filter_by(recipe_whiteboard=whiteboard_val)
            dyn = dyn.filter_by(arch_arch=arch_val)   
            for d in dyn:
                log.debug('d is %s %s %s %s %s' % (d.arch_arch,d.New, d.Pass, d.Fail, d.task_name) )
                
                result_data.append(d)
         
            #dyn = InnerDynamo.query()
            #log.debug('type is %s' % type(InnerDynamo.query()))
            #result_data.append(InnerDynamo.query())
        return result_data
      
       
