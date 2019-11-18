# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.server.model import TaskResult
from bkr.inttest import get_server_base
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup


# OLD, DEPRECATED JOB PAGE ONLY

class JobAckTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def check_cannot_review(self):
        self.browser.find_element_by_xpath('.//*[@class="recipeset" and '
                                           'not(.//div[contains(@class, "ackpanel")])]')

    def review(self, recipeset, response='Nak'):
        b = self.browser
        rs = b.find_element_by_xpath('//*[@id="RS_%s"]' % recipeset.id)
        # click response radio button
        rs.find_element_by_xpath('.//label[normalize-space(string(.))="%s"]/input'
                                 % response).click()
        rs.find_element_by_xpath('.//span[text()="Success"]')

        with session.begin():
            session.refresh(recipeset)
            if response == 'Nak':
                self.assertTrue(recipeset.waived)
            else:
                self.assertFalse(recipeset.waived)

    def test_cannot_review_unfinished_recipesets(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            owner.use_old_job_page = True
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_running(job)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.check_cannot_review()

    def test_owner_can_review(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            owner.use_old_job_page = True
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.review(job.recipesets[0])

    def test_other_users_cannot_review(self):
        with session.begin():
            user = data_setup.create_user(password=u'other_user')
            user.use_old_job_page = True
            job = data_setup.create_job()
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=user.user_name, password='other_user')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.check_cannot_review()

    def test_group_member_cannot_review_non_group_job(self):
        with session.begin():
            owner = data_setup.create_user()
            member = data_setup.create_user(password=u'group_member')
            member.use_old_job_page = True
            group = data_setup.create_group()
            group.add_member(owner)
            group.add_member(member)
            job = data_setup.create_job(owner=owner, group=None)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=member.user_name, password='group_member')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.check_cannot_review()

    def test_group_member_can_review_group_job(self):
        with session.begin():
            owner = data_setup.create_user()
            member = data_setup.create_user(password=u'group_member')
            member.use_old_job_page = True
            group = data_setup.create_group()
            group.add_member(owner)
            group.add_member(member)
            job = data_setup.create_job(owner=owner, group=group)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=member.user_name, password='group_member')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.review(job.recipesets[0])

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_ack_change(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            owner.use_old_job_page = True
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_complete(job, result=TaskResult.pass_)
            self.assertEquals(job.result, TaskResult.pass_)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        rs = b.find_element_by_xpath('//*[@id="RS_%s"]' % job.recipesets[0].id)
        rs.find_element_by_xpath('.//label[normalize-space(string(.))="Nak"]/input').click()
        rs.find_element_by_xpath('.//span[text()="Success"]')
        with session.begin():
            self.assertEquals(job.recipesets[0].activity[0].service, u'WEBUI')
            self.assertEquals(job.recipesets[0].activity[0].field_name, 'Ack/Nak')
            self.assertEquals(job.recipesets[0].activity[0].object_name(),
                              'RecipeSet: %s' % job.recipesets[0].id)
            self.assertEquals(job.recipesets[0].activity[0].old_value, u'ack')
            self.assertEquals(job.recipesets[0].activity[0].new_value, u'nak')
