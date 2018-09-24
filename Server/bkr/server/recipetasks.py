
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, config
from sqlalchemy.sql import func
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
#from bkr.server.helpers import *
from bkr.common.bexceptions import BX
import urlparse
#from turbogears.scheduler import add_interval_task

import cherrypy

from bkr.server.model import (session, RecipeTask, LogRecipeTask,
                              RecipeTaskResult, LogRecipeTaskResult,
                              LabController, Watchdog, ResourceType,
                              RecipeTaskComment, RecipeTaskResultComment,
                              Recipe)
from flask import redirect, request, jsonify
from bkr.server.app import app
from bkr.server.flask_util import auth_required, convert_internal_errors, \
    BadRequest400, NotFound404, Forbidden403, read_json_request

class RecipeTasks(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    def _warn_once(self, recipetask, msg):
        """
        Records a Warn result with the given message against the given recipe 
        task, but only if the same message does not already appear anywhere 
        else in the recipe already.
        """
        # We use a query with count() here, rather than loading all task 
        # results, for efficiency. Bear in mind that this code may be 
        # firing once we already have a very large number of results against 
        # the task, which could be expensive to fully load.
        if RecipeTaskResult.query.join(RecipeTaskResult.recipetask)\
                .filter(RecipeTask.recipe_id == recipetask.recipe_id)\
                .filter(RecipeTaskResult.log == msg)\
                .with_entities(func.count(RecipeTaskResult.id)).scalar() == 0:
            recipetask.warn(u'/', 0, msg)
            # Need to explicitly commit here because the caller will be raising 
            # an exception, which would otherwise roll everything back.
            session.commit()

    def _check_log_limit(self, recipetask):
        max_logs = config.get('beaker.max_logs_per_recipe', 7500)
        if not max_logs or max_logs <= 0:
            return
        task_log_count = LogRecipeTask.query.join(LogRecipeTask.parent)\
                .filter(RecipeTask.recipe_id == recipetask.recipe_id).count()
        result_log_count = LogRecipeTaskResult.query\
                .join(LogRecipeTaskResult.parent, RecipeTaskResult.recipetask)\
                .filter(RecipeTask.recipe_id == recipetask.recipe_id).count()
        if (task_log_count + result_log_count) >= max_logs:
            self._warn_once(recipetask, u'Too many logs in recipe')
            raise ValueError('Too many logs in recipe %s' % recipetask.recipe_id)

    def _check_result_limit(self, recipetask):
        max_results_per_recipe = config.get('beaker.max_results_per_recipe', 7500)
        if not max_results_per_recipe or max_results_per_recipe <= 0:
            return
        result_count = RecipeTaskResult.query.join(RecipeTaskResult.recipetask)\
                .filter(RecipeTask.recipe_id == recipetask.recipe_id).count()
        if result_count >= max_results_per_recipe:
            self._warn_once(recipetask, u'Too many results in recipe')
            raise ValueError(u'Too many results in recipe %s' % recipetask.recipe_id)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def register_file(self, server, task_id, path, filename, basepath):
        """
        register file and return path to store
        """
        try:
            recipetask = RecipeTask.by_id(task_id, lockmode='update')
        except NoResultFound:
            raise BX(_('Invalid task ID: %s' % task_id))
        Recipe.by_id(recipetask.recipe_id, lockmode='update')
        if recipetask.is_finished():
            raise BX('Cannot register file for finished task %s'
                    % recipetask.t_id)
        self._check_log_limit(recipetask)

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
            result = RecipeTaskResult.by_id(result_id, lockmode='update')
        except NoResultFound:
            raise BX(_('Invalid result ID: %s' % result_id))
        RecipeTask.by_id(result.recipe_task_id, lockmode='update')
        Recipe.by_id(result.recipetask.recipe_id, lockmode='update')
        if result.recipetask.is_finished():
            raise BX('Cannot register file for finished task %s'
                    % result.recipetask.t_id)
        self._check_log_limit(result.recipetask)

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
                     system = w.recipe.resource.fqdn,
                     is_virt_recipe = (w.recipe.resource.type == ResourceType.virt)) for w in Watchdog.by_status(labcontroller, status)]

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
        return {'id': task.id,
                'name': task.name,
                'version': task.version,
                'status': unicode(task.status)}

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
        self._check_result_limit(task)
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

def _get_recipe_task_by_id(recipeid, taskid):
    try:
        task = RecipeTask.by_id(taskid)
    except NoResultFound:
        raise NotFound404('Recipe task not found')
    if recipeid != '_' and str(task.recipe.id) != recipeid:
        raise NotFound404('Recipe task not found')
    return task

