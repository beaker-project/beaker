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
from datetime import datetime
from turbogears.database import session
from turbogears import expose, flash, widgets, redirect, paginate, url
from sqlalchemy import not_, and_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.common.bexceptions import BX
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.widgets import RecipeWidget
from bkr.server.widgets import SearchBar
from bkr.server import search_utility, identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link
from bkr.server.recipetasks import RecipeTasks
from bkr.server.controller_utilities import _custom_status, _custom_result
from datetime import timedelta
import urlparse

import cherrypy

from bkr.server.model import (Recipe, RecipeSet, TaskStatus, Job, System,
                              MachineRecipe, SystemResource, VirtResource,
                              VirtManager, LogRecipe, LogRecipeTask,
                              LogRecipeTaskResult)

import logging
log = logging.getLogger(__name__)

class Recipes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True
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

    log_types = dict(R = LogRecipe,
                     T = LogRecipeTask,
                     E = LogRecipeTaskResult,
                    )

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def by_log_server(self, server, limit=50):
        """
        Returns a list of recipe IDs which have logs stored on the given 
        server. By default, returns at most 50 at a time.

        Only returns recipes where the whole recipe set has completed. Also 
        excludes recently completed recipe sets, since the system may continue 
        uploading logs for a short while until beaker-provision powers it off.
        """
        finish_threshold = datetime.utcnow() - timedelta(minutes=2)
        recipes = Recipe.query.join(Recipe.recipeset)\
                .filter(RecipeSet.status.in_([s for s in TaskStatus if s.finished]))\
                .filter(not_(RecipeSet.recipes.any(Recipe.finish_time >= finish_threshold)))\
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
        if recipe.is_finished():
            raise BX('Cannot register file for finished recipe %s'
                    % recipe.t_id)

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
            except InvalidRequestError:
                raise BX(_("Invalid %s" % tid))
        mylog.server = server
        mylog.basepath = basepath
        return True

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def extend(self, recipe_id, kill_time):
        """
        Extend recipe watchdog by kill_time seconds
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        return recipe.extend(kill_time)

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
    @identity.require(identity.not_anonymous())
    def install_start(self, recipe_id=None):
        """
        Report comencement of provisioning of a recipe's resource, extend
        first task's watchdog, and report 'Install Started' against it.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID %s" % recipe_id))

        first_task = recipe.first_task
        if not recipe.resource.install_started:
            recipe.resource.install_started = datetime.utcnow()
            # extend watchdog by 3 hours 60 * 60 * 3
            kill_time = 10800
            # XXX In future releases where 'Provisioning'
            # is a valid recipe state, we will no longer
            # need the following block.
            log.debug('Extending watchdog for %s', first_task.t_id)
            first_task.extend(kill_time)
            log.debug('Recording /start for %s', first_task.t_id)
            first_task.pass_(path=u'/start', score=0, summary=u'Install Started')
            return True
        else:
            log.debug('Already recorded /start for %s', first_task.t_id)
            return False

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def postinstall_done(self, recipe_id=None):
        """
        Report completion of postinstallation
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_(u'Invalid Recipe ID %s' % recipe_id))
        recipe.resource.postinstall_finished = datetime.utcnow()
        return True


    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def install_done(self, recipe_id=None, fqdn=None):
        """
        Report completion of installation with current FQDN
        """
        if not recipe_id:
            raise BX(_("No recipe id provided!"))
        if not fqdn:
            raise BX(_("No fqdn provided!"))

        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID %s" % recipe_id))

        recipe.resource.install_finished = datetime.utcnow()
        # We don't want to change an existing FQDN, just set it
        # if it hasn't been set already (see BZ#879146)
        configured = recipe.resource.fqdn
        if configured is None:
            recipe.resource.fqdn = configured = fqdn
        elif configured != fqdn:
            # We use eager formatting here to make this easier to test
            log.info("Configured FQDN (%s) != reported FQDN (%s) in R:%s" %
                     (configured, fqdn, recipe_id))
        return configured

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def postreboot(self, recipe_id=None):
        # Backwards compat only, delete this after 0.10:
        # the recipe_id arg used to be hostname
        try:
            int(recipe_id)
        except ValueError:
            system = System.by_fqdn(recipe_id, identity.current.user)
            system.action_power('reboot', service=u'XMLRPC', delay=30)
            return system.fqdn

        try:
            recipe = Recipe.by_id(int(recipe_id))
        except (InvalidRequestError, NoResultFound, ValueError):
            raise BX(_('Invalid recipe ID %s') % recipe_id)
        if isinstance(recipe.resource, SystemResource):
            recipe.resource.system.action_power('reboot',
                    service=u'XMLRPC', delay=30)
        elif isinstance(recipe.resource, VirtResource):
            # XXX this should also be delayed 30 seconds but there is no way
            with VirtManager() as manager:
                vm = manager.api.vms.get(recipe.resource.system_name)
                vm.stop()
                vm.start()
        return True

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
                           label=_(u'Recipe Search'),    
                           simplesearch_label = 'Lookup ID',
                           table = search_utility.Recipe.search.create_search_table(),
                           complete_data = search_utility.Recipe.search.create_complete_search_table(),
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
            flash(_(u"Invalid recipe id %s" % recipe_id))
            redirect(url("/recipes"))
        PDC = widgets.PaginateDataGrid.Column
        fields = [PDC(name='fqdn', getter=lambda x: x.link, title='Name'),
            PDC(name='user', getter=lambda x: x.user.email_link if x.user else None, title='User'),]
        grid = myPaginateDataGrid(fields=fields)
        return dict(title='Recipe Systems', grid=grid, list=recipe.systems,
            search_bar=None)

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
                    recipe               = recipe)

# hack for Sphinx
recipes = Recipes
