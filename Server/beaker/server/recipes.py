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

class Recipes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

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
		     widgets.PaginateDataGrid.Column(name='arch', getter=lambda x:x.arch, title='Arch', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='system', getter=lambda x: make_system_link(x.system), title='System', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='distro', getter=lambda x: make_distro_link(x.distro), title='Distro', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
                    ])
        return dict(title="Recipes", grid=recipes_grid, list=recipes, search_bar=None)

def new_recipes(*args):
    for recipe in Recipe.query().filter(
            Recipe.status==TestStatus.by_name(u'New')):
        if recipe.distro:
            systems = recipe.distro.systems_filter(
                                        recipe.recipeset.job.owner,
                                        recipe.host_requires)
            # Don't add ystems from lab controllers where we have already tried
            if recipe.recipeset.lab_controllers:
                systems = systems.filter(
                                     not_(
                                    System.lab_controller.in_(
                                       recipe.recipeset.lab_controllers
                                                             )
                                         )
                                        )
            recipe.possible_systems = []
            for system in systems:
                # Don't add the same host twice to the same recipeSet.
                for peer_recipe in recipe.recipeset.recipes:
                    if system in peer_recipe.possible_systems:
                        break
                else:
                    # Add matched systems to recipe.
                    recipe.possible_systems.append(system)
            if recipe.possible_systems:
                recipe.status = TestStatus.by_name(u'Queued')
                print "recipe ID %s moved from New to Queued" % recipe.id
            else:
                #FIXME Do this properly
                recipe.status = TestStatus.by_name(u'Aborted')
                print "recipe ID %s moved from New to Aborted" % recipe.id
        else:
            #FIXME Do this properly
            recipe.status = TestStatus.by_name(u'Aborted')
    session.flush()

def queued_recipes(*args):
    recipes = Recipe.query()\
                    .join('status')\
                    .join('possible_systems')\
                    .filter(
                        and_(Recipe.status==TestStatus.by_name(u'Queued'),
                             System.user==None
                            )
                           )
    for recipe in recipes:
        system = recipe.free_systems
        if recipe.recipeset.lab_controller:
            # First recipe of a recipeSet determines the lab_controller
            system = system.filter(
                         System.lab_controller==recipe.recipeset.lab_controller
                                  )
        system = system.first()
        if system:
            # Atomic operation to put recipe in Scheduled state
            if session.connection(Recipe).execute(recipe_table.update(
                 and_(recipe_table.c.id==recipe.id,
                   recipe_table.c.status_id==TestStatus.by_name(u'Queued').id)),
                   status_id=TestStatus.by_name(u'Scheduled').id).rowcount == 1:
                # Atomic operation to reserve the system
                if session.connection(System).execute(system_table.update(
                     and_(system_table.c.id==system.id,
                      system_table.c.user_id==None)),
                      user_id=recipe.recipeset.job.owner.user_id).rowcount == 1:
                    recipe.system = system
                    recipe.recipeset.lab_controller = system.lab_controller
                    recipe.possible_systems = []
                    if system.lab_controller not in recipe.recipeset.lab_controllers:
                        recipe.recipeset.lab_controllers.append(system.lab_controller)
                    print "recipe ID %s moved from Queued to Scheduled" % recipe.id
                else:
                    # The system was taken from underneath us.  Put recipe
                    # back into queued state and try again.
                    recipe.status = TestStatus.by_name(u'Queued')
            else:
                #Some other thread beat us. Skip this recipe now.
                # Depending on scheduler load it should be safe to run multiple
                # Queued processes..  Also, systems that we don't directly
                # control, for example, systems at a remote location that can
                # pull jobs but not have any pushed onto them.  These systems
                # could take a recipe and put it in running state. Not sure how
                # to deal with multi-host jobs at remote locations.  May need to
                # enforce single recipes for remote execution.
                pass
    session.flush()

def schedule():
    add_interval_task(action=new_recipes,
                      args=[lambda:datetime.now()],
                      interval=20)
    add_interval_task(action=queued_recipes,
                      args=[lambda:datetime.now()],
                      interval=20,
                      initialdelay=5)

