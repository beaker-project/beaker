
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from flask import jsonify, request
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.app import app
from bkr.server.flask_util import NotFound404, request_wants_json, \
    render_tg_template, admin_auth_required, read_json_request, \
    convert_internal_errors, json_collection
from bkr.server.model import Task, OSMajor, TaskType, Arch

import logging


log = logging.getLogger(__name__)


@app.route('/tasks', methods=['GET'])
def get_tasks():
    """
    Returns a pageable JSON collection of the task library in Beaker.
    Refer to :ref:`pageable-json-collections`.

    The following fields are supported for filtering and sorting:

    ``id``
        ID of the task.
    ``name``
        Name of the task.
    ``description``
        The description of the task provided in the loaded RPM.
    ``version``
        Version of the task provided in the loaded RPM.
    ``type``
        Type of the task, derived from the ``Type`` field in the task metadata.
    ``excluded_arch``
        Arch for which the task is excluded from. Tasks
        are applicable to all arches by default, unless specified
        otherwise in the ``Architectures`` field of the task metadata.
    ``excluded_osmajor``
        OS major version for which the task is excluded from.
        Tasks are applicable to all OS major versions by default,
        unless otherwise specified in the ``Releases`` field of
        the task metadata.
    """
    query = Task.query.filter(Task.valid == True).order_by(Task.name)
    json_result = json_collection(query, columns={
        'id': Task.id,
        'name': Task.name,
        'description': Task.description,
        'version': Task.version,
        'type': (Task.types, TaskType.type),
        'excluded_arch': (Task.excluded_arches, Arch.arch),
        'excluded_osmajor': (Task.excluded_osmajors, OSMajor.osmajor),
    })

    if request_wants_json():
        return jsonify(json_result)

    result = render_tg_template('bkr.server.templates.backgrid', {
        'title': 'Tasks Library',
        'grid_collection_type': 'TaskLibrary',
        'grid_collection_data': json_result,
        'grid_collection_url': request.base_url,
        'grid_view_type': 'TasksView',
    })
    return result

# This route is used whenever user enters any integer past /tasks/.
# Paths that don't match this template are rerouted by either default function or their specific function
# eq. path  .../tasks//custom/name/of/task - will NOT be picked up (processed by default function)
#           .../tasks/custom_name          - will NOT be picked up
#           .../tasks/name/with/slash      - will NOT be picked up
#           .../tasks/123456               - will be picked up
@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    # Dummy handler to fall back to CherryPy
    # so that other methods such as PATCH/DELETE work.
    # ---
    # Because Flask defined 404 has priority before CherryPy's 404,
    # message defined in here will be presented to user when CherryPy's 404 is raised.
    raise NotFound404('No such task with ID: %s' % task_id)

@app.route('/tasks/<int:task_id>', methods=['PATCH'])
@admin_auth_required
def update_task(task_id):
    """
    Updates a task - only handles disabling at this time.

    :param task_id: The task id to update/disable
    :jsonparam bool disabled: Whether the task should be disabled.
    :status 200: Task was successfully updated/disabled
    :status 404: Task was not found (to be disabled)
    """
    try:
        task = Task.by_id(task_id)
    except DatabaseLookupError as e:
        # This should be NotFound404 but due to still using cherrypy
        # 404's are handled there which then will then do a GET /tasks/id
        # which will resolve correctly, which isn't desired
        raise NotFound404('Task %s does not exist' % task_id)

    data = read_json_request(request)

    if data:
        with convert_internal_errors():
            if data.get('disabled', False) and task.valid:
                task.disable()

    response = jsonify(task.to_dict())

    return response
