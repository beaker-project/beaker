
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientTestCase

class DistroTreesVerifyTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.dodgy_lc = data_setup.create_labcontroller(
                fqdn=u'dodgylc.example.invalid')
        self.distro_tree = data_setup.create_distro_tree()
        for lca in list(self.distro_tree.lab_controller_assocs):
            if lca.lab_controller == self.dodgy_lc:
                self.distro_tree.lab_controller_assocs.remove(lca)

    def test_verify_distro(self):
        output = run_client(['bkr', 'distro-trees-verify', '--name', self.distro_tree.distro.name])
        lines = output.splitlines()
        self.assert_(self.distro_tree.distro.name in lines[0])
        self.assertEquals(lines[1], "missing from labs ['dodgylc.example.invalid']")
