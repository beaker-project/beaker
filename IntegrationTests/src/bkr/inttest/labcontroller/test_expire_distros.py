# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import pkg_resources
import tempfile
import shutil
from bkr.server.model import session
from bkr.server.tests import data_setup
from bkr.inttest import Process
from bkr.inttest.labcontroller import LabControllerTestCase
from bkr.labcontroller.expire_distros import check_all_trees

class ExpireDistrosTest(LabControllerTestCase):

    @classmethod
    def setUpClass(cls):
        # Need to populate a directory with a fake distro tree, and serve it over 
        # HTTP, so that beaker-expire-distros can expire other missing distros.
        cls.distro_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(cls.distro_dir, 'fakedistros'))
        open(os.path.join(cls.distro_dir, 'fakedistros/MattAwesomelinux9'), 'w').write('lol')
        cls.distro_server = Process('http_server.py', args=[sys.executable,
                    pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                    '--base', cls.distro_dir],
                listen_port=19998)
        cls.distro_server.start()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.distro_dir, ignore_errors=True)
        cls.distro_server.stop()

    def setUp(self):
        # We need at least one working tree to exist in every test,
        # otherwise beaker-expire-distros will just bail out and refuse
        # to do anything as a safety feature.
        with session.begin():
            self.lc = self.get_lc()
            self.distro_tree = data_setup.create_distro_tree(
                    osmajor=u'MattAwesomelinux9', osminor=u'1',
                    arch=u'x86_64', lab_controllers=[self.lc],
                    urls=[u'http://localhost:19998/fakedistros/MattAwesomelinux9'])

    def test_200(self):
        check_all_trees(ignore_errors=True)
        with session.begin():
            session.expire_all()
            # The working tree should not be expired.
            self.assertTrue(any(dla.lab_controller == self.lc
                    for dla in self.distro_tree.lab_controller_assocs))

    def test_403(self):
        with session.begin():
            lc = self.get_lc()
            distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[lc],
                    urls=[u'http://localhost:19998/error/403'])
        check_all_trees(ignore_errors=True)
        with session.begin():
            session.expire_all()
            # The distro tree should not be expired.
            self.assertTrue(any(dla.lab_controller == self.lc
                    for dla in distro_tree.lab_controller_assocs))

    def test_404(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[self.lc],
                    urls=[u'http://localhost:19998/error/404'])
        check_all_trees(ignore_errors=True)
        with session.begin():
            session.expire_all()
            # The distro tree should be expired.
            self.assertFalse(any(dla.lab_controller == self.lc
                    for dla in distro_tree.lab_controller_assocs))

    def test_500(self):
        with session.begin():
            lc = self.get_lc()
            distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[lc],
                    urls=[u'http://localhost:19998/error/500'])
        check_all_trees(ignore_errors=True)
        with session.begin():
            session.expire_all()
            # The distro tree should not be expired.
            self.assertTrue(any(dla.lab_controller == self.lc
                    for dla in distro_tree.lab_controller_assocs))
