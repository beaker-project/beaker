import os
import unittest
from nose.plugins.skip import SkipTest
from bkr.inttest.client import create_client_config

class QpidConnection(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        if not os.environ.get('BEAKER_CLIENT_TEST_QPID'):
            raise SkipTest('QPID not enabled for client tests,\
                set BEAKER_CLIENT_TEST_QPID=1 and \
                BEAKER_CLIENT_TEST_QPID_BROKER="yourbroker.com"')

    def test_connection(self):
        qpid_broker = os.environ.get('BEAKER_CLIENT_TEST_QPID_BROKER')
        config = create_client_config(qpid_broker=qpid_broker)
        os.environ['BEAKER_CLIENT_CONF'] = config.name
        try:
            from bkr.client.message_bus import ClientBeakerBus
            conn = ClientBeakerBus()
            conn.open()
            conn.close()
        finally:
            config.close()


        
