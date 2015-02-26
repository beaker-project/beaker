
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
    Forbidden403, MethodNotAllowed405
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
