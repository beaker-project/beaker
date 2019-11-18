# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import subprocess
import unittest

from bkr.server.tools import ipxe_image, log_delete


class LogDelete(unittest.TestCase):
    """Tests the log_delete.py script"""

    def test_remove_descendants(self):
        input = [
            'http://server/a/x/',
            'http://server/a/y/',
            'http://server/a/',
            'http://server/b/',
            'http://server/b/z/',
            'http://server/c/',
        ]
        expected = [
            'http://server/a/',
            'http://server/b/',
            'http://server/c/',
        ]
        self.assertEquals(list(log_delete.remove_descendants(input)), expected)


def list_msdos_filesystem(image_filename):
    mdir = subprocess.Popen(['mdir', '-i', image_filename, '-/', '-b', '::'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = mdir.communicate()
    if mdir.returncode != 0:
        raise RuntimeError('mdir failed: %s' % err)
    return out.splitlines()


class IpxeImageTest(unittest.TestCase):

    def test_image_generation(self):
        f = ipxe_image.generate_image()
        self.assertItemsEqual(
            list_msdos_filesystem(f.name),
            ['::/syslinux.cfg', '::/ipxe.lkrn'])
