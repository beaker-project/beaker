
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import delete_and_confirm, \
    get_server_base, is_text_present, login, wait_for_animation
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session
from bkr.server.model import Group

# XXX Merge into test_jobs.py
class JobDeleteWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.password = 'password'
            self.user = data_setup.create_user(password=self.password)
            self.job_to_delete = data_setup. \
                create_completed_job(owner=self.user)
            self.job_to_delete_2 = data_setup. \
                create_completed_job(owner=self.user)
        self.browser = self.get_browser()

    def test_submission_delegate_with_group(self):
        with session.begin():
            group = data_setup.create_group()
            self.job_to_delete.group = group
            self.job_to_delete_2.group = group
        self.test_submission_delegate()

    def test_submission_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.user.submission_delegates[:] = [submission_delegate]
        login(self.browser, submission_delegate.user_name, 'password')
        # Go to the jobs page and search for our job
        job = self.job_to_delete
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text("Show Search Options").click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('jobsearch-0.table'))\
                .select_by_visible_text('Id')
        Select(b.find_element_by_name('jobsearch-0.operation'))\
                .select_by_visible_text('is')
        b.find_element_by_name('jobsearch-0.value').clear()
        b.find_element_by_name('jobsearch-0.value'). \
            send_keys('%s' % job.id)
        b.find_element_by_id('searchform').submit()
        # We are only a submission delegate, not the submitter,
        # check we cannot delete
        action_text = b.find_element_by_xpath("//td[preceding-sibling::td/"
            "a[normalize-space(text())='%s']]/"
            "div[contains(@class, 'job-action-container')]" % job.t_id).text
        self.assertTrue('Delete' not in action_text)
        # Now go to the individual job page to test for the lack
        # of a 'Delete' link
        b.get(get_server_base() + 'jobs/%d' % \
            job.id)
        b.find_element_by_xpath('//body[not(.//button[normalize-space(string(.))="Delete"])]')

        # Ok add our delegates as the submitters
        with session.begin():
            self.job_to_delete.submitter = submission_delegate
            self.job_to_delete_2.submitter = submission_delegate
        # Now let's see if we can do some deleting
        self.job_delete_jobpage(self.job_to_delete_2)
        self.job_delete(self.job_to_delete)

    def test_group_job_member(self):
        with session.begin():
            new_user = data_setup.create_user(password='password')
            group = data_setup.create_group()
            group.add_member(new_user)
            self.job_to_delete.group = group
            self.job_to_delete_2.group = group
        login(self.browser, new_user.user_name, 'password')
        self.job_delete_jobpage(self.job_to_delete_2)
        self.job_delete(self.job_to_delete)

    def test_admin(self):
        login(self.browser)
        self.job_delete(self.job_to_delete)
        self.job_delete_jobpage(self.job_to_delete_2)

    def test_not_admin(self):
        login(self.browser, user=self.user.user_name, password=self.password)
        self.job_delete(self.job_to_delete)
        self.job_delete_jobpage(self.job_to_delete_2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1330405
    def test_can_cancel_delete_modal_successfully(self):
        login(self.browser)
        b = self.browser
        job = self.job_to_delete
        b.get(get_server_base() + 'jobs/%d' % job.id)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Delete"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
                'delete this job?"]')
        modal.find_element_by_xpath('.//button[text()="Cancel"]').click()
        # if delete action is cancelled, the modal is dismissed
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')

    def job_delete_jobpage(self, job):
        b = self.browser
        b.get(get_server_base() + 'jobs/%d' % \
            job.id)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Delete"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
                'delete this job?"]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        # once it's deleted we are returned to My Jobs grid
        b.find_element_by_xpath('.//title[text()="My Jobs"]')

    def job_delete(self, job):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text("Show Search Options").click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('jobsearch-0.table'))\
                .select_by_visible_text('Id')
        Select(b.find_element_by_name('jobsearch-0.operation'))\
                .select_by_visible_text('is')
        b.find_element_by_name('jobsearch-0.value').clear()
        b.find_element_by_name('jobsearch-0.value'). \
            send_keys('%s' % job.id)
        b.find_element_by_id('searchform').submit()

        delete_and_confirm(b, "//tr[td/a[normalize-space(text())='%s']]" % job.t_id)
        # table should have no remaining rows, since we searched by id
        b.find_element_by_xpath("//table[@id='widget']/tbody[not(./tr)]")
        b.get(get_server_base() + 'jobs/%d' % job.id)
        self.assertIn('This job has been deleted.',
                b.find_element_by_class_name('alert-warning').text)
