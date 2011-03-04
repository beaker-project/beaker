from sqlalchemy import select, distinct, Table, Column, Integer, String
from sqlalchemy.sql.expression import case, func, and_, bindparam, not_
from turbogears import controllers, identity, expose, url, database
from turbogears.widgets import DataGrid
from turbogears.database import session, metadata, mapper
from kid import Element, SubElement
from bkr.server.widgets import JobMatrixReport as JobMatrixWidget, MatrixDataGrid
from bkr.server.helpers import make_link
import model
import logging
log = logging.getLogger(__name__)

class TaskR:
                    
    def __init__(self,task_name,*args,**kw):
        self.task_name = task_name
        self.results = {}
                      
    def add_result(self,arch,whiteboard,results): 
        try:
            self.results[arch][whiteboard] = results
        except KeyError:
            self.results[arch] = { whiteboard : results } 

    def get_results(self,arch,whiteboard=None):
        try:
            if not whiteboard:
                return_list = []
                for w in self.results[arch]:
                    return_list += self.results[arch][w] 
                return return_list
            else:
                return self.results[arch][whiteboard]
        except KeyError, (e): #This is fine, just means that this task has no entry for a given arch/whiteboard
            #log.debug('Index does not exist Arch %s whiteboard:%s ' % (arch,whiteboard))
            return []

