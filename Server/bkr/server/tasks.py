
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, flash, widgets, validate, redirect, paginate, url
from flask import jsonify, request
from bkr.server import search_utility, identity
from bkr.server.widgets import TasksWidget, TaskSearchForm, \
        TaskActionWidget, HorizontalForm
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.app import app
from bkr.common.helpers import siphon
from bkr.common.bexceptions import BX
from sqlalchemy import or_, not_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import joinedload
from bkr.server.flask_util import NotFound404, request_wants_json, \
    render_tg_template, admin_auth_required, read_json_request, \
    convert_internal_errors, json_collection

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
        tasks = Task.query

        if filter.get('distro_name'):
            distro = Distro.by_name(filter['distro_name'])
            tasks = tasks.filter(Task.compatible_with_distro(distro))
        elif 'osmajor' in filter and filter['osmajor']:
            try:
                osmajor = OSMajor.by_name(filter['osmajor'])
            except InvalidRequestError:
                raise BX(_('Invalid OSMajor: %s' % filter['osmajor']))
            tasks = tasks.filter(Task.compatible_with_osmajor(osmajor))

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

        result = []
        for task in tasks:
            if task.exclusive_arches:
                excluded_arches = [arch.arch for arch in Arch.query
                                   if arch not in task.exclusive_arches]
            else:
                excluded_arches = [arch.arch for arch in task.excluded_arches]
            # Note that the 'arches' key in the return value is actually the 
            # list of *excluded* arches, in spite of its name.
            result.append({'name': task.name, 'arches': excluded_arches})
        return result

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
        redirect("/tasks/%s" % task.id)

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
        tasks = RecipeTask.query.join(RecipeTask.recipe).join(Recipe.recipeset).join(RecipeSet.job) \
            .filter(not_(Job.is_deleted)) \
            .options(joinedload(RecipeTask.task),
                     joinedload(RecipeTask.results).joinedload(RecipeTaskResult.logs))

        recipe_task_id = kw.get('recipe_task_id')
        if recipe_task_id:
            if isinstance(recipe_task_id, basestring):
                tasks = tasks.filter(RecipeTask.id == recipe_task_id)
            elif isinstance(recipe_task_id, list):
                tasks = tasks.filter(RecipeTask.id.in_(recipe_task_id))
        if 'recipe_id' in kw: #most likely we are coming here from a LinkRemoteFunction in recipe_widgets
            tasks = tasks.filter(Recipe.id == kw['recipe_id'])
            hidden = dict(distro_tree=1, system=1)
        if kw.get('distro_tree_id'):
            tasks =  tasks.join(Recipe.distro_tree) \
                    .filter(DistroTree.id == kw.get('distro_tree_id'))
            hidden = dict(distro_tree=1)
        elif kw.get('distro_id'):
            tasks = tasks.join(Recipe.distro_tree).join(DistroTree.distro) \
                    .filter(Distro.id == kw.get('distro_id'))
        if kw.get('task_id'):
            try:
                tasks = tasks.join(RecipeTask.task).filter(Task.id==kw.get('task_id'))
                hidden = dict(task = 1,
                             )
            except InvalidRequestError:
                return "<div>Invalid data:<br>%r</br></div>" % kw
        if kw.get('system_id'):
            tasks = tasks.join(
                    Recipe.resource.of_type(SystemResource),
                    SystemResource.system)\
                    .filter(System.id == kw.get('system_id'))\
                    .order_by(RecipeTask.id.desc())
            hidden = dict(system=1)
        if kw.get('job_id'):
            job_id = kw.get('job_id')
            if not isinstance(job_id, list):
                job_id = [job_id]
            tasks = tasks.filter(Job.id.in_(job_id))
        if kw.get('system'):
            tasks = tasks.join(RecipeResource)\
                    .filter(RecipeResource.fqdn.like('%%%s%%' % kw.get('system')))
        if kw.get('task'):
            # Shouldn't have to do this.  This only happens on the LinkRemoteFunction calls
            kw['task'] = kw.get('task').replace('%2F','/')
            tasks = tasks.filter(RecipeTask.name.like('%s' % kw.get('task').replace('*','%%')))
        if kw.get('version'):
            tasks = tasks.filter(RecipeTask.version.like(kw.get('version').replace('*', '%')))
        if kw.get('distro'):
            tasks = tasks.join(Recipe.distro_tree).join(DistroTree.distro) \
                    .filter(Distro.name.like('%%%s%%' % kw.get('distro')))
        if kw.get('arch_id'):
            tasks = tasks.join(Recipe.distro_tree).join(DistroTree.arch) \
                    .filter(Arch.id == kw.get('arch_id'))
        if kw.get('status'):
            tasks = tasks.filter(RecipeTask.status == kw['status'])
        if kw.get('is_failed'):
            tasks = tasks.filter(RecipeTask.is_failed())
        elif kw.get('result'):
            tasks = tasks.filter(RecipeTask.result == kw['result'])
        if kw.get('osmajor_id'):
            tasks.join(Recipe.distro_tree).join(DistroTree.distro) \
                .join(Distro.osversion) \
                .join(OSVersion.osmajor) \
                .filter(OSMajor.id == kw.get('osmajor_id'))
        if kw.get('whiteboard'):
            tasks = tasks.filter(Recipe.whiteboard==kw.get('whiteboard'))
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

    @expose(template='bkr.server.templates.task')
    def default(self, *args, **kw):
        # to handle the case one of the flask methods
        # have raised a 404 but the intention isn't to redirect
        # back to cherrypy, but legitimately 404
        if cherrypy.request.method != 'GET':
            raise cherrypy.HTTPError(404)
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
            raise cherrypy.HTTPError(status=404, message='%s' % e)

        attributes = task.to_dict()
        attributes['can_disable'] = bool(
            identity.current.user and identity.current.user.is_admin())

        return dict(attributes=attributes,
                    url="/tasks/%s" % task.id,
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

@app.route('/tasks', methods=['GET'])
def get_tasks():
    """
    Returns a pageable JSON collection of the task library in Beaker.
    Refer to :ref:`pageable-json-collections`.

    The following fields are supported for filtering and sorting:

    ``id``
        ID of the task.
    ``name``
        Name of the task.
    ``description``
        The description of the task provided in the loaded RPM.
    ``version``
        Version of the task provided in the loaded RPM.
    ``type``
        Type of the task, derived from the ``Type`` field in the task metadata.
    ``excluded_arch``
        Arch for which the task is excluded from. Tasks
        are applicable to all arches by default, unless specified
        otherwise in the ``Architectures`` field of the task metadata.
    ``excluded_osmajor``
        OS major version for which the task is excluded from.
        Tasks are applicable to all OS major versions by default,
        unless otherwise specified in the ``Releases`` field of
        the task metadata.
    """
    query = Task.query.filter(Task.valid == True).order_by(Task.name)
    json_result = json_collection(query, columns={
        'id': Task.id,
        'name': Task.name,
        'description': Task.description,
        'version': Task.version,
        'type': (Task.types, TaskType.type),
        'excluded_arch': (Task.excluded_arches, Arch.arch),
        'excluded_osmajor': (Task.excluded_osmajors, OSMajor.osmajor),
    })

    if request_wants_json():
        return jsonify(json_result)

    result = render_tg_template('bkr.server.templates.backgrid', {
        'title': 'Tasks Library',
        'grid_collection_type': 'TaskLibrary',
        'grid_collection_data': json_result,
        'grid_collection_url': request.base_url,
        'grid_view_type': 'TasksView',
    })
    return result

# This route is used whenever user enters any integer past /tasks/.
# Paths that don't match this template are rerouted by either default function or their specific function
# eq. path  .../tasks//custom/name/of/task - will NOT be picked up (processed by default function)
#           .../tasks/custom_name          - will NOT be picked up
#           .../tasks/name/with/slash      - will NOT be picked up
#           .../tasks/123456               - will be picked up
@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    # Dummy handler to fall back to CherryPy
    # so that other methods such as PATCH/DELETE work.
    # ---
    # Because Flask defined 404 has priority before CherryPy's 404,
    # message defined in here will be presented to user when CherryPy's 404 is raised.
    raise NotFound404('No such task with ID: %s' % task_id)

@app.route('/tasks/<int:task_id>', methods=['PATCH'])
@admin_auth_required
def update_task(task_id):
    """
    Updates a task - only handles disabling at this time.

    :param task_id: The task id to update/disable
    :jsonparam bool disabled: Whether the task should be disabled.
    :status 200: Task was successfully updated/disabled
    :status 404: Task was not found (to be disabled)
    """
    try:
        task = Task.by_id(task_id)
    except DatabaseLookupError as e:
        # This should be NotFound404 but due to still using cherrypy
        # 404's are handled there which then will then do a GET /tasks/id
        # which will resolve correctly, which isn't desired
        raise NotFound404('Task %s does not exist' % task_id)

    data = read_json_request(request)

    if data:
        with convert_internal_errors():
            if data.get('disabled', False) and task.valid:
                task.disable()

    response = jsonify(task.to_dict())

    return response

# for sphinx
tasks = Tasks
