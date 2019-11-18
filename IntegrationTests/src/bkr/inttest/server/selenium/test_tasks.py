# encoding: utf8

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import urlparse
import requests
import requests.exceptions
from bkr.inttest.server.selenium import WebDriverTestCase, XmlRpcTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as requests_login, patch_json
import unittest as unittest
import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskPackage, Task, OSMajor
from sqlalchemy.sql import func
import turbogears as tg


class TestSubmitTask(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.uploader = data_setup.create_user(password=u'upload')
            # Make sure the Releases values we are using in the test cases
            # below are already known to Beaker, otherwise they will be ignored.
            OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinuxServer5')
            OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinuxClient5')
            OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinux7')
            OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinux6')
        self.browser = self.get_browser()
        login(self.browser, user=self.uploader.user_name, password=u'upload')

    def assert_task_upload_task_header(self, name):
        expected = 'Task %s' % name
        self.browser.find_element_by_xpath('//h1[text()[contains(., "%s")]]' % expected)

    def test_submit_task(self):
        test_package_name = '/distribution/beaker/task_test'
        b = self.browser

        # upload v1.1 first...
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header(test_package_name)
        self.assert_task_correct_v1_1()
        self.assertEqual(self.get_task_info_field('Uploader'), self.uploader.user_name)
        self.assertEqual(self.get_task_info_field_href('Uploader'),
                         'mailto:%s' % self.uploader.email_address)

        # ...then upload v2.0...
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header(test_package_name)
        # ...and make sure everything was updated
        self.assert_task_correct_v2_0()

    def assert_task_correct_v1_1(self):
        self.assertEqual(self.get_task_info_field('Description'),
                         'Fake test for integration testing v1.1')
        self.assertEqual(self.get_task_info_field('Expected Time'), '5 minutes')
        self.assertEqual(self.get_task_info_field('Owner'), 'Nobody <nobody@example.com>')
        self.assertEqual(self.get_task_info_field('Version'), '1.1-0')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Regression')
        self.assertEqual(self.get_task_info_field('RPM'),
                         'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm')
        self.assertEqual(self.get_task_info_field_href('RPM'),
                         # no /bkr prefix for /rpms served by Apache
                         urlparse.urljoin(get_server_base(),
                                          '/rpms/tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Requires'), 'beaker')

    def assert_task_correct_v2_0(self):
        self.assertEqual(self.get_task_info_field('Description'),
                         'Fake test for integration testing v2.0')
        self.assertEqual(self.get_task_info_field('Expected Time'), '30 minutes')
        self.assertEqual(self.get_task_info_field('Owner'), 'Nobody <nobody@example.com>')
        self.assertEqual(self.get_task_info_field('Version'), '2.0-5')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Multihost')
        self.assertEqual(self.get_task_info_field('RPM'),
                         'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        self.assertEqual(self.get_task_info_field_href('RPM'),
                         # no /bkr prefix for /rpms served by Apache
                         urlparse.urljoin(get_server_base(),
                                          '/rpms/tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'))
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Priority'), 'Low')
        self.assertEqual(self.get_task_info_field('Destructive'), 'false')
        self.assertEqual(self.get_task_info_field('Requires'),
                         '\n'.join(['beaker', 'coreutils', 'rpm']))

    def get_task_info_field(self, field_label):
        """Returns the value of a field in the task info table."""
        return self.browser.find_element_by_xpath('//table'
                                                  '//td[preceding-sibling::th/text()="%s"]' % field_label).text

    def get_task_info_field_href(self, field_label):
        """Returns the href of a link in the task info table."""
        return self.browser.find_element_by_xpath('//table'
                                                  '//td[preceding-sibling::th/text()="%s"]/a' % field_label) \
            .get_attribute('href')

    # https://bugzilla.redhat.com/show_bug.cgi?id=681143
    def test_task_package_names_are_case_sensitive(self):
        test_package_name = '/distribution/beaker/dummy_for_bz681143'

        # There is a pre-existing TaskPackage in all lowercase...
        with session.begin():
            TaskPackage.lazy_create(package=u'opencryptoki')

        # But the task we are uploading has RunFor: openCryptoki,
        # with uppercase C
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker-dummy_for_bz681143-1.0-1.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header(test_package_name)
        # Should have openCryptoki in correct case:
        self.assertEqual(self.get_task_info_field('Run For'), 'openCryptoki')

    def test_task_invalid_file(self):
        invalidtask = 'invalid-task_file'
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/' + invalidtask))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          'Failed to import task: error reading package header')
        rpms = tg.config.get('basepath.rpms')
        self.assertEqual(os.path.exists('%s/%s' % (rpms, invalidtask)), False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=617274
    def test_task_without_owner_is_not_accepted(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker-dummy_for_bz617274-1.0-1.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          'Failed to import task: Owner field not defined')

    # https://bugzilla.redhat.com/show_bug.cgi?id=915549
    def test_task_name_length(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker-long-task-RPM-1.0-1.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          'Failed to import task: Task name should be <= 255 characters')

    # https://bugzilla.redhat.com/show_bug.cgi?id=859796
    def test_task_name_with_redundant_slashes_is_rejected(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker----redundant_slashes-1.0-0.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          "Failed to import task: Task name must not contain redundant slashes")

    # https://bugzilla.redhat.com/show_bug.cgi?id=859796
    def test_task_name_with_trailing_slash_is_rejected(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
            pkg_resources.resource_filename('bkr.inttest.server',
                                            'task-rpms/tmp-distribution-beaker-trailing_slash--1.0-0.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          "Failed to import task: Task name must not end with slash")

    def test_upload_duplicate_task_version_is_rejected(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm1_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                    'task-rpms/tmp-test-cannot-add-same-version-WebUI-tasks-1.1.4-0.noarch.rpm')
        same_version_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                           'task-rpms/tmp-test-cannot-add-same-version-WebUI-1-tasks-1.1.4-0.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm1_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/CoreOS/tmp/Sanity/a-few-descriptive-words')
        b.get(get_server_base() + 'tasks/new')
        # Upload same version of rpm package should show warning message.
        b.find_element_by_id('task_task_rpm').send_keys(same_version_rpm)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEqual(b.find_element_by_css_selector('.alert.flash').text,
                         'Failed to import task: Failed to import, 1.1.4-0 is the same version we already have')

    # https://bugzilla.redhat.com/show_bug.cgi?id=972407
    def test_submit_no_task(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          "No task RPM specified")

    # https://bugzilla.redhat.com/show_bug.cgi?id=1092758
    def test_arm_related_arches_are_accepted(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-arm-related-arches-1.0-0.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/arm-related-arches')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1226443
    def test_unrecognised_fields_in_testinfo_are_ignored(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-dummy_for_bz1226443-1.0-1.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/dummy_for_bz1226443')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1491658
    def test_non_ascii_owner_is_accepted(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-dummy_for_bz1491658-1.0-0.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/dummy_for_bz1491658')
        self.assertEqual(self.get_task_info_field('Owner'), u'Gęśla Jaźń <gj@example.com>')

    def test_excluded_releases(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-excluded-releases-1.0-1.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/excluded-releases')
        self.assertEqual(self.get_task_info_field('Excluded OSMajors'),
                         'RedHatEnterpriseLinuxClient5\n'
                         'RedHatEnterpriseLinuxServer5')

    # https://bugzilla.redhat.com/show_bug.cgi?id=800455
    def test_exclusive_releases(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-exclusive-releases-1.0-1.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/exclusive-releases')
        self.assertEqual(self.get_task_info_field('Exclusive OSMajors'),
                         'RedHatEnterpriseLinux6\n'
                         'RedHatEnterpriseLinux7')

    # https://bugzilla.redhat.com/show_bug.cgi?id=670149
    def test_excluded_architectures(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-excluded-arches-1.0-1.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/excluded-arches')
        self.assertEqual(self.get_task_info_field('Excluded Arches'), 'ia64')

    def test_exclusive_architectures(self):
        b = self.browser
        b.get(get_server_base() + 'tasks/new')
        rpm_path = pkg_resources.resource_filename('bkr.inttest.server',
                                                   'task-rpms/tmp-distribution-beaker-exclusive-arches-1.0-1.noarch.rpm')
        b.find_element_by_id('task_task_rpm').send_keys(rpm_path)
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_task_header('/distribution/beaker/exclusive-arches')
        self.assertEqual(self.get_task_info_field('Exclusive Arches'), 'x86_64')


class TaskDisable(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.my_task = data_setup.create_task()
            self.normal_user = data_setup.create_user(password=u'secret')
        self.browser = self.get_browser()

    def test_task_disable_successful(self):
        login(self.browser, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        b = self.browser
        b.get(get_server_base() + 'tasks/%s' % self.my_task.id)
        b.find_element_by_xpath('//td[../th[text()="Valid"] and ./text()="true"]')
        b.find_element_by_xpath('//button[contains(text(), "Disable") and not(@disabled)]').click()
        b.find_element_by_xpath('//button[text()="OK"]').click()
        b.find_element_by_xpath('//td[../th[text()="Valid"] and ./text()="false"]')
        b.find_element_by_xpath('//button[contains(text(), "Disable") and @disabled]')

    def test_task_disable_not_available_normal_user(self):
        login(self.browser, user=self.normal_user.user_name, password=u'secret')
        b = self.browser
        b.get(get_server_base() + 'tasks/%s' % self.my_task.id)
        b.find_element_by_xpath('//button[not(contains(text(), "Disable"))]')


class TaskHTTPTest(DatabaseTestCase):

    def setUp(self):
        super(TaskHTTPTest, self).setUp()
        with session.begin():
            self.my_task = data_setup.create_task()
            self.normal_user = data_setup.create_user(password=u'secret')

    def test_task_update_disable_successful(self):
        req_sess = requests.Session()
        requests_login(req_sess, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        self.assertEqual(self.my_task.valid, True)
        response = patch_json(get_server_base() + 'tasks/%s' % self.my_task.id,
                              session=req_sess, data={'disabled': True})
        response.raise_for_status()
        self.assertEqual(response.json()['valid'], False)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.my_task.valid, False)

    def test_task_update_disable_normal_user_fail(self):
        req_sess = requests.Session()
        requests_login(req_sess, self.normal_user.user_name, 'secret')
        self.assertEqual(self.my_task.valid, True)
        response = patch_json(get_server_base() + 'tasks/%s' % self.my_task.id,
                              session=req_sess, data={'disabled': True})
        self.assertEqual(response.status_code, 403)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.my_task.valid, True)

    def test_task_update_task_not_available_404(self):
        req_sess = requests.Session()
        with session.begin():
            result = session.query(func.max(Task.id)).first()
        fake_id = result[0] + 1
        requests_login(req_sess, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        response = patch_json(get_server_base() + 'tasks/%s' % fake_id,
                              session=req_sess, data={'disabled': True})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, 'Task %s does not exist' % fake_id)


class TasksXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    def test_filter_by_osmajor(self):
        with session.begin():
            included = data_setup.create_task()
            excluded = data_setup.create_task(
                exclude_osmajors=[u'MagentaGloveLinux4'])
        result = self.server.tasks.filter(dict(osmajor=u'MagentaGloveLinux4'))
        task_names = [task['name'] for task in result]
        self.assertIn(included.name, task_names)
        self.assertNotIn(excluded.name, task_names)

    def test_filter_by_distro(self):
        with session.begin():
            distro = data_setup.create_distro(osmajor=u'MagentaGloveLinux5')
            included = data_setup.create_task()
            excluded = data_setup.create_task(
                exclude_osmajors=[u'MagentaGloveLinux5'])
        result = self.server.tasks.filter(dict(distro_name=distro.name))
        task_names = [task['name'] for task in result]
        self.assertIn(included.name, task_names)
        self.assertNotIn(excluded.name, task_names)

    def test_exclusive_arches(self):
        with session.begin():
            task = data_setup.create_task(runfor=[u'httpd'],
                                          exclusive_arches=[u's390', u's390x'])
        result = self.server.tasks.filter(dict(packages=['httpd']))
        self.assertEquals(result[0]['name'], task.name)
        # Note that the 'arches' key is actually the *excluded* arches.
        self.assertEquals(result[0]['arches'],
                          ['aarch64', 'arm', 'armhfp', 'i386', 'ia64', 'ppc', 'ppc64', 'ppc64le',
                           'x86_64'])


if __name__ == "__main__":
    unittest.main()
