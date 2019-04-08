
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy import select
from sqlalchemy.sql.expression import case, func, and_, bindparam, not_
from turbogears import expose, url, flash
from turbogears.database import session
from kid import Element, SubElement
from bkr.server.widgets import JobMatrixReport as JobMatrixWidget, MatrixDataGrid
from bkr.server import model
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
        except KeyError: #This is fine, just means that this task has no entry for a given arch/whiteboard
            #log.debug('Index does not exist Arch %s whiteboard:%s ' % (arch,whiteboard))
            return []

class JobMatrix:
    MAX_JOBS_FROM_WHITEBOARD = 20
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
        matrix_options['whiteboard_options'] = self.get_whiteboard_options(kw.get('filter'), selected=kw.get('whiteboard'))
        if ('job_ids' in kw or 'whiteboard' in kw):
            job_ids = []
            if 'job_ids' in kw:
                job_ids = [int(j) if j.isdigit() else None for j in kw['job_ids'].split()]
                # Filter out ids of deleted jobs
                query = model.Job.query.filter(not_(model.Job.is_deleted)).filter(model.Job.id.in_(job_ids))
                job_ids = [job_id for job_id, in query.values(model.Job.id)]
            # Build the result grid
            gen_results = self.generate(whiteboard=kw.get('whiteboard'),
                job_ids=job_ids, toggle_nacks=kw.get('toggle_nacks_on'))
            matrix_options['grid'] = gen_results['grid']
            matrix_options['list'] = gen_results['data']
            if 'whiteboard' in kw: # Getting results by whiteboard
                jobs = model.Job.by_whiteboard(kw.get('whiteboard')).filter(not_(model.Job.is_deleted))
                job_count = jobs.count()
                if job_count > model.Job.max_by_whiteboard:
                    flash(_('Your whiteboard contains %s jobs, only %s will be used' % (job_count, model.Job.max_by_whiteboard)))
                jobs = jobs.limit(model.Job.max_by_whiteboard)
                job_ids = [str(j.id) for j in jobs]
                self.job_ids = job_ids
                matrix_options['job_ids_vals'] = "\n".join([str(j) for j in job_ids])
            elif job_ids: #Getting results by job id
                self.job_ids = job_ids
                matrix_options['job_ids_vals'] = '\n'.join([str(j) for j in job_ids])
            if 'toggle_nacks_on' in kw:
                matrix_options['toggle_nacks_on'] = True
            else:
                matrix_options['toggle_nacks_on'] = False
        else:
            matrix_options['toggle_nacks_on'] = False
            matrix_options['grid'] = None
       
        return dict(widget=self.job_matrix_widget, widget_options=matrix_options,
                title="Job Matrix Report", value=None, widget_attrs={})

    @expose(format='json')
    def get_whiteboard_options_json(self,filter):
        return_dict = {}
        return_dict['options'] = self.get_whiteboard_options(filter)
        return return_dict

    def get_whiteboard_options(self,filter, selected=None):
        """
        get_whiteboard_options() returns all whiteboards from the job_table
        if value is passed in for 'filter' it will perform an SQL 'like' operation
        against whiteboard
        """
        if selected is None:
            selected = []
        if filter:
            query = model.Job.by_whiteboard(filter, like=True)
        else:
            query = model.Job.query
        query = query.filter(not_(model.Job.is_deleted))
        query = query.group_by(model.Job.whiteboard). \
            order_by(model.Job.id.desc()).limit(50)
        whiteboards = query.values(model.Job.whiteboard)
        options = []
        for whiteboard in whiteboards:
            whiteboard = whiteboard[0]
            option_list = [whiteboard, whiteboard]
            if whiteboard in selected:
                option_list.append({'selected' : 'selected' })
            options.append(option_list)
        return options

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
                        return self.make_result_box(d)
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

    def generate(self, whiteboard, job_ids, toggle_nacks):
        """Return Grid and Data

        generate() returns a BeakerDataGrid and a dataset for it to operate on

        """
        grid_data = self.generate_data(whiteboard, job_ids, toggle_nacks)
        grid = MatrixDataGrid(fields = self._job_grid_fields(self.arches_used.keys()))
        session.flush()
        return {'grid' : grid, 'data' : grid_data}

    def generate_data(self, whiteboard, job_ids, toggle_nacks):
        """Return matrix details

        generate_data() returns a nested tuple which represents tasks->arches->whiteboards and their data objects

        """
        self.arches_used = {}
        self.whiteboards_used = {}
        whiteboard_data = {}
        # If somehow both are passed, use the whiteboard
        if whiteboard:
            if isinstance(whiteboard, basestring):
                whiteboards = [whiteboard]
            else:
                whiteboards = whiteboard
            # If the whiteboard contains an embedded newline the browser will 
            # have converted it to CRLF, convert it back here.
            whiteboards = [w.replace('\r\n', '\n') for w in whiteboards]
            job_ids = []
            job_query = model.Job.by_whiteboard(whiteboards).filter(not_(model.Job.is_deleted))
            for job in job_query:
                job_ids.append(job.id)

        recipes = model.Recipe.query.join(model.Recipe.distro_tree, model.DistroTree.arch)\
                .join(model.Recipe.recipeset, model.RecipeSet.job)\
                .filter(model.RecipeSet.job_id.in_(job_ids))\
                .add_column(model.Arch.arch)
        # if we're here we are potentially trying to hide naked RS'
        if toggle_nacks:
            recipes = recipes.filter(model.RecipeSet.waived == False)
        # Let's get all the tasks that will be run, and the arch/whiteboard
        the_tasks = {}
        for recipe,arch in recipes:
            the_tasks.update(dict([(rt.name,{}) for rt in recipe.tasks]))
            if arch in whiteboard_data:
                if recipe.whiteboard not in whiteboard_data[arch]:
                    whiteboard_data[arch].append(recipe.whiteboard)
            else:
                whiteboard_data[arch] = [recipe.whiteboard]
        case0 = case([(model.RecipeTask.result == u'New',1)],else_=0)
        case1 = case([(model.RecipeTask.result == u'Pass',1)],else_=0)
        case2 = case([(model.RecipeTask.result == u'Warn',1)],else_=0)
        case3 = case([(model.RecipeTask.result == u'Fail',1)],else_=0)
        case4 = case([(model.RecipeTask.result == u'Panic',1)],else_=0)
        case5 = case([(model.RecipeTask.result == u'None',1)],else_=0)
        case6 = case([(model.RecipeTask.result == u'Skip',1)],else_=0)
    
        arch_alias = model.Arch.__table__.alias()
        recipe_table_alias = model.Recipe.__table__.alias()
        my_select = [model.RecipeTask.name,
                     model.RecipeTask.result,
                     recipe_table_alias.c.whiteboard,
                     arch_alias.c.arch,
                     arch_alias.c.id.label('arch_id'),
                     case0.label('rc0'),
                     case1.label('rc1'),
                     case2.label('rc2'),
                     case3.label('rc3'),
                     case4.label('rc4'),
                     case5.label('rc5'),
                     case6.label('rc6'),
                    ]
        my_from = [model.RecipeSet.__table__.join(recipe_table_alias).
                              join(model.DistroTree.__table__, model.DistroTree.id == recipe_table_alias.c.distro_tree_id).
                              join(arch_alias, arch_alias.c.id == model.DistroTree.arch_id).
                              join(model.RecipeTask.__table__, model.RecipeTask.recipe_id == recipe_table_alias.c.id)]

        #If this query starts to bog down and slow up, we could create a view for the inner select (s2)
        #SQLAlchemy Select object does not really support this,I think you would have to use SQLAlchemy text for s2, and then
        #build a specific table for it
        #eng = database.get_engine()
        #c = s2.compile(eng) 
        #eng.execute("CREATE VIEW foobar AS %s" % c)
        for arch_val,whiteboard_set in whiteboard_data.iteritems():
            for whiteboard_val in whiteboard_set:
                if whiteboard_val is not None:
                    my_and = [model.RecipeSet.job_id.in_(job_ids),
                                   arch_alias.c.arch == bindparam('arch'), 
                                   recipe_table_alias.c.whiteboard == bindparam('recipe_whiteboard')]
                else: 
                    my_and = [model.RecipeSet.job_id.in_(job_ids),
                                   arch_alias.c.arch == bindparam('arch'), 
                                   recipe_table_alias.c.whiteboard==None]

                if toggle_nacks:
                    my_and.append(model.RecipeSet.waived == False)

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
                              func.sum(s2.c.rc5).label('None'),
                              func.sum(s2.c.rc6).label('Skip'),
                              s2.c.whiteboard,
                              s2.c.arch,
                              s2.c.arch_id,
                              s2.c.name.label('task_name')],
                              from_obj=[s2]).group_by(s2.c.name).order_by(s2.c.name).alias()
                results = session.connection(model.Recipe).execute(s1)
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
                result=result,
                whiteboard=query_obj.whiteboard or '',
                arch_id=query_obj.arch_id,
                job_id=self.job_ids)

    def make_result_box(self, query_obj):
        """
        make_result_box() returns a DOM element representing a Task result.
        """
        elem = Element('div',{'class' : 'result-box'})
        
        for result in model.TaskResult:
            how_many = getattr(query_obj, result.value, None)
            if how_many is not None and how_many > 0:            
                sub_span = SubElement(elem,'span', {'class':'label label-result-%s' % result.value.lower()})
                SubElement(elem,'br') 
                task_list_params = self._create_task_list_params(query_obj, result.value)
                sub_link = SubElement(sub_span,
                                      'a', 
                                      {'style':'color:inherit;text-decoration:none'}, 
                                      href=task_list_params)
                                               

                sub_link.text = '%s: %s' % (result, how_many)
  
        return elem
