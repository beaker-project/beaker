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
from turbogears.scheduler import add_interval_task

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

    def set_status(self, task_id, status):
        """
        Set Task Status
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        recipe.status = TaskStatus.by_name(status)
        return

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def start(self, recipe_id):
        """
        Set recipe status to Running
        """
        return self.set_status(recipe_id, u'Running')

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def abort(self, recipe_id):
        """
        Set recipe status to Aborted
        """
        return self.set_status(recipe_id, u'Aborted')

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def cancel(self, recipe_id):
        """
        Set recipe status to Cancelled
        """
        return self.set_status(recipe_id, u'Cancelled')

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def finish(self, recipe_id):
        """
        Set recipe status to Finished
        """
        return self.set_status(recipe_id, u'Completed')

    @expose(format='json')
    def to_xml(self, id):
        recipexml = Recipe.by_id(id).to_xml().toprettyxml()
        return dict(xml=recipexml)

    @expose(template='beaker.server.templates.grid')
    @paginate('list',default_order='id')
    def index(self, *args, **kw):
        recipes = session.query(MachineRecipe).order_by(recipe_table.c.id.desc())
        recipes_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='id', getter=lambda x:x.id, title='ID', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='whiteboard', getter=lambda x:x.whiteboard, title='Whiteboard', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='arch', getter=lambda x:x.arch, title='Arch', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='system', getter=lambda x: make_system_link(x.system), title='System', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='distro', getter=lambda x: make_distro_link(x.distro), title='Distro', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='progress', getter=lambda x: make_progress_bar(x), title='Progress', options=dict(sortable=False)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
                    ])
        return dict(title="Recipes", grid=recipes_grid, list=recipes, search_bar=None)
