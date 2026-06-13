
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from bkr.server.helpers import make_link

class MakeLinkTest(unittest.TestCase):

    def test_coerces_non_string_text(self):
        a = make_link('/distros/view?id=5', 5)
        self.assertEqual(a.text, u'5')

    def test_string_text(self):
        a = make_link('/x', u'label')
        self.assertEqual(a.text, u'label')
