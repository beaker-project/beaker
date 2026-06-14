
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.model import (session, RecipeTask, RecipeTaskResult,
                              RecipeTaskComment, RecipeTaskResultComment)
from flask import redirect, request, jsonify
from bkr.server.app import app
from bkr.server.flask_util import auth_required, convert_internal_errors, \
    BadRequest400, NotFound404, Forbidden403, read_json_request



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
