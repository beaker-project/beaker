
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from bkr.client import json_compat

class JsonDumpsTest(unittest.TestCase):

    def test_dumps(self):
        self.assertEquals(json_compat.dumps({}), '{}')
        self.assertEquals(json_compat.dumps({}, indent=4), '{}')
