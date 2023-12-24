# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest

from bkr.server.distrotrees import DistroTrees


class CheckDistroTreeImportUnitTest(unittest.TestCase):

    def test_undefined_schema_in_url(self):
        t_url = [
            "https://example.com/RHEL11-Server/x86_64/os",
            "example.com/RHEL11-Server/x86_64/ppc64",
            "example.com/RHEL11-Server/x86_64/aarch64"
        ]
        t_distro_tree, t_lab_controller = None, None

        with self.assertRaises(ValueError) as context:
            DistroTrees.add_distro_urls(t_distro_tree, t_lab_controller, t_url)

        self.assertTrue('URL {} is not absolute'.format(t_url[2]) in context.exception)
