# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest

from bkr.common.helpers_six import parse_content_type


class ParsingContentType(unittest.TestCase):

    def test_ok(self):
        self.assertEqual(parse_content_type('type/subtype; charset=utf-8'), 'type/subtype')
        self.assertEqual(parse_content_type('type/subtype'), 'type/subtype')

    def test_empty(self):
        self.assertEqual(parse_content_type(''), '')
