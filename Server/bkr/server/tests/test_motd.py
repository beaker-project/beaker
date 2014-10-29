
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import tempfile
from bkr.server.motd import _load_motd

class MotdTest(unittest.TestCase):

    def test_nonexistent(self):
        motd = _load_motd('/this_file_does_not_exist')
        self.assertEquals(motd, None)

    def test_empty(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertEquals(_load_motd(f.name), None)

    # https://bugzilla.redhat.com/show_bug.cgi?id=759269
    def test_comment_only(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write('<!-- span>commented out</span -->\n')
            f.flush()
            self.assertEquals(_load_motd(f.name), None)

    def test_message(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write('<span>Beaker is <em>awesome</em>!</span>\n')
            f.flush()
            self.assertEquals(_load_motd(f.name),
                    '<span>Beaker is <em>awesome</em>!</span>')
