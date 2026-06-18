
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import logging

import cherrypy
from sqlalchemy import not_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import joinedload
from turbogears import expose, flash, widgets, validate, redirect, paginate
from bkr.server.database import session
from bkr.server.util import url
from bkr.server import identity
from bkr.server.widgets import TasksWidget, TaskSearchForm, \
        TaskActionWidget, HorizontalForm
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.model import (Distro, Task, OSMajor, Recipe, RecipeSet,
                              RecipeTask, DistroTree, Job, Arch, OSVersion,
                              RecipeTaskResult, System,
                              SystemResource, RecipeResource)
from bkr.common.helpers import siphon
from bkr.server.rpc.tasks import Tasks as TasksRPC

import six


log = logging.getLogger(__name__)


class Tasks(RPCRoot, TasksRPC):
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
        submit_text = u'Upload'
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

    @expose()
    @identity.require(identity.not_anonymous())
    def save(self, task_rpm, *args, **kw):
        """
        TurboGears method to upload task rpm package
        """
        rpm_path = Task.get_rpm_path(task_rpm.filename)

        if not task_rpm.filename:
            flash(u'No task RPM specified')
            redirect(url("./new"))

        # we do it here, since we do not want to proceed
        # any further
        if len(task_rpm.filename) > 255:
            flash(u"Task RPM name should be <= 255 characters")
            redirect(url("./new"))

        if os.path.exists("%s" % rpm_path):
            flash(u'Failed to import because we already have %s' % task_rpm.filename )
            redirect(url("./new"))

        try:
            def write_data(f):
                siphon(task_rpm.file, f)
            task = Task.update_task(task_rpm.filename, write_data)
        except Exception as err:
            session.rollback()
            log.exception('Failed to import %s', task_rpm.filename)
            flash(u'Failed to import task: %s' % err)
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
            if isinstance(recipe_task_id, six.string_types):
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
