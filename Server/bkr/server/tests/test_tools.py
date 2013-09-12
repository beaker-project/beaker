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

    def test_update_harness_repos(self):
        """Test that the update_repo() call runs without error.

        Does not check repo metadata or anything like that.
        """
        try:
            tmp_dir = mkdtemp()
            faux_remote_harness = os.path.join(tmp_dir, 'foobangmajor')
            os.mkdir(faux_remote_harness)
            faux_local_harness = mkdtemp('local_harness')
            with session.begin():
                OSMajor('foobangmajor')
            rpm_file = pkg_resources.resource_filename('bkr.server.tests', \
                'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
            copy(rpm_file, faux_remote_harness)
            # I'm not testing the config here, so just use createrepo
            p = subprocess.Popen(['createrepo', '-q',
                '--checksum', 'sha', '.'], cwd=faux_remote_harness,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, err = p.communicate()
            self.assertEqual(p.returncode, 0, err)
            self.assertTrue(update_repos('file://%s' % faux_remote_harness,
                faux_local_harness) == 0, 'Gave returncode %d' % p.returncode)
        finally:
            rmtree(tmp_dir)
            rmtree(faux_local_harness)
