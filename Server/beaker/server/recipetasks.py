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
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.widgets import myPaginateDataGrid
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *
from bexceptions import *
#from turbogears.scheduler import add_interval_task

import cherrypy

from model import *
import string

class RecipeTasks(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def upload_task_output(self, task_id, data):
        """
        upload the task output in pieces
        """
        raise NotImplementedError

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def expired(self):
        """ Return all expired tasks for this lab controller
            The lab controllers login with host/fqdn
        """
        try:
            lab_controller = identity.current.user.user_name.split('/')[1]
        except IndexError:
            raise BX(_('Invalid login: %s, must log in as lab controller' % identity.current.user))
        try:
            labcontroller = LabController.by_name(lab_controller)
        except InvalidRequestError:
            raise BX(_('Invalid lab_controller: %s' % lab_controller))
        return [('%s' % w.recipetask, '%s' % w.system) for w in Watchdog.expired(labcontroller)]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Start(self, task_id, watchdog_override):
        """
        Set task status to Running
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Start(watchdog_override)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Stop(self, task_id):
        """
        Set task status to Completed
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Stop()

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Pass(self, task_id, path, score, summary):
        """
        Record a Pass
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Pass(path, score, summary)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Warn(self, task_id, path, score, summary):
        """
        Record a Warn
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Warn(path, score, summary)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Fail(self, task_id, path, score, summary):
        """
        Record a Fail
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Fail(path, score, summary)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Panic(self, task_id, path, score, summary):
        """
        Record a Panic
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Panic(path, score, summary)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Abort(self, task_id, msg):
        """
        Set task status to Aborted
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Abort(msg)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Cancel(self, task_id, msg):
        """
        Set task status to Cancelled
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.Cancel(msg)

    @expose(format='json')
    def to_xml(self, id):
        taskxml = RecipeTask.by_id(id).to_xml().toprettyxml()
        return dict(xml=taskxml)
