import unittest
import pkg_resources
import subprocess
import os
from shutil import copy, rmtree
from tempfile import mkdtemp
from turbogears.database import session
from bkr.server.tools.repo_update import update_repos
from bkr.server.model import OSMajor


class RepoUpdate(unittest.TestCase):
    """Tests the repo_update.py script"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _create_remote_harness(self, base_path, name):
        tmp_dir = os.path.join(base_path, name)
        os.mkdir(tmp_dir)
        rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
            'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        copy(rpm_file, tmp_dir)
        p = subprocess.Popen(['createrepo', '-q',
            '--checksum', 'sha', '.'], cwd=tmp_dir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, err = p.communicate()
        self.assertEqual(p.returncode, 0, err)

    def test_update_harness_repos(self):
        """Test that the update_repo() call runs as expected.

        This checks that the harness repos that are supposed to be
        synced are actually synced.

        Does not check repo metadata.
        """
        try:
            base_path = mkdtemp()
            faux_remote_harness1 = self._create_remote_harness(base_path, 'foobangmajor')
            faux_remote_harness2 = self._create_remote_harness(base_path, 'foobazmajor')
            faux_local_harness = mkdtemp('local_harness')
            with session.begin():
                OSMajor.lazy_create(osmajor=u'foobangmajor')
                OSMajor.lazy_create(osmajor=u'foobazmajor')
            # I'm not testing the config here, so just use createrepo
            update_repos('file://%s/' % base_path,
                faux_local_harness)
            self.assertTrue(os.path.exists(os.path.join(faux_local_harness, 'foobangmajor')))
            self.assertTrue(os.path.exists(os.path.join(faux_local_harness, 'foobazmajor')))
        finally:
            rmtree(base_path)
            rmtree(faux_local_harness)
