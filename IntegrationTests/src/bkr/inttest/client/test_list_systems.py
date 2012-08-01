
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client
from bkr.server.model import System, Key, Key_Value_String

class ListSystemsTest(unittest.TestCase):

    def test_list_all_systems(self):
        with session.begin():
            data_setup.create_system() # so that we have at least one
        out = run_client(['bkr', 'list-systems'])
        self.assertEqual(len(out.splitlines()), System.query.count())

    # https://bugzilla.redhat.com/show_bug.cgi?id=690063
    def test_xml_filter(self):
        with session.begin():
            module_key = Key.by_name(u'MODULE')
            with_module = data_setup.create_system()
            with_module.key_values_string.extend([
                    Key_Value_String(module_key, u'cciss'),
                    Key_Value_String(module_key, u'kvm')])
            without_module = data_setup.create_system()
        out = run_client(['bkr', 'list-systems',
                '--xml-filter', '<key_value key="MODULE" />'])
        returned_systems = out.splitlines()
        self.assert_(with_module.fqdn in returned_systems, returned_systems)
        self.assert_(without_module.fqdn not in returned_systems,
                returned_systems)
