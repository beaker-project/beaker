# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from flask import jsonify

from bkr.server.app import app
from bkr.server.flask_util import json_collection
from bkr.server.model import DistroTag


def _serialize_tag(tag):
    return {
        'id': tag.id,
        'tag': tag.tag,
    }


@app.route('/tags', methods=['GET'])
def get_distro_tags():
    query = DistroTag.query.order_by(DistroTag.tag)
    result = json_collection(query, columns={
        'id': DistroTag.id,
        'tag': DistroTag.tag,
    })
    result['entries'] = [_serialize_tag(tag) for tag in result['entries']]
    return jsonify(result)
