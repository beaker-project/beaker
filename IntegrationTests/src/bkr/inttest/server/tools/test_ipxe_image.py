
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.common import __version__
from bkr.inttest import DatabaseTestCase
from bkr.inttest.server.tools import run_command

class IpxeImageTest(DatabaseTestCase):

    def test_version(self):
        out = run_command('ipxe_image.py', 'beaker-create-ipxe-image', ['--version'])
        self.assertEquals(out.strip(), __version__)
