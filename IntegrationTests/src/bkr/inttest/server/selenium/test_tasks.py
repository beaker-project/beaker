
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import urlparse
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from bkr.common.helpers import unlink_ignore
import unittest2 as unittest
import time, re, os, shutil, turbogears
import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskPackage
import turbogears as tg

class TestSubmitTask(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.uploader = data_setup.create_user(password=u'upload')
        self.browser = self.get_browser()
        login(self.browser, user=self.uploader.user_name, password=u'upload')

    @classmethod
    def teardownClass(cls):
        basepath = (turbogears.config.get('basepath.rpms'))
        # These may be missing if a test failed or wasn't run. We shouldn't
        # confuse matters further by complaining that they're missing.
        unlink_ignore(os.path.join(basepath, 'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'))
        unlink_ignore(os.path.join(basepath, 'tmp-distribution-beaker-dummy_for_bz681143-1.0-1.noarch.rpm'))

    def assert_task_upload_flash_OK(self, name):
        expected = '%s Added/Updated' % name
        actual = self.browser.find_element_by_class_name('flash').text
        self.assertIn(expected, actual)

    def test_submit_task(self):
        test_package_name = '/distribution/beaker/task_test'
        b = self.browser

        # upload v1.1 first...
        b.get(get_server_base() + 'tasks/new')
        b.find_element_by_id('task_task_rpm').send_keys(
                pkg_resources.resource_filename('bkr.inttest.server',
                                                'task-rpms/tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        b.find_element_by_xpath('//button[text()="Upload"]').click()
        self.assert_task_upload_flash_OK(test_package_name)
        # ...and make sure it worked...
        b.find_element_by_name('simplesearch').send_keys(test_package_name)
        b.find_element_by_id('simpleform').submit()
        b.find_element_by_link_text(test_package_name).click()
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
        self.assert_task_upload_flash_OK(test_package_name)
        # ...and make sure everything was updated
        b.find_element_by_name('simplesearch').send_keys(test_package_name)
        b.find_element_by_id('simpleform').submit()
        b.find_element_by_link_text(test_package_name).click()
        self.assert_task_correct_v2_0()

    def assert_task_correct_v1_1(self):
        self.assertEqual(self.get_task_info_field('Description'),
                'Fake test for integration testing v1.1')
        self.assertEqual(self.get_task_info_field('Expected Time'), '5 minutes')
        self.assertEqual(self.get_task_info_field('Owner'), 'Nobody <nobody@example.com>')
        self.assertEqual(self.get_task_info_field('Version'), '1.1-0')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Regression')
        self.assertEqual(self.get_task_info_field('RPM'), 'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm')
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
        self.assertEqual(self.get_task_info_field('RPM'), 'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        self.assertEqual(self.get_task_info_field_href('RPM'),
                # no /bkr prefix for /rpms served by Apache
                urlparse.urljoin(get_server_base(),
                    '/rpms/tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'))
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Priority'), 'Low')
        self.assertEqual(self.get_task_info_field('Destructive'), 'False')
        self.assertEqual(self.get_task_info_field('Requires'),
                '\n'.join(['beaker', 'coreutils', 'rpm']))

    def get_task_info_field(self, field_label):
        """Returns the value of a field in the task info table."""
        return self.browser.find_element_by_xpath('//table'
                '//td[preceding-sibling::th/text()="%s"]' % field_label).text

    def get_task_info_field_href(self, field_label):
        """Returns the href of a link in the task info table."""
        return self.browser.find_element_by_xpath('//table'
                '//td[preceding-sibling::th/text()="%s"]/a' % field_label)\
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
        self.assert_task_upload_flash_OK(test_package_name)
        b.find_element_by_name('simplesearch').send_keys(test_package_name)
        b.find_element_by_id('simpleform').submit()
        b.find_element_by_link_text(test_package_name).click()
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
        self.assertEqual(os.path.exists('%s/%s' % (rpms,invalidtask)),False)

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

    #https://bugzilla.redhat.com/show_bug.cgi?id=972407
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
        self.assert_task_upload_flash_OK('/distribution/beaker/arm-related-arches')

if __name__ == "__main__":
    unittest.main()
