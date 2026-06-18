
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import cherrypy
from sqlalchemy import not_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from turbogears import expose, flash, widgets, redirect, paginate
from bkr.server.database import session
from bkr.server.util import url
from bkr.server.widgets import myPaginateDataGrid, RecipeWidget, SearchBar
from bkr.server import search_utility, identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link
from bkr.server.bexceptions import BX
from bkr.server.controller_utilities import _custom_status, _custom_result
from bkr.server.model import (Recipe, RecipeSet, TaskStatus, Job,
                              LogRecipe, LogRecipeTask, LogRecipeTaskResult,
                              MachineRecipe)
from bkr.server.rpc.recipes import Recipes as RecipesRPC
from bkr.server.legacy.recipetasks import RecipeTasks

logger = logging.getLogger(__name__)


class Recipes(RPCRoot, RecipesRPC):
    exposed = True

    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to release the system?")
    return_reservation_form = widgets.TableForm(
        'end_recipe_reservation',
        fields = [hidden_id, confirm],
        action = './really_return_reservation',
        submit_text = u'Yes'
    )

    tasks = RecipeTasks()

    recipe_widget = RecipeWidget()

    log_types = dict(R = LogRecipe,
                     T = LogRecipeTask,
                     E = LogRecipeTaskResult,
                    )

    @identity.require(identity.not_anonymous())
    @expose()
    def really_return_reservation(self, id, msg=None):
        try:
            recipe = Recipe.by_id(id)
        except InvalidRequestError:
            raise BX("Invalid Recipe ID %s" % id)
        recipe.return_reservation()

        flash(u"Successfully released reserved system for %s" % recipe.t_id)
        redirect('/jobs/mine')

    @expose(template="bkr.server.templates.form")
    @identity.require(identity.not_anonymous())
    def return_reservation(self, recipe_id=None):
        """
        End recipe reservation
        """
        if not recipe_id:
            raise BX("No recipe id provided!")

        return dict(
            title = 'Release reserved system for Recipe %s' % recipe_id,
            form = self.return_reservation_form,
            action = './really_return_reservation',
            options = {},
            value = dict(id=recipe_id),
        )

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-id', limit=50)
    def index(self, *args, **kw):
        return self.recipes(recipes=session.query(Recipe).filter_by(
                type='machine_recipe'), *args, **kw)

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-id', limit=50)
    def mine(self, *args, **kw):
        return self.recipes(recipes=MachineRecipe.mine(identity.current.user),
                action='./mine', *args, **kw)

    def recipes(self, recipes, action='.', *args, **kw):
        recipes = recipes.join(Recipe.recipeset)\
            .join(RecipeSet.job)\
            .filter(not_(Job.is_deleted))
        recipes_return = self._recipes(recipes, **kw)
        searchvalue = None
        search_options = {}
        if recipes_return:
            if 'recipes_found' in recipes_return:
                recipes = recipes_return['recipes_found']
            if 'searchvalue' in recipes_return:
                searchvalue = recipes_return['searchvalue']
            if 'simplesearch' in recipes_return:
                search_options['simplesearch'] = recipes_return['simplesearch']
        PDC = widgets.PaginateDataGrid.Column
        recipes_grid = myPaginateDataGrid(
            fields=[
                PDC(name='id',
                    getter=lambda x:make_link(url='./%s' % x.id, text=x.t_id),
                    title='ID', options=dict(sortable=True)),
                PDC(name='whiteboard',
                    getter=lambda x:x.whiteboard, title='Whiteboard',
                    options=dict(sortable=True)),
                PDC(name='distro_tree.arch.arch',
                    getter=lambda x:x.arch, title='Arch',
                    options=dict(sortable=True)),
                PDC(name='resource.fqdn',
                    getter=lambda x: x.resource and x.resource.link,
                    title='System', options=dict(sortable=True)),
                PDC(name='distro_tree.distro.name',
                    getter=lambda x: x.distro_tree and x.distro_tree.link,
                    title='Distro Tree', options=dict(sortable=False)),
                PDC(name='progress',
                    getter=lambda x: x.progress_bar,
                    title='Progress', options=dict(sortable=False)),
                PDC(name='status',
                    getter=_custom_status, title='Status',
                    options=dict(sortable=True)),
                PDC(name='result',
                    getter=_custom_result, title='Result',
                    options=dict(sortable=True)),
                PDC(name='action', getter=lambda x:self.action_cell(x),
                    title='Action', options=dict(sortable=False)),])

        search_bar = SearchBar(name='recipesearch',
                           label=u'Recipe Search',
                           simplesearch_label = 'Lookup ID',
                           table = search_utility.Recipe.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_recipe"),
                           quick_searches = [('Status-is-Queued','Queued'),('Status-is-Running','Running'),('Status-is-Completed','Completed')])
        return dict(title="Recipes",
                    grid=recipes_grid,
                    list=recipes,
                    search_bar=search_bar,
                    action=action,
                    options=search_options,
                    searchvalue=searchvalue)

    def action_cell(self, recipe):
        return make_link(recipe.clone_link(), 'Clone RecipeSet', elem_class='btn')

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def systems(self, recipe_id=None, *args, **kw):
        try:
            recipe = Recipe.by_id(recipe_id)
        except NoResultFound:
            flash(u"Invalid recipe id %s" % recipe_id)
            redirect(url("/recipes"))
        PDC = widgets.PaginateDataGrid.Column
        fields = [PDC(name='fqdn', getter=lambda x: x.link, title='Name'),
                  PDC(name='loanedto', getter=lambda x: x.loaned.user_name if x.loaned else None, title='Loaned'),
                  PDC(name='user', getter=lambda x: x.user.email_link if x.user else None, title='User'),]
        grid = myPaginateDataGrid(fields=fields)
        return dict(title='Recipe Systems', grid=grid, list=recipe.systems,
            search_bar=None)

    @expose(template="bkr.server.templates.recipe-old")
    def default(self, id, *args, **kwargs):
        # When flask returns a 404, it falls back to here so we need to
        # raise a cherrypy 404.
        if cherrypy.request.method == 'POST':
            raise cherrypy.HTTPError(404)
        if args:
            raise cherrypy.HTTPError(404)
        if cherrypy.request.path.endswith('/'):
            raise cherrypy.HTTPError(404)
        try:
            recipe = Recipe.by_id(id)
        except InvalidRequestError:
            flash(u"Invalid recipe id %s" % id)
            redirect(".")
        if recipe.is_deleted:
            flash(u"Invalid %s, has been deleted" % recipe.t_id)
            redirect(".")
        if recipe.is_finished() or recipe.status == TaskStatus.reserved:
            recipe.set_reviewed_state(identity.current.user, True)
        return dict(title   = 'Recipe',
                    recipe_widget        = self.recipe_widget,
                    recipe               = recipe)

    def _recipe_search(self, recipe, **kw):
        recipe_search = search_utility.Recipe.search(recipe)
        for search in kw['recipesearch']:
            col = search['table']
            try:
                recipe_search.append_results(search['value'], col, search['operation'], **kw)
            except KeyError as e:
                logger.error(e)
                return recipe_search.return_results()

        return recipe_search.return_results()

    def _recipes(self, recipe, **kw):
        return_dict = {}
        # We can do a quick search, or a regular simple search. 
        # If we have done neither of these, it will fall back to 
        # an advanced search and look in the 'recipesearch'
        # simplesearch set to None will display the advanced search, 
        # otherwise in the simplesearch textfield it will display 
        # the value assigned to it
        simplesearch = None
        if kw.get('simplesearch'):
            value = kw['simplesearch']
            kw['recipesearch'] = [{'table' : 'Id',
                                   'operation' : 'is',
                                   'value' : value}]
            simplesearch = value
        if kw.get("recipesearch"):
            if 'quick_search' in kw['recipesearch']:
                table,op,value = kw['recipesearch']['quick_search'].split('-')
                kw['recipesearch'] = [{'table' : table,
                                       'operation' : op,
                                       'value' : value}]
                simplesearch = ''
            searchvalue = kw['recipesearch']
            recipes_found = self._recipe_search(recipe, **kw)
            return_dict.update({'recipes_found':recipes_found})
            return_dict.update({'searchvalue':searchvalue})
            return_dict.update({'simplesearch':simplesearch})
        return return_dict
