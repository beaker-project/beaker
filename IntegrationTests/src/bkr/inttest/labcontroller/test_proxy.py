
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os, os.path
import re
import posixpath
import datetime
import tempfile
import copy
from base64 import b64encode
import xmlrpclib
import lxml.etree, lxml.html
from urlparse import urljoin
import requests
import time
from nose.plugins.skip import SkipTest
from bkr.common.helpers import total_seconds
from bkr.server.model import session, TaskResult, TaskStatus, LogRecipe, \
        LogRecipeTask, LogRecipeTaskResult, RecipeTask, RecipeTaskResult
from bkr.labcontroller.proxy import ProxyHelper
from bkr.labcontroller.config import get_conf
from bkr.inttest import data_setup
from bkr.inttest.assertions import assert_datetime_within
from bkr.inttest.labcontroller import LabControllerTestCase, processes, \
    config_file, daemons_running_externally

class GetRecipeGuestXML(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.job = data_setup.create_running_job(num_recipes=1,
                    num_guestrecipes=1,
                    lab_controller=self.get_lc())
            self.addCleanup(self.cleanup_job, self.job)
            self.system_recipe = self.job.recipesets[0].recipes[0]
            self.guest_recipe = self.job.recipesets[0].recipes[0].guests[0]

    def test_GET_guests_host(self):
        url = '%srecipes/%s/' % (self.get_proxy_url(), self.guest_recipe.id)
        response = requests.get(url, headers={'Accept': 'application/xml'})
        response.raise_for_status()
        self.assertEquals(response.headers['Content-Type'], 'application/xml')
        # should work without the Accept header as well
        response = requests.get(url)
        response.raise_for_status()
        self.assertEquals(response.headers['Content-Type'], 'application/xml')
        # Call through our API
        # Check the results are what we expect
        root = lxml.etree.fromstring(response.content)
        reported_host_fqdn = root.find('./recipeSet/recipe').get('system')
        self.assertEqual(self.system_recipe.resource.fqdn, reported_host_fqdn)


class GetRecipeTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def check_recipe_xml(self, xml):
        root = lxml.etree.fromstring(xml)
        self.assertEquals(root.tag, 'job')
        self.assertEquals(root.find('./recipeSet/recipe').get('id'),
                str(self.recipe.id))
        # add more assertions here...

    def test_xmlrpc_get_my_recipe(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        recipe_xml = s.get_my_recipe({'recipe_id': self.recipe.id})
        self.check_recipe_xml(recipe_xml)

    def test_xmlrpc_get_recipe_custom_distro(self):
        with session.begin():
            self.recipe = data_setup.create_recipe(custom_distro=True)
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)
            # These are optional attributes
            self.recipe.installation.distro_name = None
            self.recipe.installation.variant = None
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        recipe_xml = s.get_my_recipe({'recipe_id': self.recipe.id})
        self.check_recipe_xml(recipe_xml)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1279871
    def test_xmlrpc_with_charset_param_is_not_rejected(self):
        # Need to send the XMLRPC request manually with requests, so that we
        # can customise the Content-Type request header.
        xmlrpc_url = self.get_proxy_url() + 'RPC2'
        xmlrpc_request_body = """
            <?xml version="1.0"?>
            <methodCall>
                <methodName>get_my_recipe</methodName>
                <params>
                    <param>
                        <value><struct>
                            <member>
                                <name>recipe_id</name>
                                <value><int>%s</int></value>
                            </member>
                        </struct></value>
                    </param>
                </params>
            </methodCall>
            """ % self.recipe.id
        response = requests.post(xmlrpc_url, data=xmlrpc_request_body,
                headers={'Content-Type': 'text/xml; charset=utf-8'})
        response.raise_for_status()

    def test_GET_recipe(self):
        url = '%srecipes/%s/' % (self.get_proxy_url(), self.recipe.id)
        response = requests.get(url, headers={'Accept': 'application/xml'})
        response.raise_for_status()
        self.assertEquals(response.headers['Content-Type'], 'application/xml')
        self.check_recipe_xml(response.content)
        # should work without the Accept header as well
        response = requests.get(url)
        response.raise_for_status()
        self.assertEquals(response.headers['Content-Type'], 'application/xml')
        self.check_recipe_xml(response.content)

class TaskResultTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def check_result(self, result_id, result_type, path, score, log):
        with session.begin():
            session.expire_all()
            result = self.recipe.tasks[0].results[0]
            self.assertEquals(result.id, result_id)
            self.assertEquals(result.result, result_type)
            self.assertEquals(result.path, path)
            self.assertEquals(result.score, score)
            self.assertEquals(result.log, log)

    def test_xmlrpc_pass(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        result_id = s.task_result(self.recipe.tasks[0].id, u'pass_',
                u'/random/junk', 123, u'The thing worked')
        self.check_result(result_id, TaskResult.pass_, u'/random/junk', 123,
                u'The thing worked')

    def test_xmlrpc_fail(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        result_id = s.task_result(self.recipe.tasks[0].id, u'fail',
                u'/random/junk', 456, u'The thing failed')
        self.check_result(result_id, TaskResult.fail, u'/random/junk', 456,
                u'The thing failed')

    def test_xmlrpc_warn(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        result_id = s.task_result(self.recipe.tasks[0].id, u'warn',
                u'/random/junk', -1, u'The thing broke')
        self.check_result(result_id, TaskResult.warn, u'/random/junk', -1,
                u'The thing broke')

    def test_xmlrpc_panic(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        result_id = s.task_result(self.recipe.tasks[0].id, u'panic',
                u'/random/junk', 0, u'The thing really broke')
        self.check_result(result_id, TaskResult.panic, u'/random/junk', 0,
                u'The thing really broke')

    def test_POST_pass(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Pass',
                path='/random/junk', score='123', message='The thing worked'))
        self.assertEquals(response.status_code, 201)
        self.assert_(response.headers['Location'].startswith(results_url),
                response.headers['Location'])
        result_id = int(posixpath.basename(response.headers['Location']))
        self.check_result(result_id, TaskResult.pass_, u'/random/junk', 123,
                u'The thing worked')

    def test_POST_fail(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Fail',
                path='/random/junk', score='456', message='The thing failed'))
        self.assertEquals(response.status_code, 201)
        self.assert_(response.headers['Location'].startswith(results_url),
                response.headers['Location'])
        result_id = int(posixpath.basename(response.headers['Location']))
        self.check_result(result_id, TaskResult.fail, u'/random/junk', 456,
                u'The thing failed')

    def test_POST_warn(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Warn',
                path='/random/junk', score='-1', message='The thing broke'))
        self.assertEquals(response.status_code, 201)
        self.assert_(response.headers['Location'].startswith(results_url),
                response.headers['Location'])
        result_id = int(posixpath.basename(response.headers['Location']))
        self.check_result(result_id, TaskResult.warn, u'/random/junk', -1,
                u'The thing broke')

    def test_POST_none(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='None',
                path='/random/junk', message='See elsewhere for results'))
        self.assertEquals(response.status_code, 201)
        self.assert_(response.headers['Location'].startswith(results_url),
                response.headers['Location'])
        result_id = int(posixpath.basename(response.headers['Location']))
        self.check_result(result_id, TaskResult.none, u'/random/junk', None,
                u'See elsewhere for results')

    def test_POST_skip(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Skip',
                path='/', message='Did not run'))
        self.assertEquals(response.status_code, 201)
        self.assert_(response.headers['Location'].startswith(results_url),
                response.headers['Location'])
        result_id = int(posixpath.basename(response.headers['Location']))
        self.check_result(result_id, TaskResult.skip, u'/', None,
                u'Did not run')

    def test_POST_missing_result(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(asdf='lol'),
                allow_redirects=False)
        self.assertEquals(response.status_code, 400)

    def test_POST_unknown_result(self):
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Eggplant'),
                allow_redirects=False)
        self.assertEquals(response.status_code, 400)

    # https://bugzilla.redhat.com/show_bug.cgi?id=962254
    def test_result_for_finished_task(self):
        with session.begin():
            self.recipe.tasks[0].stop()
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Pass'),
                allow_redirects=False)
        self.assertEquals(response.status_code, 409)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1293007
    def test_max_results_per_recipe_limit_is_enforced(self):
        with session.begin():
            RecipeTaskResult.__table__.insert().values([
                {'recipe_task_id': self.recipe.tasks[0].id,
                 'result': TaskResult.pass_, 'path': u'test-bz1293007',
                 'score': i, 'start_time': datetime.datetime.utcnow()}
                for i in range(7500)]).execute()
            session.expire(self.recipe.tasks[0])
            self.assertEqual(len(self.recipe.tasks[0].results), 7500)
        # Test XMLRPC endpoint
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        with self.assertRaisesRegexp(xmlrpclib.Fault, 'Too many results'):
            s.task_result(self.recipe.tasks[0].id, 'pass_', '/', 0, 'Should fail')
        # Test POST endpoint
        results_url = '%srecipes/%s/tasks/%s/results/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(results_url, data=dict(result='Pass'))
        self.assertEqual(response.status_code, 403)
        self.assertIn('Too many results in recipe', response.text)
        # Warning result should have been recorded, but only once
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.recipe.tasks[0].results), 7501)
            self.assertEqual(self.recipe.tasks[0].results[-1].path, u'/')
            self.assertEqual(self.recipe.tasks[0].results[-1].log,
                    u'Too many results in recipe')

class TaskStatusTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe(task_list=[
                    data_setup.create_task(), data_setup.create_task()])
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_xmlrpc_task_start(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.task_start(self.recipe.tasks[0].id)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.running)

    def test_xmlrpc_task_stop(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.task_stop(self.recipe.tasks[0].id, 'stop')
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.completed)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1322219
    def test_cannot_complete_aborted_task(self):
        # The scenario is that the task itself invokes rhts-abort -t recipe,
        # which aborts all tasks, and then the harness tries to complete the
        # task. We want the task to stay Aborted, not Completed, so the stop
        # request should fail.
        with session.begin():
            self.recipe.abort(u'someone ran rhts-abort -t recipe')
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        try:
            s.task_stop(self.recipe.tasks[0].id, 'stop')
            self.fail('should raise')
        except xmlrpclib.Fault as fault:
            self.assertIn('Cannot change status for finished task',
                    fault.faultString)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.aborted)

    def test_xmlrpc_task_abort(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.task_stop(self.recipe.tasks[0].id, 'abort', 'fooed the bar up')
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.aborted)
            self.assertEquals(task.results[-1].log, u'fooed the bar up')

    def test_POST_task_status(self):
        status_url = '%srecipes/%s/tasks/%s/status' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(status_url, data=dict(status='Running'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.running)
        response = requests.post(status_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.completed)

    def test_retry_POST_task_status(self):
        # It may happen that harness will try to update status to already completed tasks.
        # We have to make sure we will respond to this correctly - status code 409

        status_url = '%srecipes/%s/tasks/%s/status' % (self.get_proxy_url(),
                                                       self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(status_url, data=dict(status='Running'))
        self.assertEquals(response.status_code, 204)
        response = requests.post(status_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.completed)
        response = requests.post(status_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 409)
        self.assertIn('Cannot change status for finished task', response.text)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.completed)

    def test_POST_task_abort(self):
        status_url = '%srecipes/%s/tasks/%s/status' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(status_url, data=dict(status='Aborted',
                message='fooed the bar up'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.aborted)
            self.assertEquals(task.results[-1].log, u'fooed the bar up')

    def test_POST_missing_status(self):
        status_url = '%srecipes/%s/tasks/%s/status' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(status_url, data=dict(asdf='lol'))
        self.assertEquals(response.status_code, 400)

    def test_POST_invalid_transition(self):
        status_url = '%srecipes/%s/tasks/%s/status' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.post(status_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 204)
        response = requests.post(status_url, data=dict(status='Running'))
        self.assertEquals(response.status_code, 409)

class UpdateTaskTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe(task_name=u'/distribution/check-install')
            self.recipe.tasks.extend([
                RecipeTask.from_task(data_setup.create_task()),
                RecipeTask.from_fetch_url(u'http://example.com/tasks/example.tar.bz2'),
            ])
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_start_and_complete_task(self):
        # This simulates the traditional beah style where the task comes from
        # the task library, and its name and version are already known. We just
        # set it to Running and then to Completed.
        task_url = '%srecipes/%s/tasks/%s/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[1].id)
        response = requests.patch(task_url, data=dict(status='Running'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.json()['status'], 'Running')
        with session.begin():
            task = self.recipe.tasks[1]
            session.refresh(task)
            self.assertEquals(task.status, TaskStatus.running)
        response = requests.patch(task_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.json()['status'], 'Completed')
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[1]
            self.assertEquals(task.status, TaskStatus.completed)

    def test_start_and_complete_external_task(self):
        # Alternative harnesses which support external tasks can report back
        # the name and version of the task after they fetch it.
        task_url = '%srecipes/%s/tasks/%s/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[2].id)
        name = '/external/example'
        version = '3.14-1'
        response = requests.patch(task_url, data=dict(status='Running',
                name=name, version=version))
        self.assertEquals(response.status_code, 200)
        json = response.json()
        self.assertEquals(json['status'], 'Running')
        self.assertEquals(json['name'], name)
        self.assertEquals(json['version'], version)
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[2]
            self.assertEquals(task.status, TaskStatus.running)
            self.assertEquals(task.name, name)
            self.assertEquals(task.version, version)
        response = requests.patch(task_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.json()['status'], 'Completed')
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[2]
            self.assertEquals(task.status, TaskStatus.completed)

    def test_abort_task(self):
        task_url = '%srecipes/%s/tasks/%s/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.patch(task_url, data=dict(status='Aborted',
                message='fooed the bar up'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.json()['status'], 'Aborted')
        with session.begin():
            session.expire_all()
            task = self.recipe.tasks[0]
            self.assertEquals(task.status, TaskStatus.aborted)
            self.assertEquals(task.results[-1].log, u'fooed the bar up')

    def test_invalid_status_transition(self):
        task_url = '%srecipes/%s/tasks/%s/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[0].id)
        response = requests.patch(task_url, data=dict(status='Completed'))
        self.assertEquals(response.status_code, 200)
        response = requests.patch(task_url, data=dict(status='Running'))
        self.assertEquals(response.status_code, 409)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1072133
    def test_initial_watchdog_set_correctly(self):
        # When a task is started the watchdog is implicitly extended to the
        # task's expected time plus 30 minutes.
        task_url = '%srecipes/%s/tasks/%s/' % (self.get_proxy_url(),
                self.recipe.id, self.recipe.tasks[1].id)
        response = requests.patch(task_url, data=dict(status='Running'))
        response.raise_for_status()
        with session.begin():
            self.assertEquals(self.recipe.tasks[1].task.avg_time, 1200)
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=3000))

class RecipeStatusTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe(task_list=[
                    data_setup.create_task(), data_setup.create_task()])
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_xmlrpc_recipe_abort(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.recipe_stop(self.recipe.id, 'abort', 'fooed the bar up')
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe.tasks[0].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[0].results[-1].log,
                    u'fooed the bar up')
            self.assertEquals(self.recipe.tasks[1].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[1].results[-1].log,
                    u'fooed the bar up')

    def test_POST_recipe_abort(self):
        status_url = '%srecipes/%s/status' % (self.get_proxy_url(),
                self.recipe.id)
        response = requests.post(status_url, data=dict(status='Aborted',
                message='fooed the bar up'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe.tasks[0].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[0].results[-1].log,
                    u'fooed the bar up')
            self.assertEquals(self.recipe.tasks[1].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[1].results[-1].log,
                    u'fooed the bar up')


class WatchdogTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_xmlrpc_extend_watchdog(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        result_id = s.extend_watchdog(self.recipe.tasks[0].id, 600)
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))

    def test_GET_watchdog(self):
        with session.begin():
            self.recipe.extend(100)
        watchdog_url = '%srecipes/%s/watchdog' % (self.get_proxy_url(),
                self.recipe.id)
        response = requests.get(watchdog_url)
        response.raise_for_status()
        self.assertAlmostEquals(response.json()['seconds'], 100, delta=5)

    def test_POST_watchdog(self):
        watchdog_url = '%srecipes/%s/watchdog' % (self.get_proxy_url(),
                self.recipe.id)
        response = requests.post(watchdog_url, data=dict(seconds=600))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))

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
            data_setup.mark_recipe_waiting(self.recipe)

    def test_install_start(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.install_start(self.recipe.id)
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.installation.install_started,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(hours=3))

    def test_install_start_GET(self):
        response = requests.get('%sinstall_start/%s' %
                (self.get_proxy_url(), self.recipe.id))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.installation.install_started,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(hours=3))

    # https://bugzilla.redhat.com/show_bug.cgi?id=954219
    def test_install_start_faulty(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())

        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe)

        s.install_start(recipe.id)
        with session.begin():
            session.expire_all()
            start1_kill_time = recipe.watchdog.kill_time

        # a buggy second start report
        time.sleep(1)
        s.install_start(recipe.id)
        with session.begin():
            session.expire_all()
            start2_kill_time = recipe.watchdog.kill_time

        self.assertTrue(start1_kill_time == start2_kill_time)

class InstallDoneTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            job = data_setup.create_job(num_guestrecipes=1)
            data_setup.mark_recipe_running(job.recipesets[0].recipes[0])
            data_setup.mark_recipe_installing(job.recipesets[0].recipes[0].guests[0])
            # On a normal (machine) recipe, the fqdn reported in the
            # install_done call is just discarded since we already know the
            # machine's real FQDN. For this test we use a guest recipe, so that
            # the reported FQDN will be filled in by the install_done call.
            self.recipe = job.recipesets[0].recipes[0].guests[0]
            self.assertIsNone(self.recipe.resource.fqdn)

    def test_install_done(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.install_done(self.recipe.id, 'somefqdn')
        with session.begin():
            session.expire_all()
            self.assertIsNotNone(self.recipe.installation.install_finished)
            self.assertEquals(self.recipe.resource.fqdn, 'somefqdn')

    def test_install_done_GET(self):
        response = requests.get('%sinstall_done/%s/%s' %
                (self.get_proxy_url(), self.recipe.id, 'somefqdn'))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIsNotNone(self.recipe.installation.install_finished)
            self.assertEquals(self.recipe.resource.fqdn, 'somefqdn')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1412897
    def test_install_done_without_fqdn(self):
        response = requests.get('%sinstall_done/%s/' %
                (self.get_proxy_url(), self.recipe.id))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIsNotNone(self.recipe.installation.install_finished)
            self.assertEquals(self.recipe.resource.fqdn, None)


class InstallFailTest(LabControllerTestCase):
    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe(num_tasks=2)
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_installing(self.recipe)

    def test_install_fail(self):
        s = xmlrpclib.Server(self.get_proxy_url())
        s.install_fail(self.recipe.id)
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe.tasks[0].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[1].status, TaskStatus.aborted)

    def test_install_fail_get(self):
        response = requests.get(
            reduce(urljoin,
                   [self.get_proxy_url(),
                    'install_fail/',
                    '{}'.format(self.recipe.id)]
                   )
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe.tasks[0].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[0].results[-1].log, u'Installation failed')
            self.assertEquals(self.recipe.tasks[1].status, TaskStatus.aborted)
            self.assertEquals(self.recipe.tasks[1].results[-1].log, u'Installation failed')

class PostrebootTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system(lab_controller=self.get_lc())
            self.recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([self.recipe])
            self.addCleanup(self.cleanup_job, job)
            data_setup.mark_recipe_running(self.recipe, system=self.system)

    def test_postreboot(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.postreboot(self.recipe.id)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.system.command_queue[0].action, 'on')
            self.assertEqual(self.system.command_queue[1].action, 'off')

    def test_postreboot_GET(self):
        response = requests.get('%spostreboot/%s' %
                (self.get_proxy_url(), self.recipe.id))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.system.command_queue[0].action, 'on')
            self.assertEqual(self.system.command_queue[1].action, 'off')

class PowerTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.get_lc())
            self.target_system = data_setup.create_system(lab_controller=self.get_lc())
            recipe = data_setup.create_recipe()
            target_recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe, target_recipe])
            self.addCleanup(self.cleanup_job, job)
            data_setup.mark_recipe_running(recipe, system=system)
            data_setup.mark_recipe_running(target_recipe, system=self.target_system)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1501671
    def test_power(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        s.power(self.target_system.fqdn, 'off')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.target_system.command_queue[0].action, 'off')

    def test_put_power(self):
        power_url = '%spower/%s/' % (self.get_proxy_url(), self.target_system.fqdn)
        response = requests.put(power_url, data=dict(action='reboot'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.target_system.command_queue[0].action, 'on')
            self.assertEqual(self.target_system.command_queue[1].action, 'off')

        response = requests.put(power_url, data=dict(action='on'))
        self.assertEquals(response.status_code, 204)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.target_system.command_queue[0].action, 'on')
            self.assertEqual(self.target_system.command_queue[1].action, 'on')
            self.assertEqual(self.target_system.command_queue[2].action, 'off')

    def test_put_power_error(self):
        power_url = '%spower/%s/' % (self.get_proxy_url(), self.target_system.fqdn)
        response = requests.put(power_url, data=dict(action='nonexistentcase'))
        self.assertEquals(response.status_code, 400)

    def test_put_power_json(self):
        power_url = '%spower/%s/' % (self.get_proxy_url(), self.target_system.fqdn)
        response = requests.put(power_url, json=dict(action='off'))
        self.assertEquals(response.status_code, 204, response.text)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.target_system.command_queue[0].action, 'off')

    def test_put_power_missing_action(self):
        power_url = '%spower/%s/' % (self.get_proxy_url(), self.target_system.fqdn)
        response = requests.put(power_url, data=dict(status='off'))
        self.assertEquals(response.status_code, 400, response.text)

    def test_put_power_unsupported(self):
        power_url = '%spower/%s/' % (self.get_proxy_url(), self.target_system.fqdn)
        response = requests.put(power_url)
        self.assertEquals(response.status_code, 415, response.text)


