
import os, os.path
from base64 import b64encode
import xmlrpclib
import requests
from nose.plugins.skip import SkipTest
from bkr.server.model import session
from bkr.labcontroller.config import get_conf
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

class FileUploadTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_recipe_file(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.recipe_upload_file(self.recipe.id, '/', 'recipe-log', 10, None, 0,
                b64encode('a' * 10))
        local_log_dir = '%s/recipes/%s/' % (get_conf().get('CACHEPATH'), self.recipe.id)
        with session.begin():
            self.assertEquals(self.recipe.logs[0].path, '/')
            self.assertEquals(self.recipe.logs[0].filename, 'recipe-log')
            self.assertEquals(self.recipe.logs[0].server,
                    'http://localhost/beaker/logs/recipes/%s/' % self.recipe.id)
            self.assertEquals(self.recipe.logs[0].basepath, local_log_dir)
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'recipe-log'), 'r').read(),
                    'aaaaaaaaaa')
        s.recipe_upload_file(self.recipe.id, '/', 'recipe-log', 10, None, 10,
                b64encode('b' * 10))
        with session.begin():
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'recipe-log'), 'r').read(),
                    'aaaaaaaaaabbbbbbbbbb')

    def test_recipetask_file(self):
        with session.begin():
            task = self.recipe.tasks[0]
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.task_upload_file(task.id, '/', 'task-log', 10, None, 0,
                b64encode('a' * 10))
        local_log_dir = '%s/tasks/%s/' % (get_conf().get('CACHEPATH'), task.id)
        with session.begin():
            self.assertEquals(task.logs[0].path, '/')
            self.assertEquals(task.logs[0].filename, 'task-log')
            self.assertEquals(task.logs[0].server,
                    'http://localhost/beaker/logs/tasks/%s/' % task.id)
            self.assertEquals(task.logs[0].basepath, local_log_dir)
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'task-log'), 'r').read(),
                    'aaaaaaaaaa')
        s.task_upload_file(task.id, '/', 'task-log', 10, None, 10,
                b64encode('b' * 10))
        with session.begin():
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'task-log'), 'r').read(),
                    'aaaaaaaaaabbbbbbbbbb')

    def test_recipetaskresult_file(self):
        with session.begin():
            self.recipe.tasks[0].pass_('', 0, 'Pass')
            result = self.recipe.tasks[0].results[0]
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.result_upload_file(result.id, '/', 'result-log', 10, None, 0,
                b64encode('a' * 10))
        local_log_dir = '%s/results/%s/' % (get_conf().get('CACHEPATH'), result.id)
        with session.begin():
            self.assertEquals(result.logs[0].path, '/')
            self.assertEquals(result.logs[0].filename, 'result-log')
            self.assertEquals(result.logs[0].server,
                    'http://localhost/beaker/logs/results/%s/' % result.id)
            self.assertEquals(result.logs[0].basepath, local_log_dir)
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'result-log'), 'r').read(),
                    'aaaaaaaaaa')
        s.result_upload_file(result.id, '/', 'result-log', 10, None, 10,
                b64encode('b' * 10))
        with session.begin():
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'result-log'), 'r').read(),
                    'aaaaaaaaaabbbbbbbbbb')
