
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client
from bkr.server.model import System

class ListSystemsTest(unittest.TestCase):

    def test_list_all_systems(self):
        data_setup.create_system() # so that we have at least one
        session.flush()
        out = run_client(['bkr', 'list-systems'])
        self.assertEqual(len(out.splitlines()), System.query.count())
