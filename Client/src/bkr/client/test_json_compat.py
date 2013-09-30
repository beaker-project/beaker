import unittest
import json_compat

class JsonDumpsTest(unittest.TestCase):

    def test_dumps(self):
        self.assertEquals(json_compat.dumps({}), '{}')
        self.assertEquals(json_compat.dumps({}, indent=4), '{}')
