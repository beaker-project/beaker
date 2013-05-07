#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
from bkr.common.helpers import unlink_ignore
import unittest, time, re, os, shutil, turbogears
import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskPackage
import turbogears as tg

class TestSubmitTask(SeleniumTestCase):

    @classmethod
    def setupClass(cls):
        with session.begin():
            cls.uploader = data_setup.create_user(password=u'upload')
        cls.selenium = cls.get_selenium()
        cls.selenium.start()
        cls.login(user=cls.uploader.user_name, password=u'upload')

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()
        basepath = (turbogears.config.get('basepath.rpms'))
        # These may be missing if a test failed or wasn't run. We shouldn't
        # confuse matters further by complaining that they're missing.
        unlink_ignore(os.path.join(basepath, 'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'))
        unlink_ignore(os.path.join(basepath, 'tmp-distribution-beaker-dummy_for_bz681143-1.0-1.noarch.rpm'))

    def assert_task_upload_flash_OK(self, name):
        sel = self.selenium
        expected = '%s Added/Updated' % name
        actual = sel.get_text('css=.flash')
        failure_msg = "%s not in %s" % (expected, actual)
        self.assert_(expected in actual, failure_msg)

    def test_submit_task(self):
        test_package_name = '/distribution/beaker/task_test'
        sel = self.selenium
        sel.open('')

        # upload v1.1 first...
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assert_task_upload_flash_OK(test_package_name)
        # ...and make sure it worked...
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('30000')
        self.assert_task_correct_v1_1()
        self.assertEqual(self.get_task_info_field('Uploader'), self.uploader.user_name)
        self.assertEqual(self.get_task_info_field_href('Uploader'),
                'mailto:%s' % self.uploader.email_address)

        # ...then upload v2.0...
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-task_test-2.0-5.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assert_task_upload_flash_OK(test_package_name)
        # ...and make sure everything was updated
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('30000')
        self.assert_task_correct_v2_0()

    def assert_task_correct_v1_1(self):
        self.assertEqual(self.get_task_info_field('Description'),
                'Fake test for integration testing v1.1')
        self.assertEqual(self.get_task_info_field('Expected Time'), '5 minutes')
        self.assertEqual(self.get_task_info_field('Owner'), 'Nobody <nobody@example.com>')
        self.assertEqual(self.get_task_info_field('Version'), '1.1-1')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Regression')
        self.assertEqual(self.get_task_info_field('RPM'), 'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm')
        self.assertEqual(self.get_task_info_field_href('RPM'),
                # no /bkr prefix for /rpms served by Apache
                '/rpms/tmp-distribution-beaker-task_test-1.1-0.noarch.rpm')
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
                '/rpms/tmp-distribution-beaker-task_test-2.0-5.noarch.rpm')
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Priority'), 'Low')
        self.assertEqual(self.get_task_info_field('Destructive'), 'False')
        self.assertEqual(self.get_task_info_field('Requires'),
                '\n'.join(['beaker', 'coreutils', 'rpm']))

    def get_task_info_field(self, field_label):
        """Returns the value of a field in the task info table."""
        return self.selenium.get_text('//table[@class="show"]'
                '//td[preceding-sibling::td[1]//text()="%s:"]' % field_label)

    def get_task_info_field_href(self, field_label):
        """Returns the href of a link in the task info table."""
        return self.selenium.get_attribute('//table[@class="show"]'
                '//td[preceding-sibling::td[1]//text()="%s:"]/a@href' % field_label)

    # https://bugzilla.redhat.com/show_bug.cgi?id=681143
    def test_task_package_names_are_case_sensitive(self):
        test_package_name = '/distribution/beaker/dummy_for_bz681143'

        # There is a pre-existing TaskPackage in all lowercase...
        with session.begin():
            TaskPackage.lazy_create(package=u'opencryptoki')

        # But the task we are uploading has RunFor: openCryptoki, 
        # with uppercase C
        sel = self.selenium
        sel.open('')
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-dummy_for_bz681143-1.0-1.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assert_task_upload_flash_OK(test_package_name)
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('30009')
        # Should have openCryptoki in correct case:
        self.assertEqual(self.get_task_info_field('Run For'), 'openCryptoki')

    def test_task_invalid_file(self):
        invalidtask = 'invalid-task_file'
        sel = self.selenium
        sel.open('')
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                invalidtask))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Failed to import task: '
                'error reading package header')
        rpms = tg.config.get('basepath.rpms')
        self.assertEqual(os.path.exists('%s/%s' % (rpms,invalidtask)),False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=617274
    def test_task_without_owner_is_not_accepted(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-dummy_for_bz617274-1.0-1.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Failed to import task: '
                'Owner field not defined')


    # https://bugzilla.redhat.com/show_bug.cgi?id=915549
    def test_task_name_length(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                 pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-long-task-RPM-1.0-1.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), "Failed to import task: "
                  "'Task name should be <= 255 characters'")

if __name__ == "__main__":
    unittest.main()
