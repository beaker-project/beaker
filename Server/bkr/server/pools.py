
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
from flask import jsonify, request
from bkr.server import identity
from bkr.server.app import app
from bkr.server.model import System, SystemPool, SystemAccessPolicy, \
    SystemAccessPolicyRule, User, Group, SystemPermission, Activity
from bkr.server.flask_util import auth_required, \
    convert_internal_errors, read_json_request, BadRequest400, \
    Forbidden403, MethodNotAllowed405, NotFound404, Conflict409, \
    UnsupportedMediaType415, request_wants_json, render_tg_template, \
    json_collection
from bkr.server.util import absolute_url
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from turbogears.database import session
from bkr.server.systems import _get_system_by_FQDN, _edit_access_policy_rules
import datetime
from bkr.server.bexceptions import DatabaseLookupError

@app.route('/pools/', methods=['GET'])
def get_pools():
    """
    Returns a pageable JSON collection of system pools in Beaker.
    Refer to :ref:`pageable-json-collections`.

    The following fields are supported for filtering and sorting:

    ``id``
        ID of the pool.
    ``name``
        Name of the pool.
    ``owner.user_name``
        Username of the pool owner (if the pool is owned by a user rather than 
        by a group).
    ``owner.group_name``
        Name of the pool's owning group (if the pool is owned by a group rather 
        than by a user).
    """
    query = SystemPool.query.order_by(SystemPool.name)
    # join User and Group for sorting/filtering and also for eager loading
    query = query\
            .outerjoin(SystemPool.owning_user)\
            .options(contains_eager(SystemPool.owning_user))\
            .outerjoin(SystemPool.owning_group)\
            .options(contains_eager(SystemPool.owning_group))
    json_result = json_collection(query, columns={
        'id': SystemPool.id,
        'name': SystemPool.name,
        'owner.user_name': User.user_name,
        'owner.group_name': Group.group_name,
    })
    if request_wants_json():
        return jsonify(json_result)
    return render_tg_template('bkr.server.templates.backgrid', {
        'title': u'Pools',
        'grid_collection_type': 'SystemPools',
        'grid_collection_data': json_result,
        'grid_collection_url': request.path,
        'grid_view_type': 'PoolsView',
        'grid_add_label': 'Create',
        'grid_add_view_type': 'PoolCreateModal' if not identity.current.anonymous else 'null',
    })

_typeahead_split_pattern = re.compile(r'[-\s]+')
@app.route('/pools/+typeahead')
def pools_typeahead():
    if 'q' in request.args:
        pools = SystemPool.query.filter(SystemPool.name.like('%%%s%%' % request.args['q']))
    else:
        pools = SystemPool.query
    data = [{'name': pool.name, 'tokens': _typeahead_split_pattern.split(pool.name.strip())}
            for pool in pools.values(SystemPool.name)]
    return jsonify(data=data)

def _get_pool_by_name(pool_name, lockmode=False):
    """Get system pool by name, reporting HTTP 404 if the system pool is not found"""
    try:
        return SystemPool.by_name(pool_name, lockmode)
    except NoResultFound:
        raise NotFound404('System pool %s does not exist' % pool_name)

@app.route('/pools/<pool_name>/', methods=['GET'])
def get_pool(pool_name):
    """
    Provides detailed information about a system pool in JSON format.

    :param pool_name: System pool's name.
    """
    pool = _get_pool_by_name(pool_name)
    if request_wants_json():
        return jsonify(pool.__json__())
    return render_tg_template('bkr.server.templates.system_pool', {
        'title': pool.name,
        'system_pool': pool,
    })

def _get_owner(data):
    if data is None:
        data = {}
    user_name = data.get('user_name')
    group_name = data.get('group_name')
    if user_name and group_name:
        raise Forbidden403('System pool can have either an user or a group as owner')
    if user_name:
        owner = User.by_user_name(user_name)
        if owner is None:
            raise BadRequest400('No such user %s' % user_name)
        if owner.removed:
            raise BadRequest400('System pool cannot be owned by deleted user %s' % owner.user_name)
        owner_type = 'user'
    if group_name:
        try:
            owner = Group.by_name(group_name)
        except NoResultFound:
            raise BadRequest400('No such group %r' % group_name)
        owner_type = 'group'
    return owner, owner_type

