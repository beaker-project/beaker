
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from datetime import datetime
from lxml import etree
from turbogears.database import session
from turbogears import expose, flash, widgets, redirect, paginate, url
from sqlalchemy import not_, and_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.common.bexceptions import BX
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.widgets import RecipeWidget
from bkr.server.widgets import SearchBar
from bkr.server import search_utility, identity, dynamic_virt
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link
from bkr.server.recipetasks import RecipeTasks
from bkr.server.reserve_workflow import MAX_SECONDS_PROVISION, MAX_HOURS_PROVISION
from bkr.server.controller_utilities import _custom_status, _custom_result
from bkr.server.junitxml import recipe_to_junit_xml
from datetime import timedelta
import urlparse

import cherrypy

from bkr.server.model import (Recipe, RecipeSet, TaskStatus, Job, System,
                              MachineRecipe, SystemResource, VirtResource,
                              LogRecipe, LogRecipeTask, LogRecipeTaskResult,
                              RecipeResource, TaskBase, RecipeReservationRequest,
                              RecipeReservationCondition)
from bkr.server.app import app
from bkr.server.flask_util import BadRequest400, NotFound404, \
    Forbidden403, auth_required, read_json_request, convert_internal_errors, \
    request_wants_json, render_tg_template, stringbool
from flask import request, jsonify, redirect as flask_redirect, make_response
from bkr.server.bexceptions import BeakerException

import logging
import lxml.etree
logger = logging.getLogger(__name__)

