
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import lxml.etree

from sqlalchemy.orm.exc import NoResultFound
from bkr.server.database import session
from bkr.server import identity
from bkr.server.reserve_workflow import MAX_SECONDS_PROVISION, MAX_HOURS_PROVISION
from bkr.server.junitxml import recipe_to_junit_xml
from bkr.server.model import (Recipe, TaskStatus, RecipeResource, TaskBase,
                              RecipeReservationRequest, RecipeReservationCondition)
from bkr.server.app import app
from bkr.server.flask_util import BadRequest400, NotFound404, \
    Forbidden403, auth_required, read_json_request, convert_internal_errors, \
    request_wants_json, render_tg_template, stringbool
from flask import request, jsonify, redirect as flask_redirect, make_response
from bkr.server.bexceptions import BeakerException

import six


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
        raise NotFound404(six.text_type(exc))

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