@app.route('/pools/', methods=['POST'])
@auth_required
def create_pool():
    """
    Creates a new system pool in Beaker. The request must be 
    :mimetype:`application/x-www-form-urlencoded` or 
    :mimetype:`application/json`.

    :jsonparam string name: Name for the system pool.
    :jsonparam string description: Description of the system pool.
    :jsonparam object owner: JSON object containing a ``user_name`` key or
      ``group_name`` key identifying the owner for the system pool.

    :status 201: The system pool was successfully created.
    """
    owner = None
    description = None
    u = identity.current.user
    if request.json:
        if 'name' not in request.json:
            raise BadRequest400('Missing pool name key')
        new_name = request.json['name']
        if 'owner' in request.json:
            owner =  request.json['owner']
        if 'description' in request.json:
            description = request.json['description']
    elif request.form:
        if 'name' not in request.form:
            raise BadRequest400('Missing pool name parameter')
        new_name = request.form['name']
        if 'owner' in request.form:
            owner =  request.form['owner']
        if 'description' in request.form:
            description = request.form['description']
    else:
        raise UnsupportedMediaType415
    with convert_internal_errors():
        if SystemPool.query.filter(SystemPool.name == new_name).count() != 0:
            raise Conflict409('System pool with name %r already exists' % new_name)
        pool = SystemPool(name=new_name, description=description)
        session.add(pool)
        if owner:
            owner, owner_type = _get_owner(owner)
            if owner_type == 'user':
                pool.owning_user = owner
            else:
                pool.owning_group = owner
        else:
            pool.owning_user = u
        # new systems pool are visible to everybody by default
        pool.access_policy = SystemAccessPolicy()
        pool.access_policy.add_rule(SystemPermission.view, everybody=True)
        pool.record_activity(user=u, service=u'HTTP',
                     action=u'Created', field=u'Pool',
                     new=unicode(pool))
    response = jsonify(pool.__json__())
    response.status_code = 201
    response.headers.add('Location', absolute_url(pool.href))
    return response

@app.route('/pools/<pool_name>/', methods=['PATCH'])
@auth_required
def update_pool(pool_name):
    """
    Updates attributes of an existing system pool. The request body must be a JSON 
    object containing one or more of the following keys.

    :param pool_name: System pool's name.
    :jsonparam string name: New name for the system pool.
    :jsonparam string description: Description of the system pool.
    :jsonparam object owner: JSON object containing a ``user_name`` key or
      ``group_name`` key identifying the new owner for the system pool.
    :status 200: System pool was updated.
    :status 400: Invalid data was given.
    """
    pool = _get_pool_by_name(pool_name)
    if not pool.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit system pool')
    data = read_json_request(request)
    # helper for recording activity below
    def record_activity(field, old, new, action=u'Changed'):
        pool.record_activity(user=identity.current.user, service=u'HTTP',
                action=action, field=field, old=old, new=new)
    with convert_internal_errors():
        renamed = False
        if 'name' in data:
            new_name = data['name']
            if new_name != pool.name:
                if SystemPool.query.filter(SystemPool.name == new_name).count():
                    raise Conflict409('System pool %s already exists' % new_name)
                record_activity(u'Name', pool.name, new_name)
                pool.name = new_name
                renamed = True
        if 'description' in data:
            new_description = data['description']
            if new_description != pool.description:
                record_activity(u'Description', pool.description, new_description)
                pool.description = new_description
        if 'owner' in data:
            new_owner, owner_type = _get_owner(data['owner'])
            if owner_type == 'user':
                pool.change_owner(user=new_owner)
            else:
                pool.change_owner(group=new_owner)

    response = jsonify(pool.__json__())
    if renamed:
        response.headers.add('Location', absolute_url(pool.href))
    return response

# For compat only. Separate function so that it doesn't appear in the docs.
@app.route('/pools/<pool_name>/', methods=['POST'])
def update_system_pool_post(pool_name):
    return update_pool(pool_name)

