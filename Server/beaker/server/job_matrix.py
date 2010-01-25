from sqlalchemy import select, distinct, Table, Column, Integer, String
from sqlalchemy.sql.expression import case, func, and_, bindparam
from turbogears import controllers, identity, expose, url, database
from turbogears.database import session, metadata, mapper
from kid import Element, SubElement
from beaker.server.widgets import JobMatrixReport as JobMatrixWidget, myDataGrid

import model

import logging
log = logging.getLogger(__name__)

class JobMatrix: 
    job_matrix_widget = JobMatrixWidget() 
    arches_used = {}

    @expose(template='beaker.server.templates.generic')
    def index(self,**kw):    
        matrix_options = {} 
        if 'whiteboard_filter' in kw:
            filter = kw['whiteboard_filter']
        else:
            filter = None 

        whiteboard_options =  self.get_whiteboard_options(filter)
        # This is silly, I can't call get_whiteboard_options from here because it's always
        # returning JSON. Even though I only have the allow_json=True on, it should otherwise
        # give me regular returns if I'm not sending tg_format='json'. I've had to create
        # get_whiteboard_options_json 
        
        whiteboard_options = [(w[0],w[0]) for w in whiteboard_options]  # I want tuples
        matrix_options['whiteboard_options'] = self.get_whiteboard_options(filter)

        if ('job_ids' in kw) or ('whiteboard' in kw): 
            gen_results = self.generate(**kw) 
            matrix_options['grid'] = gen_results['grid']
            matrix_options['list'] = gen_results['data'] 
            if 'whiteboard' in kw:
                jobs = model.Job.by_whiteboard(kw['whiteboard'])  
                job_ids = [str(j.id) for j in jobs]
                matrix_options['job_ids_vals'] = "\n".join(job_ids)
            if 'job_ids' in kw:
                matrix_options['job_ids_vals'] = kw['job_ids']
        else: 
            matrix_options['grid'] = None 
       
        return dict(widget = self.job_matrix_widget,widget_options=matrix_options, title="Job Matrix Report") 

    @expose(format='json')
    def get_whiteboard_options_json(self,filter):
        return_dict = {}
        return_dict['options'] =  self.get_whiteboard_options(filter)
        return return_dict

    def get_whiteboard_options(self,filter):
        if filter: 
            where = model.job_table.c.whiteboard.like('%%%s%%' % filter)   
        else:
            where = None
        s1 = select([model.job_table.c.whiteboard],whereclause=where,group_by=[model.job_table.c.whiteboard,model.job_table.c.id],order_by=[model.job_table.c.id],distinct=True,limit=50)  
        res = s1.execute()  
        a = [r[0] for r in res]
        return a 
        
    @classmethod
    def arch_stat_getter(cls,this_arch):
      #ahh nice little closure...
      def f(x):
          for elem in x:
              val = getattr(elem,'arch',None)
              if val is not None:
                  if val == this_arch:
                      return_text =  cls.make_result_box('New Pass Warn Fail Panic',elem)
                      return return_text
      return f      
    @classmethod
    def _job_grid_fields(self,arches_used,**kw):
        fields = [] 
        fields.append(myDataGrid.Column(name='task', getter=lambda x: x[0], title='Task')) 
         
        for arch in arches_used:
            fields.append(myDataGrid.Column(name=arch, getter=JobMatrix.arch_stat_getter(arch), title=arch))
        return fields 
 
    def generate(self,**kw):
        grid_data = self.generate_data(**kw)  
        grid = myDataGrid(fields = self._job_grid_fields(self.arches_used.keys()))
        return {'grid' : grid, 'data' : grid_data }     
       
    def generate_data(self,**kw): 
        jobs = []
        self.arches_used = {}
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
        #recipes = model.MachineRecipe.query().join(['distro','arch']).join(['recipeset','job']).add_column(model.Arch.arch) 
        recipes = model.MachineRecipe.query().join(['distro','arch']).join(['recipeset','job']).filter(model.RecipeSet.job_id.in_(jobs)).add_column(model.Arch.arch) 
        #log.debug(recipes)
        for recipe,arch in recipes:     
            whiteboard_data[arch] = recipe.whiteboard 

        case0 = case([(model.task_result_table.c.result == u'New',1)],else_=0)
        case1 = case([(model.task_result_table.c.result == u'Pass',1)],else_=0)
        case2 = case([(model.task_result_table.c.result == u'Warn',1)],else_=0)
        case3 = case([(model.task_result_table.c.result == u'Fail',1)],else_=0)
        case4 = case([(model.task_result_table.c.result == u'Panic',1)],else_=0) 
    
        arch_alias = model.arch_table.alias()
        recipe_table_alias = model.recipe_table.alias()
        my_select = [model.task_table.c.id.label('task_id'),
                     model.task_result_table.c.id.label('result'),
                     recipe_table_alias.c.whiteboard,
                     arch_alias.c.arch,
                     case0.label('rc0'),
                     case1.label('rc1'),
                     case2.label('rc2'),
                     case3.label('rc3'),
                     case4.label('rc4')]
                   
                         
        my_from = [model.recipe_set_table.join(recipe_table_alias).
                              join(model.task_result_table,model.task_result_table.c.id == recipe_table_alias.c.result_id).
                              join(model.distro_table, model.distro_table.c.id == recipe_table_alias.c.distro_id).
                              join(arch_alias, arch_alias.c.id == model.distro_table.c.arch_id).
                              join(model.recipe_task_table, model.recipe_task_table.c.recipe_id == recipe_table_alias.c.id).
                              join(model.task_table, model.task_table.c.id == model.recipe_task_table.c.task_id)]
                   
        #If this query starts to bog down and slow up, we could create a view for the inner select (s2)
        #SQLAlchemy Select object does not really support this,I think you would have to use SQLAlchemy text for s2, and then
        #build a specific table for it
        #eng = database.get_engine()
        #c = s2.compile(eng) 
        #eng.execute("CREATE VIEW foobar AS %s" % c) 

        result_data = []    
        my_hash = {} 
        for arch_val,whiteboard_val in whiteboard_data.iteritems():
           
            if whiteboard_val is not None:
                my_and = and_( model.recipe_set_table.c.job_id.in_(jobs),
                               arch_alias.c.arch == bindparam('arch'), 
                               recipe_table_alias.c.whiteboard == bindparam('recipe_whiteboard'))
              
              
            else: 
                my_and = and_( model.recipe_set_table.c.job_id.in_(jobs),
                               arch_alias.c.arch == bindparam('arch'), 
                               recipe_table_alias.c.whiteboard==None)
            s2 = select(my_select,from_obj=my_from,whereclause=my_and).alias('foo')
            s2 = s2.params(arch=arch_val)
            if whiteboard_val is not None:
                 s2 = s2.params(recipe_whiteboard=whiteboard_val) 
               
           
            s1  = select([func.count(s2.c.result),
                                  func.sum(s2.c.rc0).label('New'),
                                  func.sum(s2.c.rc1).label('Pass'),
                                  func.sum(s2.c.rc2).label('Warn'),
                                  func.sum(s2.c.rc3).label('Fail'),
                                  func.sum(s2.c.rc4).label('Panic'),
                                  s2.c.arch,
                                  model.task_table.c.name.label('task_name'),  
                                  s2.c.task_id.label('task_id_pk')],
                                  s2.c.task_id == model.task_table.c.id,
                     
                                  from_obj=[model.task_table,s2]).group_by(model.task_table.c.name).order_by(model.task_table.c.name).alias()
          
            class InnerDynamo(object):
                pass
            mapper(InnerDynamo,s1)
 
            dyn = InnerDynamo.query() 
            for d in dyn: 
                self.arches_used[d.arch] = 1 
                if d.task_name not in my_hash:
                    my_hash[d.task_name] = [d]
                else:  
                    my_hash[d.task_name].append(d) 
      
        for k,v in my_hash.items():
            my_tuple = (k,)
            for elem in v: 
                my_tuple += (elem,) 
            result_data.append(my_tuple)
 
        return result_data 

    @classmethod
    def make_result_box(cls,returns,query_obj,result=None):
        #if result is None:
        #    result = text.lower()
        elem = Element('div',{'class' : 'result-box'})
        items = returns.split()
        for item in items:
            how_many = getattr(query_obj,item,None)
            if how_many is not None and how_many > 0:            
                result = item.lower()
                sub_span = SubElement(elem,'span', {'class':'rounded-side-pad %s' % result}) 
                SubElement(elem,'br')
                sub_link = SubElement(sub_span,'a', {'style':'color:inherit;text-decoration:none'}, href=url('/matrix/test_report?id=')) 
                sub_link.text = '%s: %s' % (item,how_many)
        return elem
