
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# These are unit tests which don't need a MySQL database. Tests which need to
# talk to external services belong in the IntegrationTests subdir.

import unittest2 as unittest
import gzip
import os
import re
import pkg_resources
import errno
from lxml import etree
from tempfile import mkdtemp
from shutil import copy, rmtree
from nose.plugins.skip import SkipTest
from sqlalchemy.schema import MetaData, Table, Column
from sqlalchemy.types import Integer, Unicode
from turbogears.config import get, update
from bkr.server.model.sql import ConditionalInsert
from bkr.server.model.tasklibrary import TaskLibrary


class ConditionalInsertTest(unittest.TestCase):

    def test_unique_params_only(self):
        metadata = MetaData()
        table = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(16), nullable=False, unique=True),
        )
        clause = ConditionalInsert(table, {table.c.name: 'asdf'})
        compiled = clause.compile()
        self.assertEquals(str(compiled),
                'INSERT INTO "table" ("table".name)\n'
                'SELECT :name\nFROM DUAL\nWHERE NOT EXISTS '
                '(SELECT 1 FROM "table"\nWHERE "table".name = :name_1 FOR UPDATE)')
        self.assertEquals(compiled.params, {'name': 'asdf', 'name_1': 'asdf'})

    def test_with_extra_params(self):
        metadata = MetaData()
        table = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(16), nullable=False, unique=True),
            Column('extra', Unicode(16), nullable=False),
        )
        clause = ConditionalInsert(table, {table.c.name: 'asdf'},
                {table.c.extra: 'something'})
        compiled = clause.compile()
        self.assertEquals(str(compiled),
                'INSERT INTO "table" ("table".name, "table".extra)\n'
                'SELECT :name, :extra\nFROM DUAL\nWHERE NOT EXISTS '
                '(SELECT 1 FROM "table"\nWHERE "table".name = :name_1 FOR UPDATE)')
        self.assertEquals(compiled.params, {'name': 'asdf',
                'extra': 'something', 'name_1': 'asdf'})


class TaskLibraryTest(unittest.TestCase):

    def setUp(self):
        test_rpmspath = mkdtemp(prefix='beaker-task-library-test-rpms')
        self.addCleanup(rmtree, test_rpmspath)
        # hack to override descriptor for rpmspath
        class TestTaskLibrary(TaskLibrary):
            rpmspath = test_rpmspath
        self.tasklibrary = TestTaskLibrary()
        self.assertEquals(self.tasklibrary.rpmspath, test_rpmspath)

    def tearDown(self):
        # Make sure sane value is left after test run
        update({'beaker.createrepo_command': 'createrepo'})

    def _hash_repodata_file(self, content, total=0):
        """Returns an int type representation of the XML contents.

        Ordering is not important, as the int representations (returned
        via the hash() function) are all just added together.
        """
        for child in content.getchildren():
            for pck in child.keys():
                pck_k_v_text = '%s%s' % (pck.strip(), child.get(pck).strip())
                total += hash(pck_k_v_text)
            if child.text is not None:
                child_text = child.text.strip()
                if child_text:
                    total += hash(child_text)
            total += hash(child.tag.strip())
            total += self._hash_repodata_file(child, total)
        return total

    def _assert_xml_equivalence(self, file1, file2):
        file1_content = etree.fromstring(file1.read().strip())
        file2_content = etree.fromstring(file2.read().strip())
        hashed_file1 = self._hash_repodata_file(file1_content)
        hashed_file2 = self._hash_repodata_file(file2_content)
        # Assert the contents of the files are indeed the same
        self.assertEquals(hashed_file2, hashed_file1)

    def test_createrepo_c_command(self):
        update({'beaker.createrepo_command': 'createrepo_c'})
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        copy(rpm_file, self.tasklibrary.rpmspath)
        try:
            self.tasklibrary.update_repo()
        except OSError, e:
            if e.errno is errno.ENOENT:
                raise SkipTest('Could not find createrepo_c')

    def test_invalid_createrepo_command_fail(self):
        update({'beaker.createrepo_command': 'iamnotarealcommand'})
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        copy(rpm_file, self.tasklibrary.rpmspath)
        with self.assertRaises(OSError):
            self.tasklibrary.update_repo()

    def test_update_repo(self):
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        copy(rpm_file, self.tasklibrary.rpmspath)
        self.tasklibrary.update_repo()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1101402
    def test_update_repo_cleans_stale_dot_repodata(self):
        # createrepo_c refuses to run if .repodata exists
        update({'beaker.createrepo_command': 'createrepo_c'})
        os.mkdir(os.path.join(self.tasklibrary.rpmspath, '.repodata'))
        self.tasklibrary.update_repo()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1101402
    def test_update_repo_cleans_stale_dot_olddata(self):
        # createrepo refuses to run if .olddata exists
        update({'beaker.createrepo_command': 'createrepo'})
        os.mkdir(os.path.join(self.tasklibrary.rpmspath, '.olddata'))
        self.tasklibrary.update_repo()

    def test_unlink_rpm(self):
        rpm_file = pkg_resources.resource_filename('bkr.server.tests',
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        copy(rpm_file, self.tasklibrary.rpmspath)
        self.tasklibrary. \
            unlink_rpm('tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        self.assertTrue(not os.path.exists(
            os.path.join(self.tasklibrary.rpmspath,
                'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')))
        # This tests that it does not throw an exception
        # if the file has been removed
        self.tasklibrary.unlink_rpm('tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')

    def test_make_snapshot_repo(self):
        recipe_repo_parent = mkdtemp(prefix='beaker-test_make_snapshot_repo')
        self.addCleanup(rmtree, recipe_repo_parent)
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        copy(rpm_file, self.tasklibrary.rpmspath)
        repo_dir = os.path.join(self.tasklibrary.rpmspath, 'repodata')
        # Assert we don't already have a repodata folder
        self.assertFalse(os.path.exists(repo_dir))
        self.tasklibrary.make_snapshot_repo(recipe_repo_parent)
        # It should now be there in the rpmspath
        self.assertTrue(os.path.exists(repo_dir))
        repo_dir_list = os.listdir(repo_dir)
        recipe_repo_dir = os.path.join(recipe_repo_parent, 'repodata')
        recipe_repo_dir_list = os.listdir(recipe_repo_dir)
        # Assert the contents at least appear to be the same
        self.assertItemsEqual(recipe_repo_dir_list, repo_dir_list)
        # Now test the actual content
        for filename in repo_dir_list:
            if filename.endswith(".gz"):
                open_file = gzip.open
            elif filename.endswith(".xml"):
                open_file = open
            else:
                raise AssertionError('Expected gzip or xml, not %r' %
                                                                 filename)
            repo_filename = os.path.join(repo_dir, filename)
            recipe_repo_filename = os.path.join(recipe_repo_dir, filename)
            repo_file = open_file(repo_filename)
            recipe_repo_file = open_file(recipe_repo_filename)
            self._assert_xml_equivalence(repo_file, recipe_repo_file)