@app.route('/pools/<pool_name>/systems/', methods=['POST'])
@auth_required
def add_system_to_pool(pool_name):
    """
    Add a system to a system pool

    :param pool_name: System pool's name.
    :jsonparam fqdn: System's fully-qualified domain name.

    """
    u = identity.current.user
    data = read_json_request(request)
    pool = _get_pool_by_name(pool_name, lockmode='update')
    if 'fqdn' not in data:
        raise BadRequest400('System FQDN not specified')
    try:
        system = System.by_fqdn(data['fqdn'], u)
    except DatabaseLookupError:
        raise BadRequest400("System '%s' does not exist" % data['fqdn'])
    if not pool in system.pools:
        if pool.can_edit(u) and system.can_edit(u):
            system.record_activity(user=u, service=u'HTTP',
                                   action=u'Added', field=u'Pool',
                                   old=None,
                                   new=unicode(pool))
            system.pools.append(pool)
            system.date_modified = datetime.datetime.utcnow()
            pool.record_activity(user=u, service=u'HTTP',
                                 action=u'Added', field=u'System', old=None,
                                 new=unicode(system))
        else:
            if not pool.can_edit(u):
                raise Forbidden403('You do not have permission to '
                                   'add systems to pool %s' % pool.name)
            if not system.can_edit(u):
                raise Forbidden403('You do not have permission to '
                                   'modify system %s' % system.fqdn)

    return '', 204

@app.route('/pools/<pool_name>/systems/', methods=['DELETE'])
@auth_required
def remove_system_from_pool(pool_name):
    """
    Remove a system from a system pool

    :param pool_name: System pool's name.
    :queryparam fqdn: System's fully-qualified domain name

    """
    if 'fqdn' not in request.args:
        raise MethodNotAllowed405
    fqdn = request.args['fqdn']
    system = _get_system_by_FQDN(fqdn)
    u = identity.current.user
    pool = _get_pool_by_name(pool_name, lockmode='update')
    if pool in system.pools:
        if pool.can_edit(u) or system.can_edit(u):
            if system.active_access_policy == pool.access_policy:
                system.active_access_policy = system.custom_access_policy
                system.record_activity(user=u, service=u'HTTP',
                                       field=u'Active Access Policy',
                                       action=u'Changed',
                                       old = pool.access_policy,
                                       new = system.custom_access_policy)
            system.pools.remove(pool)
            system.record_activity(user=u, service=u'HTTP',
                                   action=u'Removed', field=u'Pool', old=unicode(pool), new=None)
            system.date_modified = datetime.datetime.utcnow()
            pool.record_activity(user=u, service=u'HTTP',
                       action=u'Removed', field=u'System', old=unicode(system), new=None)
        else:
            raise Forbidden403('You do not have permission to modify system %s'
                               'or remove systems from pool %s' % (system.fqdn, pool.name))
    else:
        raise BadRequest400('System %s is not in pool %s' % (system.fqdn, pool.name))
    return '', 204


@app.route('/pools/<pool_name>/access-policy/', methods=['GET'])
def get_access_policy(pool_name):
    """
    Get access policy for pool

    :param pool_name: System pool's name.
    """
    pool = _get_pool_by_name(pool_name)
    rules = pool.access_policy.rules
    return jsonify({
        'id': pool.access_policy.id,
        'rules': [
            {'id': rule.id,
             'user': rule.user.user_name if rule.user else None,
             'group': rule.group.group_name if rule.group else None,
             'everybody': rule.everybody,
             'permission': unicode(rule.permission)}
            for rule in rules],
        'possible_permissions': [
            {'value': unicode(permission),
             'label': unicode(permission.label)}
            for permission in SystemPermission],
    })

@app.route('/pools/<pool_name>/access-policy/', methods=['POST', 'PUT'])
@auth_required
def save_access_policy(pool_name):
    """
    Updates the access policy for a system pool.

    :param pool_name: System pool's name.
    :jsonparam array rules: List of rules to include in the new policy. This 
      replaces all existing rules in the policy. Each rule is a JSON object 
      with ``user``, ``group``, and ``everybody`` keys.
    """
    pool = _get_pool_by_name(pool_name)
    if not pool.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system pool policy')
    data = read_json_request(request)
    _edit_access_policy_rules(pool, pool.access_policy, data['rules'])
    return jsonify(pool.access_policy.__json__())

