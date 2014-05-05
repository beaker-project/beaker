
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, flash, widgets, validate, redirect, paginate, url
from bkr.server import search_utility, identity
from bkr.server.widgets import myPaginateDataGrid, TasksWidget, TaskSearchForm, \
        SearchBar, TaskActionWidget, HorizontalForm
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link
from bkr.server.bexceptions import DatabaseLookupError
from bkr.common.helpers import siphon
from bkr.common.bexceptions import BX
from sqlalchemy import or_, and_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import joinedload, joinedload_all
from sqlalchemy.orm.exc import NoResultFound

import os

import cherrypy

from bkr.server.model import (Distro, Task, OSMajor, Recipe, RecipeSet,
                              RecipeTask, DistroTree, TaskPackage, TaskType,
                              Job, Arch, OSVersion, RecipeTaskResult, System,
                              SystemResource, RecipeResource)

import logging
log = logging.getLogger(__name__)

__all__ = ['Tasks']

class Tasks(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    task_list_action_widget = TaskActionWidget()
    task_form = TaskSearchForm()
    task_widget = TasksWidget()

    _upload = widgets.FileField(name='task_rpm', label='Task RPM')
    form = HorizontalForm(
        'task',
        fields = [_upload],
        action = 'save_data',
        submit_text = _(u'Upload')
    )
    del _upload

    @expose(template='bkr.server.templates.form-post')
    @identity.require(identity.not_anonymous())
    def new(self, **kw):
        return_dict = dict(
            title = 'New Task',
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )
        return return_dict

    @cherrypy.expose
    def filter(self, filter):
        """
        Returns a list of tasks filtered by the given criteria.

        The *filter* argument must be an XML-RPC structure (dict), with any of the following keys:

            'distro_name'
                Distro name. Include only tasks which are compatible 
                with this distro.
            'osmajor'
                OSVersion OSMajor, like RedHatEnterpriseLinux6.  Include only
                tasks which are compatible with this OSMajor.
            'names'
                Task name. Include only tasks that are named. Useful when
                combined with 'osmajor' or 'distro_name'.
            'packages'
                List of package names. Include only tasks which have a Run-For 
                entry matching any of these packages.
            'types'
                List of task types. Include only tasks which have one or more 
                of these types.
            'valid'
                bool 0 or 1. Include only tasks which are valid or not.
            'destructive'
                bool 0 or 1. Set to 0 for only non-destructive tasks. Set to 
                1 for only destructive tasks.

        The return value is an array of dicts, which are name and arches. 
        name is the name of the matching tasks.
        arches is an array of arches which this task does not apply for.
        Call :meth:`tasks.to_dict` to fetch metadata for a particular task.

        .. versionchanged:: 0.9
           Changed 'install_name' to 'distro_name' in the *filter* argument.
        """
        if filter.get('distro_name'):
            try:
                distro = Distro.by_name(filter['distro_name'])
            except NoResultFound:
                raise BX(_(u'Invalid Distro: %s') % filter['distro_name'])
            tasks = distro.tasks()
        elif 'osmajor' in filter and filter['osmajor']:
            try:
                osmajor = OSMajor.by_name(filter['osmajor'])
            except InvalidRequestError:
                raise BX(_('Invalid OSMajor: %s' % filter['osmajor']))
            tasks = osmajor.tasks()
        else:
            tasks = Task.query

        # Filter by valid task if requested
        if 'valid' in filter:
            tasks = tasks.filter(Task.valid==bool(filter['valid']))

        # Filter by destructive if requested
        if 'destructive' in filter:
            tasks = tasks.filter(Task.destructive==bool(filter['destructive']))

        # Filter by name if specified
        # /distribution/install, /distribution/reservesys
        if 'names' in filter and filter['names']:
            # if not a list, make it into a list.
            if isinstance(filter['names'], str):
                filter['names'] = [filter['names']]
            or_names = []
            for tname in filter['names']:
                or_names.append(Task.name==tname)
            tasks = tasks.filter(or_(*or_names))

        # Filter by packages if specified
        # apache, kernel, mysql, etc..
        if 'packages' in filter and filter['packages']:
            # if not a list, make it into a list.
            if isinstance(filter['packages'], str):
                filter['packages'] = [filter['packages']]
            tasks = tasks.filter(Task.runfor.any(or_(
                    *[TaskPackage.package == package for package in filter['packages']])))

        # Filter by type if specified
        # Tier1, Regression, KernelTier1, etc..
        if 'types' in filter and filter['types']:
            # if not a list, make it into a list.
            if isinstance(filter['types'], str):
                filter['types'] = [filter['types']]
            tasks = tasks.join('types')
            or_types = []
            for type in filter['types']:
                try:
                    tasktype = TaskType.by_name(type)
                except InvalidRequestError, err:
                    raise BX(_('Invalid Task Type: %s' % type))
                or_types.append(TaskType.id==tasktype.id)
            tasks = tasks.filter(or_(*or_types))

        # Return all task names
        return [dict(name = task.name, arches = [str(arch.arch) for arch in task.excluded_arch]) for task in tasks]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def upload(self, task_rpm_name, task_rpm_data):
        """
        Uploads a new task RPM.

        :param task_rpm_name: filename of the task RPM, for example 
            ``'beaker-distribution-install-1.10-11.noarch.rpm'``
        :type task_rpm_name: string
        :param task_rpm_data: contents of the task RPM
        :type task_rpm_data: XML-RPC binary
        """
        rpm_path = Task.get_rpm_path(task_rpm_name)
        # we do it here, since we do not want to proceed
        # any further
        if len(task_rpm_name) > 255:
            raise BX(_("Task RPM name should be <= 255 characters"))
        if os.path.exists("%s" % rpm_path):
            raise BX(_(u'Cannot import duplicate task %s') % task_rpm_name)

        def write_data(f):
            f.write(task_rpm_data.data)
        Task.update_task(task_rpm_name, write_data)
        return "Success"

    @expose()
    @identity.require(identity.not_anonymous())
    def save(self, task_rpm, *args, **kw):
        """
        TurboGears method to upload task rpm package
        """
        rpm_path = Task.get_rpm_path(task_rpm.filename)

        if not task_rpm.filename:
            flash(_(u'No task RPM specified'))
            redirect(url("./new"))

        # we do it here, since we do not want to proceed
        # any further
        if len(task_rpm.filename) > 255:
            flash(_(u"Task RPM name should be <= 255 characters"))
            redirect(url("./new"))

        if os.path.exists("%s" % rpm_path):
            flash(_(u'Failed to import because we already have %s' % 
                                                     task_rpm.filename ))
            redirect(url("./new"))

        try:
            def write_data(f):
                siphon(task_rpm.file, f)
            task = Task.update_task(task_rpm.filename, write_data)
        except Exception, err:
            session.rollback()
            log.exception('Failed to import %s', task_rpm.filename)
            flash(_(u'Failed to import task: %s' % err))
            redirect(url("./new"))
        flash(_(u"%s Added/Updated at id:%s" % (task.name,task.id)))
        redirect(".")

    @expose(template='bkr.server.templates.task_search')
    @validate(form=task_form)
    @paginate('tasks',default_order='-id', limit=30)
    def executed(self, hidden={}, **kw):
        tmp = self._do_search(hidden, **kw)
        tmp['form'] = self.task_form
        tmp['action'] = './do_search'
        tmp['value'] = None
        tmp['options'] = dict()
        return tmp
    
    @expose(template='bkr.server.templates.tasks')
    @validate(form=task_form)
    @paginate('tasks',default_order='-id', limit=30, max_limit=None)
    def do_search(self, hidden={}, **kw):
        return self._do_search(hidden=hidden, **kw)

    def _do_search(self, hidden={}, **kw):
        tasks = RecipeTask.query\
                .filter(RecipeTask.recipe.has(Recipe.recipeset.has(RecipeSet.job.has(
                    and_(Job.to_delete == None, Job.deleted == None)))))\
                .options(joinedload(RecipeTask.task),
                     joinedload_all(RecipeTask.results, RecipeTaskResult.logs))

        recipe_task_id = kw.get('recipe_task_id')
        if recipe_task_id:
            if isinstance(recipe_task_id, basestring):
                tasks = tasks.filter(RecipeTask.id == recipe_task_id)
            elif isinstance(recipe_task_id, list):
                tasks = tasks.filter(RecipeTask.id.in_(recipe_task_id))
        if 'recipe_id' in kw: #most likely we are coming here from a LinkRemoteFunction in recipe_widgets
            tasks = tasks.join(RecipeTask.recipe).filter(Recipe.id == kw['recipe_id'])

            hidden = dict(distro_tree=1, system=1)
        if kw.get('distro_tree_id'):
            tasks = tasks.join(RecipeTask.recipe, Recipe.distro_tree)\
                    .filter(DistroTree.id == kw.get('distro_tree_id'))
            hidden = dict(distro_tree=1)
        elif kw.get('distro_id'):
            tasks = tasks.join(RecipeTask.recipe, Recipe.distro_tree, DistroTree.distro)\
                    .filter(Distro.id == kw.get('distro_id'))
        if kw.get('task_id'):
            try:
                tasks = tasks.join('task').filter(Task.id==kw.get('task_id'))
                hidden = dict(task = 1,
                             )
            except InvalidRequestError:
                return "<div>Invalid data:<br>%r</br></div>" % kw
        if kw.get('system_id'):
            tasks = tasks.join(RecipeTask.recipe,
                    Recipe.resource.of_type(SystemResource),
                    SystemResource.system)\
                    .filter(System.id == kw.get('system_id'))\
                    .order_by(RecipeTask.id.desc())
            hidden = dict(system=1)
        if kw.get('job_id'):
            job_id = kw.get('job_id')
            if not isinstance(job_id, list):
                job_id = [job_id]
            tasks = tasks.join('recipe','recipeset','job').filter(Job.id.in_(job_id))
        if kw.get('system'):
            tasks = tasks.join(RecipeTask.recipe, Recipe.resource)\
                    .filter(RecipeResource.fqdn.like('%%%s%%' % kw.get('system')))
        if kw.get('task'):
            # Shouldn't have to do this.  This only happens on the LinkRemoteFunction calls
            kw['task'] = kw.get('task').replace('%2F','/')
            tasks = tasks.filter(RecipeTask.name.like('%s' % kw.get('task').replace('*','%%')))
        if kw.get('version'):
            tasks = tasks.filter(RecipeTask.version.like(kw.get('version').replace('*', '%')))
        if kw.get('distro'):
            tasks = tasks.join(RecipeTask.recipe, Recipe.distro_tree, DistroTree.distro)\
                    .filter(Distro.name.like('%%%s%%' % kw.get('distro')))
        if kw.get('arch_id'):
            tasks = tasks.join(RecipeTask.recipe, Recipe.distro_tree, DistroTree.arch)\
                    .filter(Arch.id == kw.get('arch_id'))
        if kw.get('status'):
            tasks = tasks.filter(RecipeTask.status == kw['status'])
        if kw.get('is_failed'):
            tasks = tasks.filter(RecipeTask.is_failed())
        elif kw.get('result'):
            tasks = tasks.filter(RecipeTask.result == kw['result'])
        if kw.get('osmajor_id'):
            tasks = tasks.join(RecipeTask.recipe, Recipe.distro_tree,
                    DistroTree.distro, Distro.osversion, OSVersion.osmajor)\
                    .filter(OSMajor.id == kw.get('osmajor_id'))
        if kw.get('whiteboard'):
            tasks = tasks.join('recipe').filter(Recipe.whiteboard==kw.get('whiteboard'))
        return dict(tasks = tasks,
                    hidden = hidden,
                    task_widget = self.task_widget)

    @identity.require(identity.in_group('admin'))
    @expose()
    def disable_from_ui(self, t_id, *args, **kw):
        to_return = dict( t_id = t_id )
        try:
            self._disable(t_id)
            to_return['success'] = True
        except Exception, e:
            log.exception('Unable to disable task:%s' % t_id)
            to_return['success'] = False
            to_return['err_msg'] = unicode(e)
            session.rollback()
        return to_return

    def _disable(self, t_id, *args, **kw):
        """
        disable task
         task.valid=False
         remove task rpms from filesystem
        """
        task = Task.by_id(t_id)
        return task.disable()

    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='name', limit=30)
    def index(self, *args, **kw):
        tasks = Task.query
        # FIXME What we really want is some default search options
        # For now we won't show deleted/invalid tasks in the grid
        # but for data integrity reasons we will allow you to view
        # the task directly.  Ideally we would have a default search
        # option of valid=True which the user could change to false
        # to see all "deleted" tasks
        tasks = tasks.filter(Task.valid==True)

        tasks_return = self._tasks(tasks,**kw)
        searchvalue = None
        search_options = {}
        if tasks_return:
            if 'tasks_found' in tasks_return:
                tasks = tasks_return['tasks_found']
            if 'searchvalue' in tasks_return:
                searchvalue = tasks_return['searchvalue']
            if 'simplesearch' in tasks_return:
                search_options['simplesearch'] = tasks_return['simplesearch']

        tasks_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='name', getter=lambda x: make_link("./%s" % x.id, x.name), title='Name', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='description', getter=lambda x:x.description, title='Description', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='version', getter=lambda x:x.version, title='Version', options=dict(sortable=True)),
                     widgets.PaginateDataGrid.Column(name='action', getter=lambda x: self.task_list_action_widget.display(task=x, type_='tasklist', title='Action', options=dict(sortable=False))),
                    ])

        search_bar = SearchBar(name='tasksearch',
                           label=_(u'Task Search'),
                           table = search_utility.Task.search.create_search_table(),
                           complete_data=search_utility.Task.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_task"),
                           )
        return dict(title="Task Library",
                    grid=tasks_grid,
                    list=tasks,
                    search_bar=search_bar,
                    action='.',
                    action_widget = self.task_list_action_widget,  #Hack,inserts JS for us.
                    options=search_options,
                    searchvalue=searchvalue)

    @expose(template='bkr.server.templates.task')
    def default(self, *args, **kw):
        try:
            using_task_id = False
            if len(args) == 1:
                try:
                    task_id = int(args[0])
                    using_task_id = True
                except ValueError:
                    pass
            if using_task_id:
                task = Task.by_id(task_id)
            else:
                task = Task.by_name("/%s" % "/".join(args))
                #Would rather not redirect but do_search expects task_id in URL
                #This is the simplest way of dealing with it
                redirect("/tasks/%s" % task.id)
        except DatabaseLookupError as e:
            flash(unicode(e))
            redirect("/tasks")

        return dict(task=task,
                    form = self.task_form,
                    value = dict(task_id = task.id),
                    options = dict(hidden=dict(task = 1)),
                    action = './do_search')

    @expose(format='json')
    def by_name(self, task):
        task = task.lower()
        return dict(tasks=[(task.name) for task in Task.query.filter(Task.name.like('%s%%' % task))])

    @cherrypy.expose
    def to_xml(self, name, pretty, valid=True):
        """
        Returns task details as xml
        """
        return Task.by_name(name, valid).to_xml(pretty)

    @cherrypy.expose
    def to_dict(self, name, valid=None):
        """
        Returns an XML-RPC structure (dict) with details about the given task.
        """
        return Task.by_name(name, valid).to_dict()

    def _tasks(self,task,**kw):
        return_dict = {}                    
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['tasksearch'] = [{'table' : 'Name',   
                                 'operation' : 'contains', 
                                 'value' : kw['simplesearch']}]                    
        else:
            simplesearch = None

        return_dict.update({'simplesearch':simplesearch})

        if kw.get("tasksearch"):
            searchvalue = kw['tasksearch']  
            tasks_found = self._task_search(task,**kw) 
            return_dict.update({'tasks_found':tasks_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _task_search(self,task,**kw):
        task_search = search_utility.Task.search(task)
        for search in kw['tasksearch']:
            col = search['table'] 
            task_search.append_results(search['value'],col,search['operation'],**kw)
        return task_search.return_results()

    @expose(template='bkr.server.templates.tasks')
    def parrot(self,*args,**kw): 
        if 'recipe_id' in kw:
            recipe = Recipe.by_id(kw['recipe_id'])
            return recipe.all_tasks

# for sphinx
tasks = Tasks