class LogUploadTestRestartProxy(LabControllerTestCase):

    @classmethod
    def setUpClass(cls):
        if daemons_running_externally():
            raise SkipTest('Too hard to control daemon process')

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def tearDown(self):
        # Ensure beaker-proxy is started
        # before every test run
        for p in processes:
            if p.name == 'beaker-proxy':
                beaker_proxy_process = p
                break
        if beaker_proxy_process.popen.poll() is not None:
            beaker_proxy_process.start()

    def test_modified_log_url_old_config_option(self):
        self._run_modified_log_url('SERVER')

    def test_modified_log_url_new_config_option(self):
        self._run_modified_log_url('URL_DOMAIN')

    def _run_modified_log_url(self, config_arg):
        # Stop beaker-proxy
        beaker_proxy_process = None
        for p in processes:
            if p.name == 'beaker-proxy':
                beaker_proxy_process = p
                break
        if not beaker_proxy_process:
            self.fail('Could not find beaker-proxy process')
        beaker_proxy_process.stop()
        with open(config_file, 'r') as f:
            contents = f.read()
        contents = re.sub('URL_DOMAIN = "localhost"', '', contents)
        contents = contents + "\nURL_SCHEME='https'\n%s='testingme.com'\n" % \
            config_arg
        tmp_config = tempfile.NamedTemporaryFile()
        tmp_config.write(contents)
        tmp_config.flush()
        old_args = copy.copy(beaker_proxy_process.args)
        new_args = []
        for arg in beaker_proxy_process.args:
            if arg != config_file:
                new_args.append(arg)
            else:
                new_args.append(tmp_config.name)
        beaker_proxy_process.args = new_args
        beaker_proxy_process.start()
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.recipe_upload_file(self.recipe.id, '/', 'recipe-log', 10, None, 0,
                b64encode('a' * 10))

        with session.begin():
            self.assertEquals(self.recipe.logs[0].server,
                    'https://testingme.com/beaker/logs/recipes/%s+/%s/'
                    % (self.recipe.id // 1000, self.recipe.id))
        beaker_proxy_process.stop()
        beaker_proxy_process.args = old_args
        beaker_proxy_process.start()


class LogUploadTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_log_storage_base_url(self):
        proxy = ProxyHelper(URL_SCHEME='https', URL_DOMAIN='testingme.com')
        self.assertEquals(proxy.log_storage.base_url, 'https://testingme.com/beaker/logs/')

    def test_xmlrpc_recipe_log(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.recipe_upload_file(self.recipe.id, '/', 'recipe-log', 10, None, 0,
                b64encode('a' * 10))
        local_log_dir = '%s/recipes/%s+/%s/' % (get_conf().get('CACHEPATH'),
                self.recipe.id // 1000, self.recipe.id)
        with session.begin():
            self.assertEquals(self.recipe.logs[0].path, '/')
            self.assertEquals(self.recipe.logs[0].filename, 'recipe-log')
            self.assertEquals(self.recipe.logs[0].server,
                    '%s/beaker/logs/recipes/%s+/%s/'
                    % (self.get_log_base_url(), self.recipe.id // 1000, self.recipe.id))
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=962253
    def test_xmlrpc_recipe_log_after_finished(self):
        with session.begin():
            data_setup.mark_recipe_complete(self.recipe, only=True)
            assert self.recipe.is_finished()
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        try:
            s.recipe_upload_file(self.recipe.id, '/', 'recipe-log', 10, None, 0,
                    b64encode('a' * 10))
            self.fail('should raise')
        except xmlrpclib.Fault, fault:
            self.assert_('Cannot register file for finished recipe'
                    in fault.faultString)

    def test_PUT_recipe_log(self):
        upload_url = '%srecipes/%s/logs/PUT-recipe-log' % (self.get_proxy_url(),
                self.recipe.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 204)
        local_log_dir = '%s/recipes/%s+/%s/' % (get_conf().get('CACHEPATH'),
                self.recipe.id // 1000, self.recipe.id)
        with session.begin():
            self.assertEquals(self.recipe.logs[0].path, '/')
            self.assertEquals(self.recipe.logs[0].filename, 'PUT-recipe-log')
            self.assertEquals(self.recipe.logs[0].server,
                    '%s/beaker/logs/recipes/%s+/%s/'
                    % (self.get_log_base_url(), self.recipe.id // 1000, self.recipe.id))
            self.assertEquals(self.recipe.logs[0].basepath, local_log_dir)
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'PUT-recipe-log'), 'r').read(),
                    'aaaaaaaaaa')
        response = requests.put(upload_url, data='b' * 10,
                headers={'Content-Range': 'bytes 10-19/20'})
        self.assertEquals(response.status_code, 204)
        with session.begin():
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'PUT-recipe-log'), 'r').read(),
                    'aaaaaaaaaabbbbbbbbbb')
        response = requests.get(upload_url)
        response.raise_for_status()
        self.assertEquals(response.content, 'aaaaaaaaaabbbbbbbbbb')

    # https://bugzilla.redhat.com/show_bug.cgi?id=962253
    def test_PUT_recipe_log_after_finished(self):
        with session.begin():
            data_setup.mark_recipe_complete(self.recipe, only=True)
            assert self.recipe.is_finished()
        upload_url = '%srecipes/%s/logs/PUT-recipe-log' % (self.get_proxy_url(),
                self.recipe.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 409)

    def test_xmlrpc_task_log(self):
        with session.begin():
            task = self.recipe.tasks[0]
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.task_upload_file(task.id, '/', 'task-log', 10, None, 0,
                b64encode('a' * 10))
        local_log_dir = '%s/tasks/%s+/%s/' % (get_conf().get('CACHEPATH'),
                task.id // 1000, task.id)
        with session.begin():
            self.assertEquals(task.logs[0].path, '/')
            self.assertEquals(task.logs[0].filename, 'task-log')
            self.assertEquals(task.logs[0].server,
                    '%s/beaker/logs/tasks/%s+/%s/'
                    % (self.get_log_base_url(), task.id // 1000, task.id))
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=962253
    def test_xmlrpc_task_log_after_finished(self):
        with session.begin():
            task = self.recipe.tasks[0]
            task.stop()
            assert task.is_finished()
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        try:
            s.task_upload_file(task.id, '/', 'task-log', 10, None, 0,
                    b64encode('a' * 10))
            self.fail('should raise')
        except xmlrpclib.Fault, fault:
            self.assert_('Cannot register file for finished task'
                    in fault.faultString)

    def test_PUT_task_log(self):
        with session.begin():
            task = self.recipe.tasks[0]
        upload_url = '%srecipes/%s/tasks/%s/logs/PUT-task-log' % (self.get_proxy_url(),
                self.recipe.id, task.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 204)
        local_log_dir = '%s/tasks/%s+/%s/' % (get_conf().get('CACHEPATH'),
                task.id // 1000, task.id)
        with session.begin():
            self.assertEquals(task.logs[0].path, '/')
            self.assertEquals(task.logs[0].filename, 'PUT-task-log')
            self.assertEquals(task.logs[0].server,
                    '%s/beaker/logs/tasks/%s+/%s/'
                    % (self.get_log_base_url(), task.id // 1000, task.id))
            self.assertEquals(task.logs[0].basepath, local_log_dir)
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'PUT-task-log'), 'r').read(),
                    'aaaaaaaaaa')
        response = requests.put(upload_url, data='b' * 10,
                headers={'Content-Range': 'bytes 10-19/20'})
        self.assertEquals(response.status_code, 204)
        with session.begin():
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'PUT-task-log'), 'r').read(),
                    'aaaaaaaaaabbbbbbbbbb')
        response = requests.get(upload_url)
        response.raise_for_status()
        self.assertEquals(response.content, 'aaaaaaaaaabbbbbbbbbb')

    # https://bugzilla.redhat.com/show_bug.cgi?id=962253
    def test_PUT_task_log_after_finished(self):
        with session.begin():
            task = self.recipe.tasks[0]
            task.stop()
            assert task.is_finished()
        upload_url = '%srecipes/%s/tasks/%s/logs/after-finished' % (self.get_proxy_url(),
                self.recipe.id, task.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 409)

    def test_xmlrpc_result_log(self):
        with session.begin():
            self.recipe.tasks[0].pass_(u'', 0, u'Pass')
            result = self.recipe.tasks[0].results[0]
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        s.result_upload_file(result.id, '/', 'result-log', 10, None, 0,
                b64encode('a' * 10))
        local_log_dir = '%s/results/%s+/%s/' % (get_conf().get('CACHEPATH'),
                result.id // 1000, result.id)
        with session.begin():
            self.assertEquals(result.logs[0].path, '/')
            self.assertEquals(result.logs[0].filename, 'result-log')
            self.assertEquals(result.logs[0].server,
                    '%s/beaker/logs/results/%s+/%s/'
                    % (self.get_log_base_url(), result.id // 1000, result.id))
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=962253
    def test_xmlrpc_result_log_after_finished(self):
        with session.begin():
            self.recipe.tasks[0].pass_(u'', 0, u'Pass')
            result = self.recipe.tasks[0].results[0]
            self.recipe.tasks[0].stop()
            assert self.recipe.tasks[0].is_finished()
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        try:
            s.result_upload_file(result.id, '/', 'result-log-after-finished',
                    10, None, 0, b64encode('a' * 10))
            self.fail('should raise')
        except xmlrpclib.Fault, fault:
            self.assert_('Cannot register file for finished task'
                    in fault.faultString)

    def test_PUT_result_log(self):
        with session.begin():
            task = self.recipe.tasks[0]
            task.pass_(u'', 0, u'Pass')
            result = self.recipe.tasks[0].results[0]
        upload_url = '%srecipes/%s/tasks/%s/results/%s/logs/PUT-result-log' % (
                self.get_proxy_url(), self.recipe.id, task.id, result.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 204)
        local_log_dir = '%s/results/%s+/%s/' % (get_conf().get('CACHEPATH'),
                result.id // 1000, result.id)
        with session.begin():
            self.assertEquals(result.logs[0].path, '/')
            self.assertEquals(result.logs[0].filename, 'PUT-result-log')
            self.assertEquals(result.logs[0].server,
                    '%s/beaker/logs/results/%s+/%s/'
                    % (self.get_log_base_url(), result.id // 1000, result.id))
            self.assertEquals(result.logs[0].basepath, local_log_dir)
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'PUT-result-log'), 'r').read(),
                    'aaaaaaaaaa')
        response = requests.put(upload_url, data='b' * 10,
                headers={'Content-Range': 'bytes 10-19/20'})
        self.assertEquals(response.status_code, 204)
        with session.begin():
            self.assertEquals(
                    open(os.path.join(local_log_dir, 'PUT-result-log'), 'r').read(),
                    'aaaaaaaaaabbbbbbbbbb')
        response = requests.get(upload_url)
        response.raise_for_status()
        self.assertEquals(response.content, 'aaaaaaaaaabbbbbbbbbb')

    # https://bugzilla.redhat.com/show_bug.cgi?id=962253
    def test_PUT_result_log_after_finished(self):
        with session.begin():
            task = self.recipe.tasks[0]
            task.pass_(u'', 0, u'Pass')
            result = self.recipe.tasks[0].results[0]
            task.stop()
            assert task.is_finished()
        upload_url = '%srecipes/%s/tasks/%s/results/%s/logs/after-finished' % (
                self.get_proxy_url(), self.recipe.id, task.id, result.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 409)

    def test_GET_nonexistent_log(self):
        log_url = '%srecipes/%s/logs/notexist' % (
                self.get_proxy_url(), self.recipe.id)
        response = requests.get(log_url)
        self.assertEquals(response.status_code, 404)

    # https://bugzilla.redhat.com/show_bug.cgi?id=961300
    def test_PUT_empty_log(self):
        upload_url = '%srecipes/%s/logs/empty-log' % (self.get_proxy_url(),
                self.recipe.id)
        local_log_dir = '%s/recipes/%s+/%s/' % (get_conf().get('CACHEPATH'),
                self.recipe.id // 1000, self.recipe.id)
        response = requests.put(upload_url, data='')
        self.assertEquals(response.status_code, 204)
        self.assertEquals(
                open(os.path.join(local_log_dir, 'empty-log'), 'r').read(),
                '')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1003454
    def test_large_xmlrpc_request_is_rejected(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        try:
            s.task_upload_file(123, 'debug', '.task_beah_raw', 4096, '', 1024,
                    'a' * (1024 * 1024 * 10 + 1))
            self.fail('should raise')
        except xmlrpclib.ProtocolError as e:
            self.assertEquals(e.errcode, 413)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1003454
    def test_large_PUT_request_is_rejected(self):
        upload_url = '%srecipes/%s/logs/asdf' % (self.get_proxy_url(),
                self.recipe.id)
        # No specified data content-type
        response = requests.put(upload_url, data='a' * (1024 * 1024 * 10 + 1))
        self.assertEquals(response.status_code, 413)
        # specify data content-type
        response = requests.put(upload_url, data='a' * (1024 * 1024 * 10 + 1),
                                headers={'content-type': 'application/x-url-encoded'})
        self.assertEquals(response.status_code, 413)


    # https://bugzilla.redhat.com/show_bug.cgi?id=1293007
    def test_max_logs_per_recipe_limit_is_enforced(self):
        with session.begin():
            self.recipe.tasks[0].pass_(path=u'test-bz1293007',
                    score=0, summary=u'Result with many logs')
            task = self.recipe.tasks[0]
            result = task.results[0]
            # 4000 task logs, 3500 result logs
            session.execute(LogRecipeTask.__table__.insert().values([
                {'recipe_task_id': task.id,
                 'path': u'/', 'filename': u'bz1293007.log',
                 'start_time': datetime.datetime.utcnow()}
                for i in range(4000)]))
            session.expire(task)
            self.assertEqual(len(task.logs), 4000)
            session.execute(LogRecipeTaskResult.__table__.insert().values([
                {'recipe_task_result_id': result.id,
                 'path': u'/', 'filename': u'bz1293007.log',
                 'start_time': datetime.datetime.utcnow()}
                for i in range(3500)]))
            session.expire(result)
            self.assertEqual(len(result.logs), 3500)
        # Test XMLRPC endpoint for result logs
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        with self.assertRaisesRegexp(xmlrpclib.Fault, 'Too many logs'):
            s.result_upload_file(result.id, '/', 'result-log', 10, None, 0,
                    b64encode('a' * 10))
        # Test POST endpoint for result logs
        upload_url = '%srecipes/%s/tasks/%s/results/%s/logs/too-many' % (
                self.get_proxy_url(), self.recipe.id, task.id, result.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 403)
        self.assertIn('Too many logs in recipe', response.text)
        # Test XMLRPC endpoint for task logs
        s = xmlrpclib.ServerProxy(self.get_proxy_url(), allow_none=True)
        with self.assertRaisesRegexp(xmlrpclib.Fault, 'Too many logs'):
            s.task_upload_file(task.id, '/', 'task-log', 10, None, 0,
                    b64encode('a' * 10))
        # Test POST endpoint for task logs
        upload_url = '%srecipes/%s/tasks/%s/logs/too-many' % (
                self.get_proxy_url(), self.recipe.id, task.id)
        response = requests.put(upload_url, data='a' * 10)
        self.assertEquals(response.status_code, 403)
        self.assertIn('Too many logs in recipe', response.text)
        # Warning result should have been recorded, but only once
        with session.begin():
            session.expire_all()
            self.assertEqual(len(task.results), 2)
            self.assertEqual(task.results[-1].path, u'/')
            self.assertEqual(task.results[-1].log, u'Too many logs in recipe')

class LogIndexTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)
            self.recipe.logs[:] = [LogRecipe(path=u'/', filename=u'console.log'),
                    LogRecipe(path=u'some-dir', filename=u'some-file.txt')]
            self.task = self.recipe.tasks[0]
            self.task.logs[:] = [LogRecipeTask(path=u'/', filename=u'TESTOUT.log'),
                    LogRecipeTask(path=u'debug', filename=u'.task_beah_raw')]
            self.task.pass_(u'', 0, u'Pass')
            self.result = self.recipe.tasks[0].results[0]
            self.result.logs[:] = [LogRecipeTaskResult(path=u'/', filename=u'test.log'),
                    LogRecipeTaskResult(path=u'some-dir', filename=u'some-file.txt')]

    def check_html_index(self, response, logs):
        self.assertEquals(response.headers['Content-Type'], 'text/html')
        tree = lxml.html.fromstring(response.content)
        links = tree.cssselect('ul li a')
        hrefs = [link.get('href') for link in links]
        self.assertEquals(hrefs, logs)

    def check_atom_index(self, response, logs):
        self.assertEquals(response.headers['Content-Type'], 'application/atom+xml')
        tree = lxml.etree.fromstring(response.content)
        entries = tree.findall('{http://www.w3.org/2005/Atom}entry')
        hrefs = [entry.find('{http://www.w3.org/2005/Atom}link').get('href')
                for entry in entries]
        self.assertEquals(hrefs, logs)

    def test_recipe_log_index_html(self):
        url = '%srecipes/%s/logs/' % (self.get_proxy_url(), self.recipe.id)
        response = requests.get(url, headers={'Accept': 'text/html'})
        response.raise_for_status()
        self.check_html_index(response, ['console.log', 'some-dir/some-file.txt'])
        # no Accept header should give us HTML as well
        response = requests.get(url)
        response.raise_for_status()
        self.check_html_index(response, ['console.log', 'some-dir/some-file.txt'])

    def test_recipe_log_index_atom(self):
        url = '%srecipes/%s/logs/' % (self.get_proxy_url(), self.recipe.id)
        response = requests.get(url, headers={'Accept': 'application/atom+xml'})
        response.raise_for_status()
        self.check_atom_index(response, ['console.log', 'some-dir/some-file.txt'])

    def test_task_log_index_html(self):
        url = '%srecipes/%s/tasks/%s/logs/' % (self.get_proxy_url(),
                self.recipe.id, self.task.id)
        response = requests.get(url, headers={'Accept': 'text/html'})
        response.raise_for_status()
        self.check_html_index(response, ['TESTOUT.log', 'debug/.task_beah_raw'])

    def test_task_log_index_atom(self):
        url = '%srecipes/%s/tasks/%s/logs/' % (self.get_proxy_url(),
                self.recipe.id, self.task.id)
        response = requests.get(url, headers={'Accept': 'application/atom+xml'})
        response.raise_for_status()
        self.check_atom_index(response, ['TESTOUT.log', 'debug/.task_beah_raw'])

    def test_result_log_index_html(self):
        url = '%srecipes/%s/tasks/%s/results/%s/logs/' % (self.get_proxy_url(),
                self.recipe.id, self.task.id, self.result.id)
        response = requests.get(url, headers={'Accept': 'text/html'})
        response.raise_for_status()
        self.check_html_index(response, ['test.log', 'some-dir/some-file.txt'])

    def test_result_log_index_atom(self):
        url = '%srecipes/%s/tasks/%s/results/%s/logs/' % (self.get_proxy_url(),
                self.recipe.id, self.task.id, self.result.id)
        response = requests.get(url, headers={'Accept': 'application/atom+xml'})
        response.raise_for_status()
        self.check_atom_index(response, ['test.log', 'some-dir/some-file.txt'])

class GetInstallationForSystemTest(LabControllerTestCase):

    def setUp(self):
        with session.begin():
            lab_controller = data_setup.create_labcontroller()
            self.tree_urls = [
                u'http://example.invalid/installationforsystem/',
                u'ftp://example.invalid/installationforsystem/',
                u'nfs://example.invalid:/installationforsystem/',
            ]
            self.distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[lab_controller], urls=self.tree_urls)
            self.recipe = data_setup.create_recipe(distro_tree=self.distro_tree)
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_waiting(self.recipe, lab_controller=lab_controller)

    # https://bugzilla.redhat.com/show_bug.cgi?id=978640
    def test_can_get_last_installation_info(self):
        s = xmlrpclib.ServerProxy(self.get_proxy_url())
        installinfo = s.get_installation_for_system(self.recipe.resource.fqdn)
        self.assertItemsEqual(installinfo['distro_tree_urls'], self.tree_urls)
        self.assertEqual(installinfo['kernel_url'],
                u'http://example.invalid/installationforsystem/pxeboot/vmlinuz')
        self.assertEqual(installinfo['initrd_url'],
                u'http://example.invalid/installationforsystem/pxeboot/initrd')
        self.assertEqual(installinfo['kernel_options'],
                         'inst.ks=%s netbootloader=pxelinux.0 noverifyssl'
                         % self.recipe.installation.rendered_kickstart.link)


class HealthTest(LabControllerTestCase):

    def setUp(self):
        self.healthz_url = '%shealthz/' % (self.get_proxy_url())

    def test_get_healthz(self):
        response = requests.get(self.healthz_url)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.text, 'We are healthy!')

    def test_head_healthz(self):
        response = requests.head(self.healthz_url)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.text, '')
