
import unittest
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskStatus, RecipeSet, LabController, System
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.inttest import data_setup

class TestLabController(unittest.TestCase):

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
