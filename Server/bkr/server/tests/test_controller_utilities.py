
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
try:
    from bkr.server.controller_utilities import _custom_status, _custom_result
except ImportError:
    _custom_status = _custom_result = None
from bkr.server.model import TaskStatus, TaskResult

class _Fake(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

class CustomStatusResultTest(unittest.TestCase):

    def setUp(self):
        if _custom_status is None:
            raise unittest.SkipTest('bkr.server.controller_utilities needs TurboGears')

    def test_status_renders_enum_symbol(self):
        e = _custom_status(_Fake(is_dirty=False, status=TaskStatus.completed))
        self.assertEqual(e.text, u'Completed')

    def test_result_renders_enum_symbol(self):
        e = _custom_result(_Fake(result=TaskResult.pass_))
        self.assertEqual(e.text, u'Pass')
