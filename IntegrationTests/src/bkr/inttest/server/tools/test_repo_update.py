
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os, os.path
import subprocess
import tempfile
import shutil
import time
import pkg_resources
import unittest2 as unittest
from bkr.common import __version__
from bkr.server.tests import data_setup
from bkr.server.model import session, OSMajor
from bkr.server.tools.repo_update import update_repos
from bkr.inttest import DatabaseTestCase
from bkr.inttest.server.tools import run_command

class RepoUpdate(DatabaseTestCase):
    """Tests the repo_update.py script"""

    def _create_remote_harness(self, base_path, name):
        tmp_dir = os.path.join(base_path, name)
        os.mkdir(tmp_dir)
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        shutil.copy(rpm_file, tmp_dir)
        p = subprocess.Popen(['createrepo', '-q',
            '--checksum', 'sha', '.'], cwd=tmp_dir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, err = p.communicate()
        self.assertEqual(p.returncode, 0, err)

    def test_version(self):
        out = run_command('repo_update.py', 'beaker-repo-update', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_update_harness_repos(self):
        """Test that the update_repo() call runs as expected.

        This checks that the harness repos that are supposed to be
        synced are actually synced.

        Does not check repo metadata.
        """
        base_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_path)
        faux_remote_harness1 = self._create_remote_harness(base_path, 'foobangmajor')
        faux_remote_harness2 = self._create_remote_harness(base_path, 'foobazmajor')
        faux_local_harness = tempfile.mkdtemp('local_harness')
        self.addCleanup(shutil.rmtree, faux_local_harness)
        with session.begin():
            lab_controller = data_setup.create_labcontroller(fqdn=u'dummylab.example.invalid')
            distro_tree = data_setup.create_distro_tree(
                                osmajor=OSMajor.lazy_create(osmajor=u'foobangmajor'),
                                harness_dir=False,
                                lab_controllers=[lab_controller])
            distro_tree = data_setup.create_distro_tree(
                                osmajor=OSMajor.lazy_create(osmajor=u'foobazmajor'),
                                harness_dir=False,
                                lab_controllers=[lab_controller])
        # I'm not testing the config here, so just use createrepo
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', 'file://%s/' % base_path, '-d', faux_local_harness],
                ignore_stderr=True)
        self.assertTrue(os.path.exists(os.path.join(faux_local_harness, 'foobangmajor')))
        self.assertTrue(os.path.exists(os.path.join(faux_local_harness, 'foobazmajor')))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1027516
    def test_does_not_run_createrepo_unnecessarily(self):
        osmajor = u'GreenBeretLinux99'
        with session.begin():
            lab_controller = data_setup.create_labcontroller(fqdn=u'dummylab.example.invalid')
            distro_tree = data_setup.create_distro_tree(osmajor=OSMajor.lazy_create(osmajor=osmajor),
                                                        harness_dir=False,
                                                        lab_controllers=[lab_controller])
        remote_harness_dir = tempfile.mkdtemp(suffix='remote')
        self.addCleanup(shutil.rmtree, remote_harness_dir)
        local_harness_dir = tempfile.mkdtemp(suffix='local')
        self.addCleanup(shutil.rmtree, local_harness_dir)
        self._create_remote_harness(remote_harness_dir, osmajor)
        # run it once, repo is built
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', 'file://%s/' % remote_harness_dir, '-d', local_harness_dir],
                ignore_stderr=True)
        repodata_dir = os.path.join(local_harness_dir, osmajor, 'repodata')
        mtime = os.path.getmtime(repodata_dir)
        # run it again, repo should not be rebuilt
        time.sleep(0.001)
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', 'file://%s/' % remote_harness_dir, '-d', local_harness_dir],
                ignore_stderr=True)
        self.assertEquals(os.path.getmtime(repodata_dir), mtime)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1213225
    def test_exclude_nonexistent_osmajor(self):
        with session.begin():
            osmajor = OSMajor.lazy_create(osmajor="exist")
            lab_controller = data_setup.create_labcontroller(fqdn=u'dummylab.example.invalid')
            distro_tree = data_setup.create_distro_tree(osmajor=osmajor.osmajor,
                                                        harness_dir=False,
                                                        lab_controllers=[lab_controller])
            nonexistent_osmajor = OSMajor.lazy_create(osmajor=u'notexist')
        remote_harness_dir = tempfile.mkdtemp(suffix='remote')
        self.addCleanup(shutil.rmtree, remote_harness_dir)
        local_harness_dir = tempfile.mkdtemp(suffix='local')
        self.addCleanup(shutil.rmtree, local_harness_dir)
        self._create_remote_harness(remote_harness_dir, osmajor.osmajor)
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', 'file://%s/' % remote_harness_dir, '-d', local_harness_dir],
                ignore_stderr=True)
        self.assertTrue(os.path.exists(os.path.join(local_harness_dir, osmajor.osmajor)))
        self.assertFalse(os.path.exists(os.path.join(local_harness_dir, nonexistent_osmajor.osmajor)))