class Recipes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to release the system?")
    return_reservation_form = widgets.TableForm(
        'end_recipe_reservation',
        fields = [hidden_id, confirm],
        action = './really_return_reservation',
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
                .join(RecipeSet.job)\
                .filter(not_(Job.is_deleted))\
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
            recipe = Recipe.by_id(recipe_id, lockmode='update')
        except NoResultFound:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        if recipe.is_finished():
            raise BX('Cannot register file for finished recipe %s'
                    % recipe.t_id)

        # Add the log to the DB if it hasn't been recorded yet.
        log_recipe = LogRecipe.lazy_create(recipe_id=recipe.id,
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
           Use :meth:`taskactions.files() <bkr.server.task_actions.taskactions.files>` instead.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        # Build a list of logs excluding duplicate paths, to mitigate:
        # https://bugzilla.redhat.com/show_bug.cgi?id=963492
        logdicts = []
        seen_paths = set()
        for log in recipe.all_logs():
            logdict = log.dict
            # The path we care about here is the path which beaker-transfer 
            # will move the file to.
            # Don't be tempted to use os.path.join() here since log['path'] 
            # is often '/' which does not give the result you would expect.
            path = os.path.normpath('%s/%s/%s' % (logdict['filepath'],
                    logdict['path'], logdict['filename']))
            if path in seen_paths:
                logger.warn('%s contains duplicate log %s', log.parent.t_id, path)
            else:
                seen_paths.add(path)
                logdicts.append(logdict)
        return logdicts

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def change_files(self, recipe_id, server, basepath):
        """
        Change the server and basepath where the log files lives, Usually
         used to move from lab controller cache to archive storage.
        """
        try:
            recipe = Recipe.by_id(recipe_id, lockmode='update')
        except NoResultFound:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        for mylog in recipe.all_logs():
            mylog.server = '%s/%s/' % (server, mylog.parent.filepath)
            mylog.basepath = '%s/%s/' % (basepath, mylog.parent.filepath)
        recipe.log_server = urlparse.urlparse(server)[1]
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
    def console_output(self, recipe_id, output_length=None, offset=None):
        """
        Get text console log output from OpenStack 
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        manager = dynamic_virt.VirtManager(recipe.recipeset.job.owner)
        return manager.get_console_output(recipe.resource.instance_id, output_length)

    @cherrypy.expose
    def watchdog(self, recipe_id):
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        return recipe.status_watchdog()

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
        Records the start of a recipe's installation. The watchdog is extended 
        by 3 hours to allow the installation to complete.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID %s" % recipe_id))
        if not recipe.installation:
            raise BX(_('Recipe %s not provisioned yet') % recipe_id)

        installation = recipe.installation
        if not installation.install_started:
            installation.install_started = datetime.utcnow()
            # extend watchdog by 3 hours 60 * 60 * 3
            kill_time = 10800
            logger.debug('Extending watchdog for %s', recipe.t_id)
            recipe.extend(kill_time)
            return True
        else:
            logger.debug('Already recorded install_started for %s', recipe.t_id)
            return False

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def install_fail(self, recipe_id=None):
        """
        Records the fail of a recipe's installation.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID {}".format(recipe_id)))  # noqa: F821
        if not recipe.installation:
            raise BX(_("Recipe {} not provisioned yet".format(recipe_id)))  # noqa: F821

        return recipe.abort('Installation failed')

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
        if not recipe.installation:
            raise BX(_('Recipe %s not provisioned yet') % recipe_id)
        recipe.installation.postinstall_finished = datetime.utcnow()
        return True


    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def install_done(self, recipe_id=None, fqdn=None):
        """
        Report completion of installation with current FQDN
        """
        if not recipe_id:
            raise BX(_("No recipe id provided!"))

        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID %s" % recipe_id))
        if not recipe.installation:
            raise BX(_('Recipe %s not provisioned yet') % recipe_id)

        recipe.installation.install_finished = datetime.utcnow()
        # We don't want to change an existing FQDN, just set it
        # if it hasn't been set already (see BZ#879146)
        configured = recipe.resource.fqdn
        if configured is None and fqdn:
            recipe.resource.fqdn = configured = fqdn
        elif configured != fqdn:
            # We use eager formatting here to make this easier to test
            logger.info("Configured FQDN (%s) != reported FQDN (%s) in R:%s" %
                     (configured, fqdn, recipe_id))
        return configured

    @identity.require(identity.not_anonymous())
    @expose()
    def really_return_reservation(self, id, msg=None):
        try:
            recipe = Recipe.by_id(id)
        except InvalidRequestError:
            raise BX(_("Invalid Recipe ID %s" % id))
        recipe.return_reservation()

        flash(_(u"Successfully released reserved system for %s" % recipe.t_id))
        redirect('/jobs/mine')

    @expose(template="bkr.server.templates.form")
    @identity.require(identity.not_anonymous())
    def return_reservation(self, recipe_id=None):
        """
        End recipe reservation
        """
        if not recipe_id:
            raise BX(_("No recipe id provided!"))

        return dict(
            title = 'Release reserved system for Recipe %s' % recipe_id,
            form = self.return_reservation_form,
            action = './really_return_reservation',
            options = {},
            value = dict(id=recipe_id),
        )

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
        return True

    @cherrypy.expose
    def to_xml(self, recipe_id=None):
        """ 
            Pass in recipe id and you'll get that recipe's xml
        """
        if not recipe_id:
            raise BX(_("No recipe id provided!"))
        try:
            recipexml = etree.tostring(Recipe.by_id(recipe_id).to_xml(),
                                       pretty_print=True, encoding='utf8')
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
                logger.error(e)
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
        recipes = recipes.join(Recipe.recipeset)\
            .join(RecipeSet.job)\
            .filter(not_(Job.is_deleted))
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
            flash(_(u"Invalid recipe id %s" % recipe_id))
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
            flash(_(u"Invalid recipe id %s" % id))
            redirect(".")
        if recipe.is_deleted:
            flash(_(u"Invalid %s, has been deleted" % recipe.t_id))
            redirect(".")
        if recipe.is_finished() or recipe.status == TaskStatus.reserved:
            recipe.set_reviewed_state(identity.current.user, True)
        return dict(title   = 'Recipe',
                    recipe_widget        = self.recipe_widget,
                    recipe               = recipe)

def _get_recipe_by_id(id):
    """Get recipe by id, reporting HTTP 404 if the recipe is not found"""
    try:
        return Recipe.by_id(id)
    except NoResultFound:
        raise NotFound404('Recipe not found')

@app.route('/recipes/<int:id>', methods=['GET'])
def get_recipe(id):
    """
    Provides detailed information about a recipe in JSON format.

    :param id: Recipe's id.
    """
    recipe = _get_recipe_by_id(id)
    if identity.current.user and (recipe.is_finished()
                                  or recipe.status == TaskStatus.reserved):
        recipe.set_reviewed_state(identity.current.user, True)
    if request_wants_json():
        return jsonify(recipe.to_json(include_recipeset=True))
    if identity.current.user and identity.current.user.use_old_job_page:
        return NotFound404('Fall back to old recipe page')
    return render_tg_template('bkr.server.templates.recipe', {
        'title': recipe.t_id,
        'recipe': recipe,
    })

@app.route('/recipes/<int:id>.xml', methods=['GET'])
def recipe_xml(id):
    """
    Returns the recipe in Beaker results XML format.

    :status 200: The recipe xml file was successfully generated.
    """
    recipe = _get_recipe_by_id(id)
    include_logs = request.args.get('include_logs', type=stringbool, default=True)
    xmlstr = lxml.etree.tostring(
            recipe.to_xml(clone=False, include_logs=include_logs),
            pretty_print=True, encoding='utf8')
    response = make_response(xmlstr)
    response.status_code = 200
    response.headers.add('Content-Type', 'text/xml; charset=utf-8')
    return response

@app.route('/recipes/<int:id>.junit.xml', methods=['GET'])
def recipe_junit_xml(id):
    """
    Returns the recipe in JUnit-compatible XML format.
    """
    recipe = _get_recipe_by_id(id)
    response = make_response(recipe_to_junit_xml(recipe))
    response.status_code = 200
    response.headers.add('Content-Type', 'text/xml; charset=utf-8')
    return response

def _record_activity(recipe, field, old, new, action=u'Changed'):
    recipe.record_activity(user=identity.current.user, service=u'HTTP',
            action=action, field=field, old=old, new=new)

@app.route('/recipes/<int:id>', methods=['PATCH'])
@auth_required
def update_recipe(id):
    """
    Updates the attributes of a recipe. The request must be 
    :mimetype:`application/json`.

    :param id: Recipe's id.
    :jsonparam string whiteboard: Whiteboard of the recipe.
    :status 200: Recipe was updated.
    :status 400: Invalid data was given.
    """

    recipe = _get_recipe_by_id(id)
    if not recipe.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit recipe %s' % recipe.id)
    data = read_json_request(request)
    with convert_internal_errors():
        if 'whiteboard' in data:
            new_whiteboard = data['whiteboard']
            if new_whiteboard != recipe.whiteboard:
                _record_activity(recipe, u'Whiteboard', recipe.whiteboard,
                    new_whiteboard)
                recipe.whiteboard = new_whiteboard
        if 'reviewed' in data:
            recipe.set_reviewed_state(identity.current.user, bool(data['reviewed']))
    return jsonify(recipe.__json__())

@app.route('/recipes/<int:id>/logs/<path:path>', methods=['GET'])
def get_recipe_log(id, path):
    """
    Redirects to the actual storage location for the requested recipe log.

    :param id: Recipe's id.
    :param path: Log path.
    """
    recipe = _get_recipe_by_id(id)
    for log in recipe.logs:
        if log.combined_path == path:
            return flask_redirect(log.absolute_url, code=307)
    return NotFound404('Recipe log %s for recipe %s not found' % (path, id))

@app.route('/recipes/<int:id>/reservation-request', methods=['PATCH'])
@auth_required
def update_reservation_request(id):
    """
    Updates the reservation request of a recipe. The request must be 
    :mimetype:`application/json`.

    :param id: Recipe's id.
    :jsonparam boolean reserve: Whether the system will be reserved at the end
      of the recipe. If true, the system will be reserved. If false, the system
      will not be reserved.
    :jsonparam int duration: Number of seconds to reserve the system.
    :jsonparam string when: Circumstances under which the system will be 
      reserved. Valid values are:

      onabort
        If the recipe status is Aborted.
      onfail
        If the recipe status is Aborted, or the result is Fail.
      onwarn
        If the recipe status is Aborted, or the result is Fail or Warn.
      always
        Unconditionally.
    """

    recipe = _get_recipe_by_id(id)
    if not recipe.can_update_reservation_request(identity.current.user):
        raise Forbidden403('Cannot update the reservation request of recipe %s'
                % recipe.id)
    data = read_json_request(request)
    if 'reserve' not in data:
        raise BadRequest400('No reserve specified')
    with convert_internal_errors():
        if data['reserve']:
            if not recipe.reservation_request:
                recipe.reservation_request = RecipeReservationRequest()
            if 'duration' in data:
                duration = int(data['duration'])
                if duration > MAX_SECONDS_PROVISION:
                    raise BadRequest400('Reservation time exceeds maximum time of %s hours'
                            % MAX_HOURS_PROVISION)
                old_duration = recipe.reservation_request.duration
                recipe.reservation_request.duration = duration
                _record_activity(recipe, u'Reservation Request', old_duration,
                        duration)
            if 'when' in data:
                old_condition = recipe.reservation_request.when
                new_condition = RecipeReservationCondition.from_string(data['when'])
                recipe.reservation_request.when = new_condition
                _record_activity(recipe, u'Reservation Condition',
                        old_condition, new_condition)
            session.flush() # to ensure the id is populated
            return jsonify(recipe.reservation_request.__json__())
        else:
            if recipe.reservation_request:
                session.delete(recipe.reservation_request)
                _record_activity(recipe, u'Reservation Request',
                        recipe.reservation_request.duration, None)
            return jsonify(RecipeReservationRequest.empty_json())

def _extend_watchdog(recipe_id, data):
    recipe = _get_recipe_by_id(recipe_id)
    kill_time = data.get('kill_time')
    with convert_internal_errors():
        seconds = recipe.extend(kill_time)
    return jsonify({'seconds': seconds})

@app.route('/recipes/<recipe_id>/watchdog', methods=['POST'])
@auth_required
def extend_watchdog(recipe_id):
    """
    Extend the watchdog for a recipe.

    :param recipe_id: The id of the recipe.
    :jsonparam string kill_time: Time in seconds to extend the watchdog by.
    """
    data = read_json_request(request)
    return _extend_watchdog(recipe_id, data)

@app.route('/recipes/by-taskspec/<taskspec>/watchdog', methods=['POST'])
@auth_required
def extend_watchdog_by_taskspec(taskspec):
    """
    Extend the watchdog for a recipe identified by a taskspec. The valid type
    of a taskspec is either R(recipe) or T(recipe-task).
    See :ref:`Specifying tasks <taskspec>` in :manpage:`bkr(1)`.

    :param taskspec: A taskspec argument that identifies a recipe or recipe task.
    :jsonparam string kill_time: Time in seconds to extend the watchdog by.
    """
    if not taskspec.startswith(('R', 'T')):
        raise BadRequest400('Taskspec type must be one of [R, T]')

    try:
        obj = TaskBase.get_by_t_id(taskspec)
    except BeakerException as exc:
        raise NotFound404(unicode(exc))

    if isinstance(obj, Recipe):
        recipe = obj
    else:
        recipe = obj.recipe
    data = read_json_request(request)
    return _extend_watchdog(recipe.id, data)

@app.route('/recipes/by-fqdn/<fqdn>/watchdog', methods=['POST'])
@auth_required
def extend_watchdog_by_fqdn(fqdn):
    """
    Extend the watchdog for a recipe that is running on the system.

    :param fqdn: The system's fully-qualified domain name.
    :jsonparam string kill_time: Time in seconds to extend the watchdog by.
    """
    try:
        recipe = Recipe.query.join(Recipe.watchdog, Recipe.resource)\
            .filter(RecipeResource.fqdn == fqdn)\
            .filter(Recipe.status == TaskStatus.running).one()
    except NoResultFound:
        raise NotFound404('Cannot find any recipe running on %s' % fqdn)
    data = read_json_request(request)
    return _extend_watchdog(recipe.id, data)

# hack for Sphinx
recipes = Recipes
