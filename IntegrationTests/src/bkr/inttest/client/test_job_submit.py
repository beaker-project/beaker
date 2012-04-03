
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client
from bkr.server.model import Distro
import pkg_resources

class JobSubmitTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        data_setup.create_product(product_name=u'the_product')
        if not Distro.by_name(u'BlueShoeLinux5-5'):
            data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')
        data_setup.create_task(name=u'/distribution/install')
        data_setup.create_task(name=u'/distribution/reservesys')

    def test_submit_job(self):
        out = run_client(['bkr', 'job-submit',
                pkg_resources.resource_filename('bkr.inttest', 'complete-job.xml')])
        self.assert_(out.startswith('Submitted:'), out)
