
from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import LabControllerDistroTree

class DistroTreesFilterXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    def test_filtering_by_lab_controller(self):
        with session.begin():
            good_lc = data_setup.create_labcontroller()
            bad_lc = data_setup.create_labcontroller()
            distro_tree_in = data_setup.create_distro_tree()
            distro_tree_out = data_setup.create_distro_tree()
            session.flush()
            distro_tree_in.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=good_lc, url=u'http://notimportant')]
            distro_tree_out.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=bad_lc, url=u'http://notimportant')]
        distro_trees = self.server.distrotrees.filter({'labcontroller': good_lc.fqdn})
        self.assert_(distro_tree_in.id in [d['distro_tree_id'] for d in distro_trees], distro_trees)
        self.assert_(distro_tree_out.id not in [d['distro_tree_id'] for d in distro_trees], distro_trees)