@app.route('/pools/<pool_name>/access-policy/rules/', methods=['POST'])
@auth_required
def add_access_policy_rule(pool_name):
    """
    Adds a new rule to the access policy for a system pool. Each rule in the policy
    grants a permission to a single user, a group of users, or to everybody.

    See :ref:`system-access-policies-api` for a description of the expected JSON parameters.

    :param pool_name: System pool's name.
    """
    pool = _get_pool_by_name(pool_name)
    if not pool.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system pool policy')
    policy = pool.access_policy
    rule = read_json_request(request)
    if rule.get('user', None):
        user = User.by_user_name(rule['user'])
        if not user:
            raise BadRequest400("User '%s' does not exist" % rule['user'])
        if user.removed:
            raise BadRequest400('Cannot add deleted user %s to access policy' % user.user_name)
    else:
        user = None

    if rule.get('group', None):
        try:
            group = Group.by_name(rule['group'])
        except NoResultFound:
            raise BadRequest400("Group '%s' does not exist" % rule['group'])
    else:
        group = None

    try:
        permission = SystemPermission.from_string(rule['permission'])
    except ValueError:
        raise BadRequest400('Invalid permission')
    new_rule = policy.add_rule(user=user, group=group,
                               everybody=rule['everybody'],
                               permission=permission)
    pool.record_activity(user=identity.current.user, service=u'HTTP',
                         field=u'Access Policy Rule', action=u'Added',
                         new=repr(new_rule))
    return '', 204


@app.route('/pools/<pool_name>/access-policy/rules/', methods=['DELETE'])
@auth_required
def delete_access_policy_rules(pool_name):
    """
    Deletes one or more matching rules from a system pool's access policy.

    See :ref:`system-access-policies-api` for description of the expected query parameters

    :param pool_name: System pool's name.

    """
    pool = _get_pool_by_name(pool_name)
    if not pool.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system policy')

    policy = pool.access_policy
    query = SystemAccessPolicyRule.query.filter(SystemAccessPolicyRule.policy == policy)
    if 'permission' in request.args:
        query = query.filter(SystemAccessPolicyRule.permission.in_(
                request.args.getlist('permission', type=SystemPermission.from_string)))
    else:
        raise MethodNotAllowed405
    if 'user' in request.args:
        query = query.join(SystemAccessPolicyRule.user)\
                .filter(User.user_name.in_(request.args.getlist('user')))
    elif 'group' in request.args:
        query = query.join(SystemAccessPolicyRule.group)\
                .filter(Group.group_name.in_(request.args.getlist('group')))
    elif 'everybody' in request.args:
        query = query.filter(SystemAccessPolicyRule.everybody)
    else:
        raise MethodNotAllowed405
    for rule in query:
        rule.record_deletion(service=u'HTTP')
        session.delete(rule)
    return '', 204


@app.route('/pools/<pool_name>/', methods=['DELETE'])
@auth_required
def delete_pool(pool_name):
    """
    Deletes a system pool

    :param pool_name: System pool's name

    """
    pool = _get_pool_by_name(pool_name, lockmode='update')
    u = identity.current.user
    if not pool.can_edit(u):
        raise Forbidden403('Cannot delete pool %s' % pool_name)

    systems = System.query.filter(System.pools.contains(pool))
    System.record_bulk_activity(systems, user=identity.current.user,
                                service=u'HTTP', action=u'Removed',
                                field=u'Pool',
                                old=unicode(pool),
                                new=None)
    # Since we are deleting the pool, we will have to change the active
    # access policy for all systems using the pool's policy to their
    # custom policy
    systems = System.query.filter(System.active_access_policy == pool.access_policy)
    for system in systems:
        system.active_access_policy = system.custom_access_policy
    System.record_bulk_activity(systems, user=identity.current.user,
                                service=u'HTTP',
                                field=u'Active Access Policy', action=u'Changed',
                                old = 'Pool policy: %s' % pool_name,
                                new = 'Custom access policy')
    session.delete(pool)
    activity = Activity(u, u'HTTP', u'Deleted', u'Pool', pool_name)
    session.add(activity)
    return '', 204
