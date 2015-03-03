
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from flask import jsonify, request
from bkr.server import identity
from bkr.server.app import app
from bkr.server.model import System, SystemPool, SystemAccessPolicy, \
    SystemAccessPolicyRule, User, Group, SystemPermission
from bkr.server.flask_util import auth_required, \
    convert_internal_errors, read_json_request, BadRequest400, \
    Forbidden403, MethodNotAllowed405, NotFound404
from sqlalchemy.orm.exc import NoResultFound
from turbogears.database import session
from bkr.server.systems import _get_system_by_FQDN
import datetime

@app.route('/pools/<pool_name>/', methods=['GET'])
def get_pool(pool_name):
    with convert_internal_errors():
        pool = SystemPool.by_name(pool_name)
        return jsonify(pool.__json__())

@app.route('/pools/<pool_name>/systems/', methods=['POST'])
@auth_required
def add_system_to_pool(pool_name):
    """
    Add a system to a system pool

    :param pool_name: System pool's pool name
    :jsonparam fqdn: System's fully-qualified domain name.

    """
    u = identity.current.user
    data = read_json_request(request)
    fqdn = data['fqdn']
    system = _get_system_by_FQDN(fqdn)
    try:
        pool = SystemPool.by_name(pool_name, lockmode='update')
    except NoResultFound:
        pool = SystemPool(name=pool_name, description=pool_name,
                          owning_user=identity.current.user)
        pool.record_activity(user=u, service=u'HTTP',
                             action=u'Created', field=u'Pool',
                             new=unicode(pool))
        pool.access_policy = SystemAccessPolicy()
        pool.access_policy.add_rule(SystemPermission.view, everybody=True)
    if not pool in system.pools:
        if pool.can_edit(u) and system.can_edit(u):
            system.record_activity(user=u, service=u'HTTP',
                                   action=u'Added', field=u'Pool',
                                   old=None,
                                   new=unicode(pool))
            system.pools.append(pool)
            system.date_modified = datetime.datetime.utcnow()
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

    :param pool_name: System pool's pool name
    :queryparam fqdn: System's fully-qualified domain name

    """
    if 'fqdn' not in request.args:
        raise MethodNotAllowed405
    fqdn = request.args['fqdn']
    system = _get_system_by_FQDN(fqdn)
    u = identity.current.user
    with convert_internal_errors():
        pool = SystemPool.by_name(pool_name, lockmode='update')
    if pool in system.pools:
        if pool.can_edit(u) or system.can_edit(u):
            system.pools.remove(pool)
            system.record_activity(user=u, service=u'HTTP',
                                   action=u'Removed', field=u'Pool', old=pool, new=None)
            system.date_modified = datetime.datetime.utcnow()
        else:
            raise Forbidden403('You do not have permission to modify system %s'
                               'or add systems to pool %s' % (system.fqdn, pool.name))
    else:
        raise BadRequest400('System %s is not in pool %s' % (system.fqdn, pool.name))
    return '', 204


@app.route('/pools/<pool_name>/access-policy/', methods=['GET'])
def get_access_policy(pool_name):
    """
    Get access policy for pool

    :param pool_name: The system pool's name.

    """
    try:
        pool = SystemPool.by_name(pool_name)
    except NoResultFound:
        raise NotFound404('System pool %s does not exist' % pool_name)
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

@app.route('/pools/<pool_name>/access-policy/rules/', methods=['POST'])
@auth_required
def add_access_policy_rule(pool_name):
    """
    Adds a new rule to the access policy for a system pool. Each rule in the policy
    grants a permission to a single user, a group of users, or to everybody.

    See :ref:`system-access-policies-api` for a description of the expected JSON parameters.

    :param pool_name: The system pool's name.
    """
    try:
        pool = SystemPool.by_name(pool_name)
    except NoResultFound:
        raise NotFound404('System pool %s does not exist' % pool_name)

    if not pool.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system pool policy')
    policy = pool.access_policy
    rule = read_json_request(request)
    if rule.get('user', None):
        user = User.by_user_name(rule['user'])
        if not user:
            raise BadRequest400("User '%s' does not exist" % rule['user'])
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

    :param pool_name: The system pool's name

    """
    try:
        pool = SystemPool.by_name(pool_name)
    except NoResultFound:
        raise NotFound404('System pool %s does not exist' % pool_name)
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
