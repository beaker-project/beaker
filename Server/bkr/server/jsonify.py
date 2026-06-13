
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from decimal import Decimal

from simplejson import JSONEncoder


class GenericJSON(JSONEncoder):

    def default(self, obj):
        if hasattr(obj, '__json__'):
            return obj.__json__()
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if hasattr(obj, '_sa_class_manager'):
            return dict((k, v) for k, v in obj.__dict__.items()
                        if not k.startswith('_sa_'))
        return super(GenericJSON, self).default(obj)


_instance = GenericJSON()


def encode(obj):
    return _instance.encode(obj)
