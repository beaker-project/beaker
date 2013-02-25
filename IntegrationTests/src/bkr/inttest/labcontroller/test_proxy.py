
import os, os.path
import xmlrpclib
import requests
from nose.plugins.skip import SkipTest
from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.labcontroller import LabControllerTestCase

class ClearNetbootTest(LabControllerTestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists('/etc/sudoers.d/beaker_proxy_clear_netboot'):
            raise SkipTest('sudoers config for clear_netboot is absent')

    def test_clear_netboot(self):
        with session.begin():
            system = data_setup.create_system()
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.clear_netboot(system.fqdn)
        with session.begin():
            self.assertEqual(system.command_queue[0].action, 'clear_netboot')

    def test_clear_netboot_GET(self):
        with session.begin():
            system = data_setup.create_system()
        response = requests.get(self.get_proxy_url() + 'nopxe/%s' % system.fqdn)
        response.raise_for_status()
        with session.begin():
            self.assertEqual(system.command_queue[0].action, 'clear_netboot')

class InstallStartTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_install_start(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.install_start(self.recipe.id)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.tasks[0].results[0].path, u'/start')

    def test_install_start_GET(self):
        response = requests.get('%sinstall_start/%s' %
                (self.get_proxy_url(), self.recipe.id))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.tasks[0].results[0].path, u'/start')

class InstallDoneTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_install_done(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.install_done(self.recipe.id, 'somefqdn')
        with session.begin():
            session.expire_all()
            self.assert_(self.recipe.resource.install_finished is not None)

    def test_install_done_GET(self):
        response = requests.get('%sinstall_done/%s/%s' %
                (self.get_proxy_url(), self.recipe.id, 'somefqdn'))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assert_(self.recipe.resource.install_finished is not None)

class PostrebootTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system(lab_controller=
                    data_setup.create_labcontroller(self.get_lc_fqdn()))
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe, system=self.system)

    def test_postreboot(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.postreboot(self.recipe.id)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.system.command_queue[0].action, 'reboot')

    def test_postreboot_GET(self):
        response = requests.get('%spostreboot/%s' %
                (self.get_proxy_url(), self.recipe.id))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.system.command_queue[0].action, 'reboot')
