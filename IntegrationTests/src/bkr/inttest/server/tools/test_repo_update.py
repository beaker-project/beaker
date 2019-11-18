
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import os.path
import tempfile

import pkg_resources
import shutil
import sys
import time

from bkr.common import __version__
from bkr.inttest import DatabaseTestCase, Process
from bkr.inttest.server.tools import run_command
from bkr.server.model import session, OSMajor
from bkr.server.tests import data_setup
from bkr.server.util import run_createrepo


class RepoUpdate(DatabaseTestCase):
    """Tests the repo_update.py script"""

    def setUp(self):
        # We will point beaker-repo-update at this fake version of the
        # harness repos that we normally publish on
        # https://beaker-project.org/yum/harness/
        self.harness_repo_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.harness_repo_dir)
        self.harness_repo_server = Process('http_server.py',
                args=[sys.executable,
                      pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                      '--base', self.harness_repo_dir],
                listen_port=19998)
        self.harness_repo_server.start()
        self.addCleanup(self.harness_repo_server.stop)
        self.harness_repo_url = 'http://localhost:19998/'

    def _create_remote_harness(self, osmajor):
        repo_dir = os.path.join(self.harness_repo_dir, osmajor)
        os.mkdir(repo_dir)
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        shutil.copy(rpm_file, repo_dir)
        result = run_createrepo(cwd=repo_dir)
        self.assertEqual(result.returncode, 0, result.err)

    def test_version(self):
        out = run_command('repo_update.py', 'beaker-repo-update', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_update_harness_repos(self):
        """Test that the update_repo() call runs as expected.

        This checks that the harness repos that are supposed to be
        synced are actually synced.

        Does not check repo metadata.
        """
        self._create_remote_harness('foobangmajor')
        self._create_remote_harness('foobazmajor')
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
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', self.harness_repo_url, '-d', faux_local_harness],
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
        local_harness_dir = tempfile.mkdtemp(suffix='local')
        self.addCleanup(shutil.rmtree, local_harness_dir)
        self._create_remote_harness(osmajor)
        # run it once, repo is built
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', self.harness_repo_url, '-d', local_harness_dir],
                ignore_stderr=True)
        repodata_dir = os.path.join(local_harness_dir, osmajor, 'repodata')
        mtime = os.path.getmtime(repodata_dir)
        # run it again, repo should not be rebuilt
        time.sleep(0.001)
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', self.harness_repo_url, '-d', local_harness_dir],
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
        local_harness_dir = tempfile.mkdtemp(suffix='local')
        self.addCleanup(shutil.rmtree, local_harness_dir)
        self._create_remote_harness(osmajor.osmajor)
        run_command('repo_update.py', 'beaker-repo-update',
                ['-b', self.harness_repo_url, '-d', local_harness_dir],
                ignore_stderr=True)
        self.assertTrue(os.path.exists(os.path.join(local_harness_dir, osmajor.osmajor)))
        self.assertFalse(os.path.exists(os.path.join(local_harness_dir, nonexistent_osmajor.osmajor)))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1619969
    def test_replaces_bad_packages(self):
        osmajor = u'MauveBeanieLinux3'
        package = 'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'
        with session.begin():
            data_setup.create_distro_tree(osmajor=osmajor)
        self._create_remote_harness(osmajor)
        local_harness_dir = tempfile.mkdtemp(suffix='local')
        self.addCleanup(shutil.rmtree, local_harness_dir)

        # Local harness dir has a corrupted copy of the package
        os.mkdir(os.path.join(local_harness_dir, osmajor))
        orig_size = os.path.getsize(os.path.join(self.harness_repo_dir, osmajor, package))
        with open(os.path.join(local_harness_dir, osmajor, package), 'wb') as f:
            f.write(b'a' * orig_size)

        run_command('repo_update.py', 'beaker-repo-update',
                ['--debug', '-b', self.harness_repo_url, '-d', local_harness_dir],
                ignore_stderr=True)
        self.assertEquals(
                open(os.path.join(self.harness_repo_dir, osmajor, package), 'rb').read(),
                open(os.path.join(local_harness_dir, osmajor, package), 'rb').read())
