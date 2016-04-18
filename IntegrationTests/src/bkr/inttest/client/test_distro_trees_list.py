
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import json
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction, DatabaseTestCase
from bkr.inttest.client import run_client, ClientError
from bkr.server.model import LabControllerDistroTree

class DistroTreesListTest(DatabaseTestCase):

    @with_transaction
    def setUp(self):
        self.distro_tree = data_setup.create_distro_tree()

    def test_list_by_distro_name(self):
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--name', self.distro_tree.distro.name])
        trees = json.loads(output)
        self.assertEquals(len(trees), 1)
        self.assertEquals(trees[0]['distro_tree_id'], self.distro_tree.id)
        self.assertEquals(trees[0]['distro_name'], self.distro_tree.distro.name)

    def test_list_by_distro_id(self):
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--distro-id', str(self.distro_tree.distro.id)])
        trees = json.loads(output)
        self.assertEquals(len(trees), 1)
        self.assertEquals(trees[0]['distro_tree_id'], self.distro_tree.id)
        self.assertEquals(trees[0]['distro_name'], self.distro_tree.distro.name)

    def test_list_by_distro_tree_id(self):
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--distro-tree-id', str(self.distro_tree.id)])
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
                    lab_controller=lc, url=u'nfs://example.com/somewhere/'))
            distro_tree_out.lab_controller_assocs.append(LabControllerDistroTree(
                    lab_controller=lc, url=u'nfs://example.com/nowhere/'))
        output = run_client(['bkr', 'distro-trees-list', '--format=json', '--treepath', '%somewhere%'])
        trees = json.loads(output)
        self.assert_(any(distro_tree_in.id == tree['distro_tree_id'] for tree in trees))
        self.assert_(not any(distro_tree_out.id == tree['distro_tree_id'] for tree in trees))

    # https://bugzilla.redhat.com/show_bug.cgi?id=835319
    def test_tabular_format_works(self):
        output = run_client(['bkr', 'distro-trees-list', '--format=tabular',
                '--name', self.distro_tree.distro.name])
        self.assert_('Name: %s' % self.distro_tree.distro.name in output, output)
        self.assert_('Arch: %s' % self.distro_tree.arch in output, output)
        self.assert_('Variant: %s' % self.distro_tree.variant in output, output)
        self.assert_('OSVersion: %s' % self.distro_tree.distro.osversion in output, output)

    def test_xml_filter(self):
        output = run_client(['bkr', 'distro-trees-list', '--format=json',
                '--xml-filter',
                '<distro_name value="%s" />' % self.distro_tree.distro.name])
        trees = json.loads(output)
        self.assertEquals(len(trees), 1)
        self.assertEquals(trees[0]['distro_tree_id'], self.distro_tree.id)
        self.assertEquals(trees[0]['distro_name'], self.distro_tree.distro.name)
