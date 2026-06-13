
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import simplejson
from bkr.server.jsonify import GenericJSON, encode

class JsonifyTest(unittest.TestCase):

    def test_encoder_accepts_simplejson_kwargs(self):
        simplejson.dumps({'a': 1}, cls=GenericJSON, iterable_as_array=False)

    def test_encodes_json_method_objects(self):
        class Obj(object):
            def __json__(self):
                return {'id': 7}
        self.assertEqual(encode(Obj()), '{"id": 7}')

    def test_encodes_sqlalchemy_object_without_json(self):
        class FakeSA(object):
            _sa_class_manager = object()
            def __init__(self):
                self._sa_instance_state = object()
                self.name = u'foo'
                self.count = 3
        self.assertEqual(simplejson.loads(encode(FakeSA())),
                         {'name': 'foo', 'count': 3})
