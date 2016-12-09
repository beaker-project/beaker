
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.orm import contains_eager
from flask import request, jsonify
from bkr.server.app import app
from bkr.server.flask_util import json_collection, request_wants_json, \
        render_tg_template
from bkr.server.model import (Activity, User, Distro, DistroTree,
        LabController, System, Group, Arch, DistroActivity, DistroTreeActivity,
                              LabControllerActivity, SystemActivity, GroupActivity,
                              SystemPool, SystemPoolActivity)

# Search field mapping which applies to all activity types.
common_activity_search_columns = {
    'id': Activity.id,
    'type': Activity.type,
    'service': Activity.service,
    'created': Activity.created,
    'field_name': Activity.field_name,
    'action': Activity.action,
    'old_value': Activity.old_value,
    'new_value': Activity.new_value,
}

@app.route('/activity/', methods=['GET'])
def get_activity():
    """
    Returns a pageable JSON collection of all activity records in Beaker.
    Refer to :ref:`pageable-json-collections`.

    The following fields are supported for filtering and sorting:

    ``id``
        ID of the activity.
    ``type``
        Type of the activity record. Possible values are: ``system_activity``, 
        ``lab_controller_activity``, ``distro_activity``, 
        ``distro_tree_activity``, ``job_activity``, ``recipeset_activity``, 
        ``recipe_activity``,``user_activity``, ``group_activity``.
    ``service``
        Service through which the action was performed. Usually this is 
        ``XMLRPC``, ``WEBUI``, ``HTTP``, or ``Scheduler``.
    ``created``
        Timestamp at which the activity was recorded.
    ``action``
        Action which was recorded.
    ``field_name``
        Field in the system data which was affected by the action.
    ``old_value``
        Previous value of the field before the action was performed (if applicable).
    ``new_value``
        New value of the field after the action was performed (if applicable).
    """
    query = Activity.query.order_by(Activity.id.desc())
    json_result = json_collection(query,
            columns=common_activity_search_columns,
            skip_count=True)
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'ActivityView',
    })

@app.route('/activity/distro', methods=['GET'])
def get_distro_activity():
    """
    Returns a pageable JSON collection of all distro activity records.

    Supports the same fields for filtering and sorting as 
    :http:get:`/activity/`, with the following additions:

    ``distro``
        Name of the distro affected.
    ``distro.name``
        Name of the distro affected.
    """
    query = DistroActivity.query.order_by(DistroActivity.id.desc())
    # join Distro for sorting/filtering and also for eager loading
    query = query.join(DistroActivity.object)\
            .options(contains_eager(DistroActivity.object))
    if not request.args.get('q'):
        # need to avoid a filesort due to MySQL picking distro as first table
        query = query.with_hint(DistroActivity.__table__,
                'IGNORE INDEX (ix_distro_activity_distro_id)', 'mysql')
    json_result = json_collection(query,
            columns=dict(common_activity_search_columns.items() + {
                'distro': Distro.name,
                'distro.name': Distro.name,
                }.items()),
            skip_count=True)
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Distro Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'DistroActivityView',
    })

@app.route('/activity/distrotree', methods=['GET'])
def get_distro_tree_activity():
    """
    Returns a pageable JSON collection of all distro tree activity records.

    Supports the same fields for filtering and sorting as 
    :http:get:`/activity/`, with the following additions:

    ``distro_tree.distro``
        Distro name of the tree affected.
    ``distro_tree.distro.name``
        Distro name of the tree affected.
    ``distro_tree.variant``
        Variant of the tree affected.
    ``distro_tree.arch``
        Arch of the tree affected.
    """
    query = DistroTreeActivity.query.order_by(DistroTreeActivity.id.desc())
    # join DistroTree, Distro, and Arch for sorting/filtering and also for eager loading
    query = query.join(DistroTreeActivity.object)\
            .join(DistroTree.distro)\
            .join(DistroTree.arch)\
            .options(contains_eager(DistroTreeActivity.object, DistroTree.distro))\
            .options(contains_eager(DistroTreeActivity.object, DistroTree.arch))
    if not request.args.get('q'):
        # need to avoid a filesort due to MySQL picking distro_tree as first table
        query = query.with_hint(DistroTreeActivity.__table__,
                'IGNORE INDEX (ix_distro_tree_activity_distro_tree_id)', 'mysql')
    json_result = json_collection(query,
            columns=dict(common_activity_search_columns.items() + {
                'distro_tree.distro': Distro.name,
                'distro_tree.distro.name': Distro.name,
                'distro_tree.variant': DistroTree.variant,
                'distro_tree.arch': Arch.arch,
                }.items()),
            skip_count=True)
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Distro Tree Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'DistroTreeActivityView',
    })

