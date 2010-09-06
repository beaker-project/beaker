import sys
from bkr.server.util import load_config
import unittest

from bkr.server.model import System, User


class SystemCreation(unittest.TestCase):
    
    def test_create_system_default(self):
        new_system = System()
        self.assertNotEqual(new_system,None)

    def test_create_system_params(self):
        new_system = System(fqdn='test_fqdn', contact='test@email.com',
                            location='Brisbane', model='Proliant', serial='4534534',
                            vendor='Dell')
        self.assertNotEqual(new_system,None)
    
class SystemUser(unittest.TestCase):
    def setUp(self):
        self.system = System('test_system')
        self.user = User('test_user')

    def test_add_user_to_system(self): 
        self.system.user = self.user
        self.assertEquals(System.user,self.user)

    def test_remove_user_from_system(self):
        self.system.user = None
        self.assertEquals(self.system.user,None)

if __name__ == '__main__':
    unittest.main()
