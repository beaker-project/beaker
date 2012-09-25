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
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, config, url
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.widgets import RecipeWidget
from bkr.server.widgets import RecipeTasksWidget
from bkr.server.widgets import SearchBar
from bkr.server.widgets import RecipeActionWidget
from bkr.server import search_utility
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.recipetasks import RecipeTasks
from bkr.server.controller_utilities import _custom_status, _custom_result
from socket import gethostname
from bkr.upload import Uploader
import exceptions
import time
import urlparse

import cherrypy

from model import *
import string

import logging
log = logging.getLogger(__name__)

class Recipes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True
    action_widget = RecipeActionWidget()
    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to cancel?")
    message = widgets.TextArea(name='msg', label=_(u'Reason?'), help_text=_(u'Optional'))

    cancel_form = widgets.TableForm(
        'cancel_recipe',
        fields = [hidden_id, message, confirm],
        action = 'really_cancel',
        submit_text = _(u'Yes')
    )

    tasks = RecipeTasks()

    recipe_widget = RecipeWidget()
    recipe_tasks_widget = RecipeTasksWidget()

    upload = Uploader(config.get("basepath.logs", "/var/www/beaker/logs"))

    log_types = dict(R = LogRecipe,
                     T = LogRecipeTask,
                     E = LogRecipeTaskResult,
                    )

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def by_log_server(self, server, limit=50):
       """
       Return a list of recipes which have logs which belong to server
       default limit of 50 at a time.
       Only return recipes where the whole recipeset has completed.
       """
       recipes = Recipe.query.join(Recipe.recipeset)\
                        .filter(not_(RecipeSet.recipes.any(
                                               Recipe.finish_time == None)))\
                        .filter(Recipe.log_server == server)\
                        .limit(limit)
       return [recipe_id for recipe_id, in recipes.values(Recipe.id)]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def register_file(self, server, recipe_id, path, filename, basepath):
        """
        register file and return path to store
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))

        # Add the log to the DB if it hasn't been recorded yet.
        log_recipe = LogRecipe.lazy_create(parent=recipe,
                                           path=path,
                                           filename=filename,
                                          )
        log_recipe.server = server
        log_recipe.basepath = basepath
        # Pull log_server out of server_url.
        recipe.log_server = urlparse.urlparse(server)[1]
        return '%s' % recipe.filepath

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def files(self, recipe_id):
        """
        Return an array of logs for the given recipe.

        :param recipe_id: id of recipe
        :type recipe_id: integer

        .. deprecated:: 0.9.4
           Use :meth:`taskactions.files` instead.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        return [log for log in recipe.all_logs]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def change_files(self, recipe_id, server, basepath):
        """
        Change the server and basepath where the log files lives, Usually
         used to move from lab controller cache to archive storage.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        for mylog in recipe.all_logs:
            myserver = '%s/%s/' % (server, mylog['filepath'])
            mybasepath = '%s/%s/' % (basepath, mylog['filepath'])
            self.change_file(mylog['tid'], myserver, mybasepath)
        recipe.log_server = urlparse.urlparse(server)[1]
        return True

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def change_file(self, tid, server, basepath):
        """
        Change the server and basepath where the log file lives, Usually
         used to move from lab controller cache to archive storage.
        """
        log_type, log_id = tid.split(":")
        if log_type.upper() in self.log_types.keys():
            try:
                mylog = self.log_types[log_type.upper()].by_id(log_id)
            except InvalidRequestError, e:
                raise BX(_("Invalid %s" % tid))
        mylog.server = server
        mylog.basepath = basepath
        return True

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def upload_file(self, recipe_id, path, filename, size, md5sum, offset, data):
        """
        upload to recipe in pieces 
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))

        # Add the log to the DB if it hasn't been recorded yet.
        LogRecipe.lazy_create(parent=recipe,
                              path=path,
                              filename=filename,
                             )
        return self.upload.uploadFile("%s/%s" % (recipe.filepath, path), 
                                      filename, 
                                      size, 
                                      md5sum, 
                                      offset, 
                                      data)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def stop(self, recipe_id, stop_type, msg=None):
        """
        Set recipe status to Completed
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        if stop_type not in recipe.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, recipe.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(recipe,stop_type)(**kwargs)

    @cherrypy.expose
    def to_xml(self, recipe_id=None):
        """ 
            Pass in recipe id and you'll get that recipe's xml
        """
        if not recipe_id:
            raise BX(_("No recipe id provided!"))
        try:
           recipexml = Recipe.by_id(recipe_id).to_xml().toprettyxml()
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID %s" % recipe_id))
        return recipexml

    def _recipe_search(self,recipe,**kw):
        recipe_search = search_utility.Recipe.search(recipe)
        for search in kw['recipesearch']:
            col = search['table']      
            try:
                recipe_search.append_results(search['value'],col,search['operation'],**kw)
            except KeyError,e:
                log.error(e)
                return recipe_search.return_results()

        return recipe_search.return_results()

    def _recipes(self,recipe,**kw):
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
            recipes_found = self._recipe_search(recipe,**kw)
            return_dict.update({'recipes_found':recipes_found})
            return_dict.update({'searchvalue':searchvalue})
            return_dict.update({'simplesearch':simplesearch})
        return return_dict

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-id', limit=50)
    def index(self, *args,**kw):
        return self.recipes(recipes=session.query(Recipe).filter_by(
                type='machine_recipe'), *args, **kw)

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='-id', limit=50)
    def mine(self,*args,**kw):
        return self.recipes(recipes=MachineRecipe.mine(identity.current.user),
                action='./mine', *args, **kw)

    def recipes(self,recipes,action='.',*args, **kw):
        recipes = recipes.filter(Recipe.recipeset.has(
            RecipeSet.job.has(and_(
            Job.deleted == None, Job.to_delete == None))))
        recipes_return = self._recipes(recipes,**kw)
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
                PDC(name='system.fqdn',
                    getter=lambda x: x.system and x.system.link,
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
                PDC(name='action', getter=lambda x:self.action_widget(x),
                    title='Action', options=dict(sortable=False)),])

        search_bar = SearchBar(name='recipesearch',
                           label=_(u'Recipe Search'),    
                           simplesearch_label = 'Lookup ID',
                           table = search_utility.Recipe.search.create_search_table(),
                           complete_data = search_utility.Recipe.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_recipe"), 
                           quick_searches = [('Status-is-Queued','Queued'),('Status-is-Running','Running'),('Status-is-Completed','Completed')])
        return dict(title="Recipes", 
                    object_count=recipes.count(),
                    grid=recipes_grid, 
                    list=recipes,
                    search_bar=search_bar,
                    action=action,
                    options=search_options,
                    searchvalue=searchvalue)

    @expose(template="bkr.server.templates.recipe")
    def default(self, id):
        try:
            recipe = Recipe.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid recipe id %s" % id))
            redirect(".")
        if recipe.is_deleted():
            flash(_(u"Invalid %s, has been deleted" % recipe.t_id))
            redirect(".")
        return dict(title   = 'Recipe',
                    recipe_widget        = self.recipe_widget,
                    recipe_tasks_widget  = self.recipe_tasks_widget,
                    recipe               = recipe)

# hack for Sphinx
recipes = Recipes
