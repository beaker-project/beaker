#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os, shutil, turbogears
import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskPackage
import turbogears as tg

class TestSubmitTask(bkr.server.test.selenium.SeleniumTestCase):

    @classmethod
    def setupClass(cls):
        cls.selenium = cls.get_selenium()
        cls.selenium.start()
        cls.login()
    
    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()
        basepath = (turbogears.config.get('basepath.rpms'))
        os.remove(os.path.join(basepath, 'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        os.remove(os.path.join(basepath, 'tmp-distribution-beaker-task_test-2.0-2.noarch.rpm'))
        os.remove(os.path.join(basepath, 'tmp-distribution-beaker-dummy_for_bz681143-1.0-1.noarch.rpm'))

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
        self.assert_(('%s Added/Updated' % test_package_name)
                in sel.get_text('css=.flash'))
        # ...and make sure it worked...
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('30000')
        self.assert_task_correct_v1_1()

        # ...then upload v2.0...
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-task_test-2.0-2.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assert_(('%s Added/Updated' % test_package_name)
                in sel.get_text('css=.flash'))
        # ...and make sure everything was updated
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('30000')
        self.assert_task_correct_v2_0()

        # upload v1.1 again...
        sel.click('link=New Task')
        sel.wait_for_page_to_load('30000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        self.assert_(('Failed to import because we already have tmp-distribution-beaker-task_test-1.1-0.noarch.rpm')
                in sel.get_text('css=.flash'))
        # ...and make sure the 2.0 task data is in place
        sel.click('link=Task Library')
        sel.wait_for_page_to_load('30000')
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
        self.assertEqual(self.get_task_info_field('Version'), '1.1-1')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Regression')
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Requires'), 'beaker')

    def assert_task_correct_v2_0(self):
        self.assertEqual(self.get_task_info_field('Description'),
                'Fake test for integration testing v2.0')
        self.assertEqual(self.get_task_info_field('Expected Time'), '30 minutes')
        self.assertEqual(self.get_task_info_field('Version'), '2.0-2')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Multihost')
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Requires'),
                '\n'.join(['beaker', 'rpm', 'coreutils']))

    def get_task_info_field(self, field_label):
        """Returns the value of a field in the task info table."""
        return self.selenium.get_text('//table[@class="show"]'
                '//td[preceding-sibling::td[1]//text()="%s:"]' % field_label)

    # https://bugzilla.redhat.com/show_bug.cgi?id=681143
    def test_task_package_names_are_case_sensitive(self):
        test_package_name = '/distribution/beaker/dummy_for_bz681143'

        # There is a pre-existing TaskPackage in all lowercase...
        TaskPackage.lazy_create(package=u'opencryptoki')
        session.flush()

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
        self.assert_(('Failed to import because of error reading package header')
                in sel.get_text('css=.flash'))
        rpms = tg.config.get('basepath.rpms')
        self.assertEqual(os.path.exists('%s/%s' % (rpms,invalidtask)),False)

if __name__ == "__main__":
    unittest.main()
