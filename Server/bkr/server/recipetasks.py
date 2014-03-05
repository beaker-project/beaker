
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
#from bkr.server.helpers import *
from bkr.common.bexceptions import BX
import urlparse
#from turbogears.scheduler import add_interval_task

import cherrypy

from bkr.server.model import (RecipeTask, LogRecipeTask,
                              RecipeTaskResult, LogRecipeTaskResult,
                              LabController, Watchdog)

class RecipeTasks(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def register_file(self, server, task_id, path, filename, basepath):
        """
        register file and return path to store
        """
        try:
            recipetask = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        if recipetask.is_finished():
            raise BX('Cannot register file for finished task %s'
                    % recipetask.t_id)

        # Add the log to the DB if it hasn't been recorded yet.
        log_recipe = LogRecipeTask.lazy_create(recipe_task_id=recipetask.id,
                                               path=path, 
                                               filename=filename,
                                              )
        log_recipe.server = server
        log_recipe.basepath = basepath
        recipetask.recipe.log_server = urlparse.urlparse(server)[1]
        return '%s' % recipetask.filepath

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def register_result_file(self, server, result_id, path, filename, basepath):
        """
        register file and return path to store
        """
        try:
            result = RecipeTaskResult.by_id(result_id)
        except InvalidRequestError:
            raise BX(_('Invalid result ID: %s' % result_id))
        if result.recipetask.is_finished():
            raise BX('Cannot register file for finished task %s'
                    % result.recipetask.t_id)

        log_recipe = LogRecipeTaskResult.lazy_create(recipe_task_result_id=result.id,
                                                     path=path, 
                                                     filename=filename,
                                                    )
        log_recipe.server = server
        log_recipe.basepath = basepath
        result.recipetask.recipe.log_server = urlparse.urlparse(server)[1]
        return '%s' % result.filepath


    @cherrypy.expose
    def watchdogs(self, status='active',lc=None):
        """ Return all active/expired tasks for this lab controller
            The lab controllers login with host/fqdn
        """
        # TODO work on logic that determines whether or not originator
        # was qpid or kobo ?
        if lc is None:
            try:
                labcontroller = identity.current.user.lab_controller
            except AttributeError:
                raise BX(_('No lab controller passed in and not currently logged in'))

            if not labcontroller:
                raise BX(_(u'Invalid login: %s, must log in as a lab controller' % identity.current.user))
        else:
            try:
                labcontroller = LabController.by_name(lc)
            except InvalidRequestError:
                raise BX(_(u'Invalid lab controller: %s' % lc))

        return [dict(recipe_id = w.recipe.id,
                        system = w.recipe.resource.fqdn) for w in Watchdog.by_status(labcontroller, status)]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def start(self, task_id, watchdog_override=None):
        """
        Set task status to Running
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.start(watchdog_override)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def extend(self, task_id, kill_time):
        """
        Extend tasks watchdog by kill_time seconds
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.extend(kill_time)

    @cherrypy.expose
    def watchdog(self, task_id):
        """
        Returns number of seconds left on task_id watchdog, or False if it doesn't exist.
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.status_watchdog()

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def stop(self, task_id, stop_type, msg=None):
        """
        Set task status to Completed
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        if stop_type not in task.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, task.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(task,stop_type)(**kwargs)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def update(self, task_id, data):
        """
        XML-RPC method used by the lab controller harness API to update 
        a recipe-task's attributes.
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        if 'name' in data:
            task.name = data['name']
        if 'version' in data:
            task.version = data['version']
        return task.__json__()

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def result(self, task_id, result_type, path=None, score=None, summary=None):
        """
        Record a Result
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        if result_type not in task.result_types:
            raise BX(_('Invalid result_type: %s, must be one of %s' %
                             (result_type, task.result_types)))
        kwargs = dict(path=path, score=score, summary=summary)
        return getattr(task,result_type)(**kwargs)

    @expose(format='json')
    def to_xml(self, id):
        taskxml = RecipeTask.by_id(id).to_xml().toprettyxml()
        return dict(xml=taskxml)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def peer_roles(self, task_id):
        try:
            task = RecipeTask.by_id(task_id)
        except NoResultFound:
            raise BX(_('Invalid task ID: %s') % task_id)
        # don't use set, we want to preserve ordering
        roles = {}
        for role, recipes in task.recipe.peer_roles().iteritems():
            fqdns = roles.setdefault(unicode(role), [])
            for recipe in recipes:
                if not recipe.resource or not recipe.resource.fqdn:
                    continue
                fqdn = unicode(recipe.resource.fqdn)
                if fqdn not in fqdns:
                    fqdns.append(fqdn)
        for role, tasks in task.peer_roles().iteritems():
            fqdns = roles.setdefault(unicode(role), [])
            for task in tasks:
                if not task.recipe.resource or not task.recipe.resource.fqdn:
                    continue
                fqdn = unicode(task.recipe.resource.fqdn)
                if fqdn not in fqdns:
                    fqdns.append(fqdn)
        return roles
