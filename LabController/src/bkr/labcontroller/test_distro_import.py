# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import ConfigParser
import unittest2 as unittest
from bkr.labcontroller.distro_import import ModularCompose

class ModularComposeTest(unittest.TestCase):

    def create_parser(self):
        cp = ConfigParser.ConfigParser()
        cp.add_section('product')
        cp.set('product', 'version', '8')
        cp.add_section('compose')
        cp.set('compose', 'date', '202027')
        cp.set('compose', 'respin', '0')
        return cp

    def test_handles_URL_with_trailing_slash(self):
        parser1 = self.create_parser()
        parser1.url = 'http://dummy.test/RHEL8/compose'
        c1 = ModularCompose(parser1, 'AppStream')

        parser2 = self.create_parser()
        parser2.url = 'http://dummy.test/RHEL8/compose/'
        c2 = ModularCompose(parser2, 'AppStream')
        self.assertEqual(c1.get_status_url(), c2.get_status_url())