@app.route('/recipes/<recipeid>/tasks/<taskid>/logs/<path:path>', methods=['GET'])
def get_recipe_task_log(recipeid, taskid, path):
    """
    Redirects to the actual storage location for the requested task log.

    :param recipeid: Recipe id.
    :param taskid: Recipe task id.
    :param path: Log path.
    """
    task = _get_recipe_task_by_id(recipeid, taskid)
    for log in task.logs:
        if log.combined_path == path:
            return redirect(log.absolute_url, code=307)
    # If the caller requested TESTOUT.log but only taskout.log exists, give them that instead.
    if path == 'TESTOUT.log':
        for log in task.logs:
            if log.combined_path == 'taskout.log':
                return redirect(log.absolute_url, code=307)
    return NotFound404('Task log %s for recipe %s task %s not found' % (path, recipeid, taskid))

@app.route('/recipes/<recipeid>/tasks/<taskid>/comments/', methods=['GET'])
def get_recipe_task_comments(recipeid, taskid):
    """
    Returns a JSON collection of comments made on a recipe task.

    :param recipeid: Recipe id.
    :param taskid: Recipe task id.
    """
    task = _get_recipe_task_by_id(recipeid, taskid)
    with convert_internal_errors():
        return jsonify({'entries': task.comments})

@app.route('/recipes/<recipeid>/tasks/<taskid>/comments/', methods=['POST'])
@auth_required
def post_recipe_task_comment(recipeid, taskid):
    """
    Adds a new comment to a recipe task. The request must be :mimetype:`application/json`.

    :param recipeid: Recipe id.
    :param taskid: Recipe task id.
    :jsonparam string comment: Comment text.
    """
    task = _get_recipe_task_by_id(recipeid, taskid)
    if not task.can_comment(identity.current.user):
        raise Forbidden403('Cannot post recipe task comment')
    data = read_json_request(request)
    if 'comment' not in data:
        raise BadRequest400('Missing "comment" key')
    with convert_internal_errors():
        comment = RecipeTaskComment(user=identity.current.user,
                comment=data['comment'])
        task.comments.append(comment)
    session.flush() # to populate the id
    return jsonify(comment.__json__())

def _get_recipe_task_result_by_id(recipeid, taskid, resultid):
    try:
        result = RecipeTaskResult.by_id(resultid)
    except NoResultFound:
        raise NotFound404('Recipe task result not found')
    if recipeid != '_' and str(result.recipetask.recipe.id) != recipeid:
        raise NotFound404('Recipe task result not found')
    if taskid != '_' and str(result.recipetask.id) != taskid:
        raise NotFound404('Recipe task result not found')
    return result

@app.route('/recipes/<recipeid>/tasks/<taskid>/results/<resultid>/logs/<path:path>', methods=['GET'])
def get_recipe_task_result_log(recipeid, taskid, resultid, path):
    """
    Redirects to the actual storage location for the requested result log.

    :param recipeid: Recipe id.
    :param taskid: Recipe task id.
    :param resultid: Recipe task result id.
    :param path: Log path.
    """
    result = _get_recipe_task_result_by_id(recipeid, taskid, resultid)
    for log in result.logs:
        if log.combined_path == path:
            return redirect(log.absolute_url, code=307)
    return NotFound404('Result log %s for recipe %s task %s result %s not found'
            % (path, recipeid, taskid, resultid))

@app.route('/recipes/<recipeid>/tasks/<taskid>/results/<resultid>/comments/', methods=['GET'])
def get_recipe_task_result_comments(recipeid, taskid, resultid):
    """
    Returns a JSON collection of comments made on a recipe task result.

    :param recipeid: Recipe id.
    :param taskid: Recipe task id.
    :param resultid: Recipe task result id.
    """
    result = _get_recipe_task_result_by_id(recipeid, taskid, resultid)
    with convert_internal_errors():
        return jsonify({'entries': result.comments})

@app.route('/recipes/<recipeid>/tasks/<taskid>/results/<resultid>/comments/', methods=['POST'])
@auth_required
def post_recipe_task_result_comment(recipeid, taskid, resultid):
    """
    Adds a new comment to a recipe task. The request must be :mimetype:`application/json`.

    :param recipeid: Recipe id.
    :param taskid: Recipe task id.
    :param resultid: Recipe task result id.
    :jsonparam string comment: Comment text.
    """
    result = _get_recipe_task_result_by_id(recipeid, taskid, resultid)
    if not result.can_comment(identity.current.user):
        raise Forbidden403('Cannot post recipe task result comment')
    data = read_json_request(request)
    if 'comment' not in data:
        raise BadRequest400('Missing "comment" key')
    with convert_internal_errors():
        comment = RecipeTaskResultComment(user=identity.current.user,
                comment=data['comment'])
        result.comments.append(comment)
    session.flush() # to populate the id
    return jsonify(comment.__json__())
