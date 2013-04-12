#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, config
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bexceptions import *
import urlparse
#from turbogears.scheduler import add_interval_task

import cherrypy

from model import *
import string

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

        # Add the log to the DB if it hasn't been recorded yet.
        log_recipe = LogRecipeTask.lazy_create(parent=recipetask,
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

        log_recipe = LogRecipeTaskResult.lazy_create(parent=result,
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
    @identity.require(identity.not_anonymous())
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
                fqdn = unicode(recipe.resource.fqdn)
                if fqdn not in fqdns:
                    fqdns.append(fqdn)
        for role, tasks in task.peer_roles().iteritems():
            fqdns = roles.setdefault(unicode(role), [])
            for task in tasks:
                fqdn = unicode(task.recipe.resource.fqdn)
                if fqdn not in fqdns:
                    fqdns.append(fqdn)
        return roles