class JobMatrix:
    default_whiteboard_title = ''
    job_matrix_widget = JobMatrixWidget() 
    arches_used = {} 
    whiteboards_used = {}
    result_data = []

    @expose(template='bkr.server.templates.generic')
    def index(self,**kw):
        self.col_call = 0
        self.max_cols = 0
        self.job_ids = []
        matrix_options = {} 
        if 'whiteboard_filter' in kw:
            filter = kw['whiteboard_filter']
        else:
            filter = None 
       
        matrix_options['whiteboard_options'] = self.get_whiteboard_options(filter)
       
        if ('job_ids' in kw) or ('whiteboard' in kw): 
            gen_results = self.generate(**kw) 
            matrix_options['grid'] = gen_results['grid']
            matrix_options['list'] = gen_results['data'] 
            if 'whiteboard' in kw: # Getting results by whiteboard
                jobs = model.Job.by_whiteboard(kw['whiteboard'])  
                job_ids = [str(j.id) for j in jobs]
                self.job_ids = job_ids
                matrix_options['job_ids_vals'] = "\n".join(job_ids)
            if 'job_ids' in kw: #Getting results by job id
                self.job_ids = kw['job_ids'].split()
                matrix_options['job_ids_vals'] = kw['job_ids']
            if 'toggle_nacks_on' in kw:
                matrix_options['toggle_nacks_on'] = True
            else:
                matrix_options['toggle_nacks_on'] = False

            all_rs_queri = model.RecipeSet.query().join(['job']).filter(model.Job.id.in_(self.job_ids))
            all_ids = [elem.id for elem in all_rs_queri]
        else:
            matrix_options['toggle_nacks_on'] = False
            matrix_options['grid'] = None
       
        return dict(widget=self.job_matrix_widget, widget_options=matrix_options, title="Job Matrix Report")

    @expose(format='json')
    def get_whiteboard_options_json(self,filter):
        return_dict = {}
        return_dict['options'] =  self.get_whiteboard_options(filter)
        return return_dict

    def get_whiteboard_options(self,filter):
        """
        get_whiteboard_options() returns all whiteboards from the job_table
        if value is passed in for 'filter' it will perform an SQL 'like' operation 
        against whiteboard
        """
        if filter: 
            where = model.job_table.c.whiteboard.like('%%%s%%' % filter)   
        else:
            where = None
        s1 = select([model.job_table.c.whiteboard],whereclause=where,
                     group_by=[model.job_table.c.whiteboard,model.job_table.c.id],
                     order_by=[model.job_table.c.id],distinct=True,limit=50) 
        res = s1.execute()  
        filtered_whiteboards = [r[0] for r in res]
        return filtered_whiteboards 
 
    def display_whiteboard_results(self,whiteboard,arch):
        """Return func pointer to display result box

        display_whiteboard_results() is a closure. It takes a whiteboard
        and returns a function that will return a result box if the whiteboard passed
        to it matches the whiteboard var which is closed over.

        """
        def f(x):
                try:
                    dyn_objs = x.get_results(arch,whiteboard)
                    for d in dyn_objs: 
                        if d.arch == arch and d.whiteboard == whiteboard:
                            return self.make_result_box(model.TaskResult.get_results(),d)
                except Exception, (e):
                    log.error('Error %s' % e)
        return f

    def _job_grid_fields(self,arches_used,**kw):
        """Return fields of Columns for matrix table

        _job_grid_fields() takes a list of arches and will return a list of
        Column objects to represent those arches. Also sets the max_cols
        variable to the number of arch columns.

        """
        fields = []
        for arch in self.whiteboards_used:
            for whiteboard in self.whiteboards_used[arch]:
                whiteboard_name = orig_whiteboard_name = whiteboard
                if not whiteboard_name:
                    whiteboard_name = self.default_whiteboard_title
                fields.append(MatrixDataGrid.Column(outer_header=arch,
                    name=whiteboard_name, getter=self.\
                        display_whiteboard_results(orig_whiteboard_name, arch),\
                        title=orig_whiteboard_name))

        fields.append(MatrixDataGrid.Column(name='task',title=None, order=MatrixDataGrid.TASK_POS, outer_header='Task',
            getter=lambda x: x.task_name))
        return fields

    def generate(self,**kw):
        """Return Grid and Data

        generate() returns a BeakerDataGrid and a dataset for it to operate on

        """
        grid_data = self.generate_data(**kw) 
        grid = MatrixDataGrid(fields = self._job_grid_fields(self.arches_used.keys()))
        session.flush()
        return {'grid' : grid, 'data' : grid_data }     

    def generate_data(self,**kw):
        """Return matrix details

        generate_data() returns a nested tuple which represents tasks->arches->whiteboards and their data objects

        """
        jobs = []
        self.arches_used = {}
        self.whiteboards_used = {}
        whiteboard_data = {} 
        if 'job_ids' in kw:
            jobs = kw['job_ids'].split() 
        elif 'whiteboard' in kw:
            job_query = model.Job.query().filter(model.Job.whiteboard == kw['whiteboard'])
            for job in job_query:
                jobs.append(job.id) 
        else:
           pass

        recipes = model.Recipe.query().join(['distro','arch']).join(['recipeset','job']).filter(model.RecipeSet.job_id.in_(jobs)).add_column(model.Arch.arch)
        if 'toggle_nacks_on' in kw: #if we're here we are potentially trying to hide naked RS'
            exclude_recipe_sets = model.Job.get_nacks(jobs)
            recipes = recipes.filter(not_(model.RecipeSet.id.in_(exclude_recipe_sets)))
        else: #Likely this is the initial page load for these Jobs. No modifying the nack db.
            exclude_recipe_sets = [] 
            #recipes = recipes.filter(not_(model.RecipeSet.id.in_(exclude_recipe_sets))) 
        """
        Let's get all the tasks that will be run, and the arch/whiteboard
        """
        the_tasks = {}
        for recipe,arch in recipes:
            the_tasks.update(dict([(rt.task.name,{}) for rt in recipe.tasks]))
            if arch in whiteboard_data:
                if recipe.whiteboard not in whiteboard_data[arch]:
                    whiteboard_data[arch].append(recipe.whiteboard)
            else:
                whiteboard_data[arch] = [recipe.whiteboard]
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
                     arch_alias.c.id.label('arch_id'),
                     case0.label('rc0'),
                     case1.label('rc1'),
                     case2.label('rc2'),
                     case3.label('rc3'),
                     case4.label('rc4'),]
                       
        my_from = [model.recipe_set_table.join(recipe_table_alias). 
                              join(model.distro_table, model.distro_table.c.id == recipe_table_alias.c.distro_id).
                              join(arch_alias, arch_alias.c.id == model.distro_table.c.arch_id).
                              join(model.recipe_task_table, model.recipe_task_table.c.recipe_id == recipe_table_alias.c.id).
                              join(model.task_result_table,model.task_result_table.c.id == model.recipe_task_table.c.result_id).
                              join(model.task_table, model.task_table.c.id == model.recipe_task_table.c.task_id)]
                   
        #If this query starts to bog down and slow up, we could create a view for the inner select (s2)
        #SQLAlchemy Select object does not really support this,I think you would have to use SQLAlchemy text for s2, and then
        #build a specific table for it
        #eng = database.get_engine()
        #c = s2.compile(eng) 
        #eng.execute("CREATE VIEW foobar AS %s" % c)
        for arch_val,whiteboard_set in whiteboard_data.iteritems():
            for whiteboard_val in whiteboard_set:
                if whiteboard_val is not None:
                    my_and = [model.recipe_set_table.c.job_id.in_(jobs),
                                   arch_alias.c.arch == bindparam('arch'), 
                                   recipe_table_alias.c.whiteboard == bindparam('recipe_whiteboard')]
                else: 
                    my_and = [model.recipe_set_table.c.job_id.in_(jobs),
                                   arch_alias.c.arch == bindparam('arch'), 
                                   recipe_table_alias.c.whiteboard==None]

                try:
                    ex = locals()['exclude_recipe_sets'] 
                    my_and.append(not_(model.recipe_set_table.c.id.in_(exclude_recipe_sets)))
                except KeyError, e: pass

                s2 = select(my_select,from_obj=my_from,whereclause=and_(*my_and)).alias('foo')
                s2 = s2.params(arch=arch_val)
                if whiteboard_val is not None:
                    s2 = s2.params(recipe_whiteboard=whiteboard_val)

                s1  = select([func.count(s2.c.result),
                              func.sum(s2.c.rc0).label('New'),
                              func.sum(s2.c.rc1).label('Pass'),
                              func.sum(s2.c.rc2).label('Warn'),
                              func.sum(s2.c.rc3).label('Fail'),
                              func.sum(s2.c.rc4).label('Panic'),
                              s2.c.whiteboard,
                              s2.c.arch,
                              s2.c.arch_id,
                              model.task_table.c.name.label('task_name'),
                              s2.c.task_id.label('task_id_pk')],
                              s2.c.task_id == model.task_table.c.id,
                              from_obj=[model.task_table,s2]).group_by(model.task_table.c.name).order_by(model.task_table.c.name).alias()
                results = s1.execute()
                for task_details in results:
                    if task_details.arch in the_tasks[task_details.task_name]:
                        if (whiteboard_val not in
                            the_tasks[task_details.task_name][task_details.arch]):
                            (the_tasks[task_details.task_name][task_details.arch]
                                [whiteboard_val]) = [task_details]
                        else:
                            (the_tasks[task_details.task_name]
                                [task_details.arch][whiteboard_val].
                                append(task_details))
                    else:
                        the_tasks[task_details.task_name][task_details.arch] = \
                            { whiteboard_val : [task_details] }

        # Here we append TaskR objects to an array. Each TaskR object
        # will have a nested dict accessable by a arch/whiteboard key, which will
        # return a InnerDynamo object. There should be one TaskR object for each
        # task name
        self.whiteboards_used = whiteboard_data
        self.arches_used = dict.fromkeys(whiteboard_data.keys(),1)
        result_data = []
        sorted_tasks = sorted(the_tasks.items())
        for task_name,arch_whiteboard_val in sorted_tasks:
            n = TaskR(task_name)
            for arch,whiteboard_val in arch_whiteboard_val.items():
                for whiteboard,dynamo_objs in whiteboard_val.items():
                    n.add_result(arch,whiteboard,dynamo_objs)
            result_data.append(n)
        self.result_data = result_data
        return result_data

    def _create_task_list_params(self,query_obj,result):
        """
        _create_task_list_params() takes a query obj of the type generated in generate_data()
        and will return a string representation of a URL pointing to a page which will display the
        results of the given task 
        """
        return url('/tasks/executed',
                task=query_obj.task_name,
                result_id=result,
                whiteboard=query_obj.whiteboard or '',
                arch_id=query_obj.arch_id,
                job_id=self.job_ids)

    def make_result_box(self,returns,query_obj,result=None): 
        """
        make_result_box() takes a list of tuples containing a result id and result name, as well as
        Query obj and returns DOM element representing a Task result. 
        """
        elem = Element('div',{'class' : 'result-box'})
        
        for item in returns:
            result_text = item[1]
            result_id = item[0]
            how_many = getattr(query_obj,result_text,None)
            if how_many is not None and how_many > 0:            
                result_text_lower = result_text.lower()
                sub_span = SubElement(elem,'span', {'class':'rounded-side-pad %s' % result_text_lower}) 
                SubElement(elem,'br') 
                task_list_params = self._create_task_list_params(query_obj,result_id)
                sub_link = SubElement(sub_span,
                                      'a', 
                                      {'style':'color:inherit;text-decoration:none'}, 
                                      href=task_list_params)
                                               

                sub_link.text = '%s: %s' % (result_text,how_many)
  
        return elem
