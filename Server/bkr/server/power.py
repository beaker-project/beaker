
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from flask import jsonify, request
from sqlalchemy.orm.exc import NoResultFound

from bkr.server.model import session, PowerType, System, Power, Activity
from bkr.server import identity
from bkr.server.app import app
from bkr.server.util import url
from bkr.server.flask_util import admin_auth_required, read_json_request,\
    convert_internal_errors, BadRequest400, NotFound404,\
    Conflict409, request_wants_json, render_tg_template


@app.route('/powertypes/', methods=['GET'])
def get_powertypes():
    """Returns a JSON collection of all power types defined in Beaker."""
    result = PowerType.query.order_by(PowerType.name).all()
    if request_wants_json():
        return jsonify(power_types=result)
    return render_tg_template('bkr.server.templates.power_types', {
        'title': 'Power Types',
        'power_types': result,
        'power_types_url': url('/powertypes/'),
        'user_can_edit': identity.current.user is not None and identity.current.user.is_admin()
    })


@app.route('/powertypes/<id>', methods=['DELETE'])
@admin_auth_required
def delete_powertype(id):
    """
    Deletes a power type by the given id.

    :param id: The id of the power type to be deleted.
    :status 204: Power type successfully deleted.
    :status 400: Power type is referenced by systems.
    :status 404: Power type can not be found.
    """
    try:
        powertype = PowerType.by_id(id)
    except NoResultFound:
        raise NotFound404('Power type: %s does not exist' % id)

    systems_referenced = System.query.join(System.power).filter(
        Power.power_type == powertype).count()
    if systems_referenced:
        raise BadRequest400('Power type %s still referenced by %i systems' % (
            powertype.name, systems_referenced))

    session.delete(powertype)

    activity = Activity(identity.current.user, u'HTTP', u'Deleted', u'PowerType', powertype.name)
    session.add(activity)

    return '', 204



@app.route('/powertypes/', methods=['POST'])
@admin_auth_required
def create_powertype():
    """
    Creates a new power type. The request must be :mimetype:`application/json`.

    :jsonparam string name: Name for the power type.
    :status 201: The power type was successfully created.
    """
    data = read_json_request(request)
    with convert_internal_errors():
        if PowerType.query.filter_by(**data).count():
            raise Conflict409('Power type %s already exists' % data['name'])
        powertype = PowerType(**data)
        activity = Activity(identity.current.user, u'HTTP', u'Created', u'PowerType', powertype.name)
        session.add_all([powertype, activity])

    response = jsonify(powertype.__json__())
    response.status_code = 201
    return response
