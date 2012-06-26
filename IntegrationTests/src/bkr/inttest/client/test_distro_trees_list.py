
import unittest
import json
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError
from bkr.server.model import LabControllerDistroTree

class DistroTreesListTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.distro_tree = data_setup.create_distro_tree()

    def test_list_by_distro_name(self):
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--name', self.distro_tree.distro.name])
        trees = json.loads(output)
        self.assertEquals(len(trees), 1)
        self.assertEquals(trees[0]['distro_tree_id'], self.distro_tree.id)
        self.assertEquals(trees[0]['distro_name'], self.distro_tree.distro.name)

    def test_exits_with_error_if_none_match(self):
        try:
            run_client(['bkr', 'distro-trees-list', '--name', 'NOTEXIST'])
            fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertEqual(e.stderr_output, 'Nothing Matches\n')

    # https://bugzilla.redhat.com/show_bug.cgi?id=728022
    def test_filtering_by_lab_controller(self):
        with session.begin():
            distro_tree_in = data_setup.create_distro_tree()
            distro_tree_out = data_setup.create_distro_tree()
            good_lc = data_setup.create_labcontroller()
            bad_lc = data_setup.create_labcontroller()
            distro_tree_in.lab_controller_assocs.append(LabControllerDistroTree(
                    lab_controller=good_lc, url=u'http://notimportant'))
            distro_tree_out.lab_controller_assocs.append(LabControllerDistroTree(
                    lab_controller=bad_lc, url=u'http://notimportant'))
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--labcontroller', good_lc.fqdn])
        trees = json.loads(output)
        self.assert_(any(distro_tree_in.id == tree['distro_tree_id'] for tree in trees))
        self.assert_(not any(distro_tree_out.id == tree['distro_tree_id'] for tree in trees))

    # https://bugzilla.redhat.com/show_bug.cgi?id=736989
    def test_filtering_by_treepath(self):
        with session.begin():
            distro_tree_in = data_setup.create_distro_tree()
            distro_tree_out = data_setup.create_distro_tree()
            lc = data_setup.create_labcontroller()
            distro_tree_in.lab_controller_assocs.append(LabControllerDistroTree(
                    lab_controller=lc, url='nfs://example.com/somewhere/'))
            distro_tree_out.lab_controller_assocs.append(LabControllerDistroTree(
                    lab_controller=lc, url='nfs://example.com/nowhere/'))
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--treepath', '%somewhere%'])
        trees = json.loads(output)
        self.assert_(any(distro_tree_in.id == tree['distro_tree_id'] for tree in trees))
        self.assert_(not any(distro_tree_out.id == tree['distro_tree_id'] for tree in trees))
