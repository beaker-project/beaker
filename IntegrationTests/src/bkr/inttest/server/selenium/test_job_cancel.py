
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import is_text_present, login, \
    wait_for_animation
from bkr.inttest import data_setup, get_server_base
from turbogears.database import session

# OLD, DEPRECATED JOB PAGE ONLY

class Cancel(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.password = 'password'
            self.user = data_setup.create_user(password=self.password)
            self.user.use_old_job_page = True
            self.job = data_setup.create_job(owner=self.user)
        self.browser = self.get_browser()

    def test_cancel_recipeset_group_job(self):
        b = self.browser
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user(password='password')
            user.use_old_job_page = True
            group.add_member(user)
            self.job.group = group
        login(b, user.user_name, 'password')
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="recipeset"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled recipeset %s"
            % self.job.recipesets[0].id))

    def test_cancel_group_job(self):
        b = self.browser
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user(password='password')
            user.use_old_job_page = True
            group.add_member(user)
            self.job.group = group
        login(b, user.user_name, 'password')
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[contains(@class, "job-action-container")]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled job %s"
            % self.job.id))

    def test_submission_delegate_cancel_with_group(self):
        with session.begin():
            group = data_setup.create_group()
            self.job.group = group
        self.test_submission_delegate_cancel_job()

    def test_submission_delegate_cancel_job(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            submission_delegate.use_old_job_page = True
            self.user.submission_delegates[:] = [submission_delegate]
        b = self.browser
        login(b, submission_delegate.user_name, password='password')

        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text("Show Search Options").click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('jobsearch-0.table'))\
                .select_by_visible_text('Id')
        Select(b.find_element_by_name('jobsearch-0.operation'))\
                .select_by_visible_text('is')
        b.find_element_by_name('jobsearch-0.value').clear()
        b.find_element_by_name('jobsearch-0.value'). \
            send_keys('%s' % self.job.id)
        b.find_element_by_id('searchform').submit()
        # We are only a submission delegate, but not the submitter,
        # check we cannot Cancel
        action_text = b.find_element_by_xpath("//td[preceding-sibling::td/"
            "a[normalize-space(text())='%s']]/"
            "div[contains(@class, 'job-action-container')]" % self.job.t_id).text
        self.assertTrue('Cancel' not in action_text)

        # Add as submitting user and refresh, try to cancel.
        with session.begin():
            self.job.submitter = submission_delegate
        b.refresh()
        b.find_element_by_xpath("//td[preceding-sibling::td/"
            "a[normalize-space(text())='%s']]/div//"
            "a[normalize-space(text())='Cancel']" % self.job.t_id).click()
        b.find_element_by_xpath("//input[@class='submitbutton' and @value='Yes']").click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            'Successfully cancelled job %s' % self.job.id)

    def test_owner_cancel_job(self):
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[contains(@class, "job-action-container")]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled job %s"
            % self.job.id))

    def test_owner_cancel_recipeset(self):
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="recipeset"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled recipeset %s"
            % self.job.recipesets[0].id))

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_job_cancel(self):
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[contains(@class, "job-action-container")]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled job %s"
                        % self.job.id))
        with session.begin():
            self.assertEquals(self.job.activity[0].service, u'WEBUI')
            self.assertEquals(self.job.activity[0].field_name, 'Status')
            self.assertEquals(self.job.activity[0].object_name(), 'Job: %s' % self.job.id)
            self.assertEquals(self.job.activity[0].action, u'Cancelled')

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_recipeset_cancel(self):
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="recipeset"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled recipeset %s"
                        % self.job.recipesets[0].id))
        with session.begin():
            self.assertEquals(self.job.recipesets[0].activity[0].service, u'WEBUI')
            self.assertEquals(self.job.recipesets[0].activity[0].field_name, 'Status')
            self.assertEquals(self.job.recipesets[0].activity[0].object_name(), 'RecipeSet: %s'
                              % self.job.recipesets[0].id)
            self.assertEquals(self.job.recipesets[0].activity[0].action, u'Cancelled')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173376
    def test_clear_rows_in_system_recipe_map(self):
        with session.begin():
            system = data_setup.create_system(owner=self.user)
            self.job.recipesets[0].recipes[0].systems[:] = [system]
        # check if rows in system_recipe_map
        self.assertNotEqual(len(self.job.recipesets[0].recipes[0].systems), 0)
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="recipeset"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled recipeset %s"
            % self.job.recipesets[0].id))
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.job.recipesets[0].recipes[0].systems), 0)
