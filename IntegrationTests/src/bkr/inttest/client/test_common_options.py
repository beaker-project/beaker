
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import unittest
from bkr.inttest import get_server_base
from bkr.inttest.client import run_client, create_client_config

class CommonOptionsTest(unittest.TestCase):

    def test_hub(self):
        # wrong hub in config, correct one passed on the command line
        config = create_client_config(hub_url='http://notexist.invalid')
        run_client(['bkr', '--hub', get_server_base().rstrip('/'),
                'list-labcontrollers'], config=config)

    # https://bugzilla.redhat.com/show_bug.cgi?id=862146
    def test_version(self):
        out = run_client(['bkr', '--version'])
        self.assert_(re.match(r'\d+\.[.a-zA-Z0-9]+$', out), out)
