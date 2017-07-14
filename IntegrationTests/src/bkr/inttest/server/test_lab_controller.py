
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskStatus, RecipeSet, LabController, System
from bkr.server.bexceptions import BX
from bkr.inttest import data_setup, DatabaseTestCase

class TestLabController(DatabaseTestCase):

    def setUp(self):
        self.lc_fqdn = u'lab.domain.com'
        with session.begin():
            lc = data_setup.create_labcontroller(fqdn=self.lc_fqdn)

    def test_lookup_secret_fqdn(self):
        with session.begin():
            system = data_setup.create_system(private=True)
        lab_controller_user = LabController.by_name(self.lc_fqdn).user
        system2 = System.by_fqdn(str(system.fqdn), user=lab_controller_user)
        self.assertEquals(system, system2)