@app.route('/activity/group', methods=['GET'])
def get_group_activity():
    """
    Returns a pageable JSON collection of all group activity records.

    Supports the same fields for filtering and sorting as 
    :http:get:`/activity/`, with the following additions:

    ``group``
        Name of the group affected.
    ``group.group_name``
        Name of the group affected.
    """
    query = GroupActivity.query.order_by(GroupActivity.id.desc())
    # join Group for sorting/filtering and also for eager loading
    query = query.join(GroupActivity.object)\
            .options(contains_eager(DistroTreeActivity.object))
    if not request.args.get('q'):
        # need to avoid a filesort due to MySQL picking group as first table
        query = query.with_hint(GroupActivity.__table__,
                'IGNORE INDEX (ix_group_activity_group_id)', 'mysql')
    json_result = json_collection(query,
            columns=dict(common_activity_search_columns.items() + {
                'group': Group.group_name,
                'group.group_name': Group.group_name,
                }.items()))
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Group Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'GroupActivityView',
    })

@app.route('/activity/labcontroller', methods=['GET'])
def get_lab_controller_activity():
    """
    Returns a pageable JSON collection of all lab controller activity records.

    Supports the same fields for filtering and sorting as 
    :http:get:`/activity/`, with the following additions:

    ``lab_controller``
        FQDN of the lab controller affected.
    ``lab_controller.fqdn``
        FQDN of the lab controller affected.
    """
    query = LabControllerActivity.query.order_by(LabControllerActivity.id.desc())
    # join LabController for sorting/filtering and also for eager loading
    query = query.join(LabControllerActivity.object)\
            .options(contains_eager(LabControllerActivity.object))
    if not request.args.get('q'):
        # need to avoid a filesort due to MySQL picking lab_controller as first table
        query = query.with_hint(LabControllerActivity.__table__,
                'IGNORE INDEX (ix_lab_controller_activity_lab_controller_id)', 'mysql')
    json_result = json_collection(query,
            columns=dict(common_activity_search_columns.items() + {
                'lab_controller': LabController.fqdn,
                'lab_controller.fqdn': LabController.fqdn,
                }.items()))
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Lab Controller Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'LabControllerActivityView',
    })

@app.route('/activity/system', methods=['GET'])
def get_systems_activity(): # distinct from get_system_activity
    """
    Returns a pageable JSON collection of all system activity records.

    Supports the same fields for filtering and sorting as 
    :http:get:`/activity/`, with the following additions:

    ``system``
        FQDN of the system affected.
    ``system.fqdn``
        FQDN of the system affected.
    """
    query = SystemActivity.query.order_by(SystemActivity.id.desc())
    # join System for sorting/filtering and also for eager loading
    query = query.join(SystemActivity.object)\
            .options(contains_eager(SystemActivity.object))
    if not request.args.get('q'):
        # need to avoid a filesort due to MySQL picking system as first table
        query = query.with_hint(SystemActivity.__table__,
                'IGNORE INDEX (ix_system_activity_system_id)', 'mysql')
    json_result = json_collection(query,
            columns=dict(common_activity_search_columns.items() + {
                'system': System.fqdn,
                'system.fqdn': System.fqdn,
                }.items()),
            skip_count=True)
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'System Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'SystemsActivityView',
    })


@app.route('/activity/pool', methods=['GET'])
def get_system_pools_activity():
    """
    Returns a pageable JSON collection of all system pool activity records.

    Supports the same fields for filtering and sorting as 
    :http:get:`/activity/`, with the following additions:

    ``pool``
        Name of the system pool
    ``pool.name``
        Name of the system pool
    ``pool.owner.user_name``
        Username of the pool owner (if the pool is owned by a user rather than 
        by a group).
    ``pool.owner.group_name``
        Name of the pool's owning group (if the pool is owned by a group rather 
        than by a user).

    """
    query = SystemPoolActivity.query.order_by(SystemPoolActivity.id.desc())
    query = query.join(SystemPoolActivity.object)\
            .options(contains_eager(SystemPoolActivity.object)) \
            .outerjoin(SystemPool.owning_user) \
            .outerjoin(SystemPool.owning_group)
    json_result = json_collection(query,
            columns=dict(common_activity_search_columns.items() + {
                'pool': SystemPool.name,
                'pool.name': SystemPool.name,
                'pool.owner.user_name': User.user_name,
                'pool.owner.group_name': Group.group_name,
                }.items()),
            skip_count=True)
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'System Pool Activity',
        'grid_collection_type': 'Activity',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'SystemPoolActivityView',
    })
