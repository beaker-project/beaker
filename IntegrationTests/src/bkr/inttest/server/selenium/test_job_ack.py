
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from nose.plugins.skip import SkipTest
from turbogears.database import session
from bkr.server.model import TaskResult
from bkr.inttest import get_server_base, stop_process, start_process, \
    edit_file, CONFIG_FILE
from bkr.inttest.server.webdriver_utils import login, logout
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup


class JobAckTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def check_cannot_review(self):
        self.browser.find_element_by_xpath('.//*[@class="recipeset" and '
                'not(.//div[contains(@class, "ackpanel")])]')

    def review(self, recipeset, response='Nak', comment='fnord'):
        b = self.browser
        rs = b.find_element_by_xpath('//*[@id="RS_%s"]' % recipeset.id)
        # click response radio button
        rs.find_element_by_xpath('.//label[normalize-space(string(.))="%s"]/input'
                % response).click()
        rs.find_element_by_xpath('.//span[text()="Success"]')
        # click comment link
        rs.find_element_by_link_text('comment').click()
        # click edit button in modal
        b.find_element_by_xpath('//*[contains(@class, "ui-dialog")]'
                '//button[text()="Edit"]').click()
        # type comment
        textarea = b.find_element_by_xpath('//*[contains(@class, "ui-dialog")]//textarea')
        textarea.clear()
        textarea.send_keys(comment)
        # click save button in modal
        b.find_element_by_xpath('//*[contains(@class, "ui-dialog")]'
                '//button[text()="Save"]').click()
        rs.find_element_by_xpath('.//span[text()="Comment saved"]')

        with session.begin():
            session.refresh(recipeset)
            self.assertEquals(unicode(recipeset.nacked.response).lower(),
                    response.lower())
            self.assertEquals(recipeset.nacked.comment, comment)

    def test_cannot_review_unfinished_recipesets(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_running(job)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.check_cannot_review()

    def test_passed_recipeset_is_acked_by_default(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_complete(job, result=TaskResult.pass_)
            self.assertEquals(job.result, TaskResult.pass_)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        ack_checkbox = b.find_element_by_xpath('//label[normalize-space(string(.))="Ack"]/input')
        self.assertTrue(ack_checkbox.is_selected())

    def test_failed_recipeset_is_not_reviewed_by_default(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
            self.assertEquals(job.result, TaskResult.fail)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        review_checkbox = b.find_element_by_xpath(
                '//label[normalize-space(string(.))="Needs Review"]/input')
        self.assertTrue(review_checkbox.is_selected())
        # comment link should be hidden until the recipe set is reviewed
        comment_link = b.find_element_by_xpath(
                '//*[@class="recipeset"]//a[text()="comment"]')
        self.assertFalse(comment_link.is_displayed())

    def test_owner_can_review(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=owner)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.review(job.recipesets[0])

    def test_other_users_cannot_review(self):
        with session.begin():
            user = data_setup.create_user(password=u'other_user')
            job = data_setup.create_job()
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=user.user_name, password='other_user')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.check_cannot_review()

    def test_group_member_can_review_non_group_job(self):
        # This is a legacy permission which will go away eventually (see below)
        with session.begin():
            owner = data_setup.create_user()
            member = data_setup.create_user(password=u'group_member')
            group = data_setup.create_group()
            data_setup.add_user_to_group(owner, group)
            data_setup.add_user_to_group(member, group)
            job = data_setup.create_job(owner=owner, group=None)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=member.user_name, password='group_member')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.review(job.recipesets[0])

    def test_group_member_can_review_group_job(self):
        with session.begin():
            owner = data_setup.create_user()
            member = data_setup.create_user(password=u'group_member')
            group = data_setup.create_group()
            data_setup.add_user_to_group(owner, group)
            data_setup.add_user_to_group(member, group)
            job = data_setup.create_job(owner=owner, group=group)
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        b = self.browser
        login(b, user=member.user_name, password='group_member')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.review(job.recipesets[0])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1000861
    # This will be deleted when legacy permissions are dropped
    # in a future release (0.17?)
    def test_disable_legacy_perms(self):
        try:
            stop_process('gunicorn')
        except ValueError:
            # It seems gunicorn is not a running process
            raise SkipTest('Can only run this test against gunicorn')
        try:
            tmp_config = edit_file(CONFIG_FILE,
                'beaker.deprecated_job_group_permissions.on = True',
                'beaker.deprecated_job_group_permissions.on = False')
            start_process('gunicorn', env={'BEAKER_CONFIG_FILE': tmp_config.name})

            with session.begin():
                owner = data_setup.create_user()
                member = data_setup.create_user(password=u'group_member')
                group = data_setup.create_group()
                data_setup.add_user_to_group(owner, group)
                data_setup.add_user_to_group(member, group)
                job = data_setup.create_job(owner=owner, group=None)
                data_setup.mark_job_complete(job, result=TaskResult.fail)
            b = self.browser
            login(b, user=member.user_name, password='group_member')
            b.get(get_server_base() + 'jobs/%s' % job.id)
            self.check_cannot_review()
        finally:
            stop_process('gunicorn')
            start_process('gunicorn')

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_ack_change(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
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
            self.assertEquals(job.recipesets[0].activity[0].object_name(), 'RecipeSet: %s' % job.recipesets[0].id)
            self.assertEquals(job.recipesets[0].activity[0].old_value, u'ack')
            self.assertEquals(job.recipesets[0].activity[0].new_value, u'nak')
