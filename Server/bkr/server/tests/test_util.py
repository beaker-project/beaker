
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from bkr.server.app import app
from bkr.server.util import url

class UrlTest(unittest.TestCase):

    def test_returns_native_str_in_request_context(self):
        with app.test_request_context('/reserve_system'):
            result = url('/get_search_options')
        self.assertIsInstance(result, str)
        self.assertNotIn("u'", str({'controller': result}))

    def test_appends_query_params(self):
        self.assertEqual(url('/jobs', job_id=1), '/jobs?job_id=1')

    def test_skips_none_params(self):
        self.assertEqual(url('/jobs', job_id=None), '/jobs')

    def test_expands_list_params(self):
        self.assertEqual(url('/jobs', id=[1, 2]), '/jobs?id=1&id=2')

    def test_appends_to_existing_query_string(self):
        self.assertEqual(url('/jobs?a=1', b=2), '/jobs?a=1&b=2')

    def test_rejects_non_dict_params(self):
        self.assertRaises(TypeError, url, '/jobs', 'notadict')
