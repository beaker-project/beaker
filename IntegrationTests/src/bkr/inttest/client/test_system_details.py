
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client
import rdflib

class SystemDetailsTest(unittest.TestCase):

    def setUp(self):
        self.system = data_setup.create_system()
        session.flush()

    def test_system_details(self):
        out = run_client(['bkr', 'system-details', self.system.fqdn])
        g = rdflib.Graph()
        g.parse(data=out)
        self.assert_(len(g) > 0)
