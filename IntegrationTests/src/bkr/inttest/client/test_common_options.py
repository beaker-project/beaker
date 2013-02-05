
import unittest
from bkr.inttest import get_server_base
from bkr.inttest.client import run_client, create_client_config

class CommonOptionsTest(unittest.TestCase):

    def test_hub(self):
        # wrong hub in config, correct one passed on the command line
        config = create_client_config(hub_url='http://notexist.invalid')
        run_client(['bkr', '--hub', get_server_base().rstrip('/'),
                'list-labcontrollers'], config=config)
