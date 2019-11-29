# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
import lxml.etree
import time
import tempfile
import pkg_resources
from turbogears.database import session
from selenium.webdriver.common.keys import Keys
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import (login, is_text_present, logout,
                                                click_menu_item, BootstrapSelect)
from bkr.inttest import data_setup, with_transaction, get_server_base, DatabaseTestCase
from bkr.server.model import (RetentionTag, Product, Job, GuestRecipe,
                              TaskStatus, TaskPriority, RecipeSetComment)
from bkr.inttest.server.requests_utils import post_json, patch_json, login as requests_login


class TestViewJob(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def go_to_job_page(self, job, recipeset=None):
        url = get_server_base() + 'jobs/%s' % job.id
        if recipeset:
            url += '#set%s' % recipeset.id
        self.browser.get(url)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1362596
    def test_recipe_summary(self):
        with session.begin():
            job = data_setup.create_completed_job(
                recipe_whiteboard=u'thewhiteboard', role=u'SERVERS',
                distro_name=u'RHEL-6.8', variant=u'ComputeNode', arch=u'x86_64',
                fqdn=u'test-recipe-summary.example.invalid')
            recipe = job.recipesets[0].recipes[0]
        b = self.browser
        self.go_to_job_page(job)
        recipe_row = b.find_element_by_xpath(
            '//table[contains(@class, "job-recipes")]/tbody'
            '/tr[td/a[@class="recipe-id" and string(.)="R:%s"]]' % recipe.id)
        self.assertEqual(
            recipe_row.find_element_by_xpath('.//span[@class="recipe-whiteboard"]').text,
            u'thewhiteboard')
        self.assertEqual(
            recipe_row.find_element_by_xpath('.//span[@class="recipe-role"]').text,
            u'Role: SERVERS')
        self.assertEqual(
            recipe_row.find_element_by_xpath('.//span[@class="recipe-distro"]').text,
            u'RHEL-6.8 ComputeNode x86_64')
        self.assertEqual(
            recipe_row.find_element_by_xpath('.//span[@class="recipe-resource"]').text,
            u'test-recipe-summary.example.invalid')

    def test_group_job(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            job = data_setup.create_job(group=group)
        b = self.browser
        self.go_to_job_page(job)
        b.find_element_by_link_text(job.group.group_name).click()
        b.find_element_by_xpath('.//h1[normalize-space(text())="%s"]' % \
                                group.group_name)

    def test_job_owner_sees_edit_button(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]')

    def test_group_member_sees_edit_button_for_group_job(self):
        with session.begin():
            group = data_setup.create_group()
            job_owner = data_setup.create_user()
            group_member = data_setup.create_user(password=u'group_member')
            group.add_member(job_owner)
            group.add_member(group_member)
            job = data_setup.create_job(owner=job_owner, group=group)
        b = self.browser
        login(b, user=group_member.user_name, password=u'group_member')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]')

    def test_other_user_does_not_see_edit_button(self):
        with session.begin():
            other_user = data_setup.create_user(password=u'other_user')
            job = data_setup.create_job()
        b = self.browser
        login(b, user=other_user.user_name, password=u'other_user')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//body[not(.//button[normalize-space(string(.))="Edit"])]')

    def test_edit_cc_list(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            job = data_setup.create_job(owner=user,
                                        cc=[u'laika@mir.su', u'tereshkova@kosmonavt.su'])
        b = self.browser
        login(b, user=user.user_name, password='password')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]').click()
        modal = b.find_element_by_class_name('modal')
        input = modal.find_element_by_name('cc')
        self.assertEqual(
            input.get_attribute('value'),
            'laika@mir.su; tereshkova@kosmonavt.su')
        input.clear()
        input.send_keys('tereshkova@kosmonavt.su; gagarin@kosmonavt.su')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEquals(job.cc,
                              ['gagarin@kosmonavt.su', u'tereshkova@kosmonavt.su'])

    def test_edit_job_whiteboard(self):
        with session.begin():
            user = data_setup.create_user(password=u'asdf')
            job = data_setup.create_job(owner=user)
        b = self.browser
        login(b, user=user.user_name, password='asdf')
        self.go_to_job_page(job)
        new_whiteboard = 'new whiteboard value %s' % int(time.time())
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]').click()
        modal = b.find_element_by_class_name('modal')
        textarea = modal.find_element_by_name('whiteboard')
        self.assertEquals(textarea.get_attribute('value'), job.whiteboard)
        textarea.clear()
        textarea.send_keys(new_whiteboard)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath('//div[@class="job-whiteboard"]/p[text()="%s"]'
                                % new_whiteboard)
        with session.begin():
            session.refresh(job)
            self.assertEquals(job.whiteboard, new_whiteboard)

    def test_change_product(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'active',
                                        product=data_setup.create_product())
            new_product = data_setup.create_product()
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]').click()
        modal = b.find_element_by_class_name('modal')
        BootstrapSelect(modal.find_element_by_name('product')) \
            .select_by_visible_text(new_product.name)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEquals(job.product, new_product)

    def test_change_retention_tag(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'scratch')
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]').click()
        modal = b.find_element_by_class_name('modal')
        BootstrapSelect(modal.find_element_by_name('retention_tag')) \
            .select_by_visible_text('60days')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEquals(job.retention_tag.tag, u'60days')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1022333
    def test_change_retention_tag_clearing_product(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'active',
                                        product=data_setup.create_product())
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]').click()
        modal = b.find_element_by_class_name('modal')
        BootstrapSelect(modal.find_element_by_name('retention_tag')) \
            .select_by_visible_text('scratch')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEquals(job.retention_tag.tag, u'scratch')
            self.assertEquals(job.product, None)

    # https://bugzilla.redhat.com/show_bug.cgi?id=662703
    def test_product_dropdown_is_sorted(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'audit',
                                        product=data_setup.create_product())
            product_before = data_setup.create_product(u'aardvark')
            product_after = data_setup.create_product(u'zebra')
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]').click()
        modal = b.find_element_by_class_name('modal')
        options = BootstrapSelect(modal.find_element_by_name('product')).options
        before_pos = options.index(product_before.name)
        after_pos = options.index(product_after.name)
        self.assertLess(before_pos, after_pos)

    def test_cancel_job(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//div[@class="page-header"]'
                                '//button[normalize-space(string(.))="Cancel"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('message').send_keys('lecnac')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath(u'//div[@class="page-header"]'
                                u'//button[normalize-space(string(.))="Cancelling\u2026"]')
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(job.status, TaskStatus.cancelled)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1335370
    def test_cancel_job_submission_ctrl_enter(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//div[@class="page-header"]'
                                '//button[normalize-space(string(.))="Cancel"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('message').send_keys(
            'LEEEEEEROY, JENKINS' + Keys.CONTROL + Keys.ENTER)
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath(u'//div[@class="page-header"]'
                                u'//button[normalize-space(string(.))="Cancelling\u2026"]')
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(job.status, TaskStatus.cancelled)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1346115
    def test_ctrl_enter_submit_posts_once(self):
        with session.begin():
            job = data_setup.create_completed_job()
            # no special permissions required to comment
            user = data_setup.create_user(password=u'theuser')
        comment_text = u'at least i have chicken'
        b = self.browser
        login(b, user=user.user_name, password='theuser')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//td[@class="recipeset-comments"]'
                                '/div/a[@class="comments-link"]').click()
        popover = b.find_element_by_class_name('popover')
        popover.find_element_by_name('comment') \
            .send_keys(comment_text + Keys.CONTROL + Keys.ENTER)
        # check the commit is submitted to comments list, textarea is cleared
        popover.find_element_by_xpath('//div[@class="comments"]'
                                      '//div[@class="comment"]/p[2][text()="%s"]' % comment_text)
        self.assertEqual(popover.find_element_by_name('comment').text, '')
        with session.begin():
            self.assertEqual(len(job.recipesets[0].comments), 1)

    def test_cancel_recipeset(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
            recipeset = job.recipesets[0]
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath('.//button[normalize-space(string(.))="Cancel"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('message').send_keys('lecnac')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        rs_row.find_element_by_xpath(
            u'.//button[normalize-space(string(.))="Cancelling\u2026"]')
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(recipeset.status, TaskStatus.cancelled)

    def test_change_recipeset_priority(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
            recipeset = job.recipesets[0]
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath('.//button[normalize-space(string(.))="Priority"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[normalize-space(string(.))="Low"]').click()
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEquals(recipeset.priority, TaskPriority.low)

    # https://bugzilla.redhat.com/show_bug.cgi?id=980711
    def test_priority_button_visible_on_job_complete(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_completed_job(owner=job_owner)
            recipeset = job.recipesets[0]
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath(
            './/button[normalize-space(string(.))="Priority"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=980711
    def test_on_job_complete_priority_settings_are_disabled_except_current_value(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_completed_job(owner=job_owner)
            recipeset = job.recipesets[0]
        b = self.browser
        login(b, user=job_owner.user_name, password=u'owner')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath(
            './/button[normalize-space(string(.))="Priority"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[normalize-space(string(.))="Normal"]'
                                    '[contains(@disabled, "")]')
        modal.find_element_by_xpath('.//button[normalize-space(string(.))="Low"]'
                                    '[contains(@disabled, "disabled")]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=881387
    def test_guestrecipes_appear_after_host(self):
        with session.begin():
            # hack to force the GuestRecipe to be inserted first
            guest = data_setup.create_recipe(cls=GuestRecipe)
            job = data_setup.create_job_for_recipes([guest])
            session.flush()
            host = data_setup.create_recipe()
            job.recipesets[0].recipes.append(host)
            host.guests.append(guest)
            session.flush()
            self.assert_(guest.id < host.id)
        b = self.browser
        self.go_to_job_page(job)
        recipe_order = [elem.text for elem in b.find_elements_by_xpath(
            '//a[@class="recipe-id"]')]
        self.assertEquals(recipe_order, [host.t_id, guest.t_id])

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_job_activities_view(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
            job.record_activity(user=job_owner, service=u'test',
                                field=u'test', action=u'change',
                                old=u'old', new=u'new')
        login(self.browser, user=job_owner.user_name, password=u'owner')
        b = self.browser
        self.go_to_job_page(job)
        b.find_element_by_link_text('(Job activity)').click()
        modal = b.find_element_by_class_name('modal')
        activity_row = modal.find_element_by_xpath('.//table/tbody/tr[1]')
        activity_row.find_element_by_xpath('./td[2][text()="%s"]' % u'test')
        activity_row.find_element_by_xpath('./td[4][text()="%s"]' % job.t_id)
        activity_row.find_element_by_xpath('./td[6][text()="%s"]' % u'change')

    def test_view_job_which_does_not_have_submitter(self):
        with session.begin():
            job = data_setup.create_job()
            job.submitter = None
        b = self.browser
        login(b)
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]')

    def test_view_job_containing_guest_recipe(self):
        with session.begin():
            job = data_setup.create_running_job(num_guestrecipes=1,
                                                whiteboard=u'contains a guest')
        b = self.browser
        login(b)
        self.go_to_job_page(job)
        b.find_element_by_xpath('//button[normalize-space(string(.))="Edit"]')
        b.find_element_by_xpath(
            '//div[@class="job-whiteboard"]/p[text()="contains a guest"]')
        b.find_element_by_xpath(
            '//a[@class="recipe-id" and normalize-space(string(.))="%s"]'
            % job.recipesets[0].recipes[0].t_id)
        b.find_element_by_xpath(
            '//a[@class="recipe-id" and normalize-space(string(.))="%s"]'
            % job.recipesets[0].recipes[0].guests[0].t_id)

    def test_export_xml(self):
        # Make sure the export link is present on the jobs page. We can't click
        # it because WebDriver can't handle XML documents in the browser.
        # Covered by HTTP API tests below instead.
        with session.begin():
            job = data_setup.create_completed_job()
        b = self.browser
        self.go_to_job_page(job)
        b.find_element_by_link_text('Beaker results XML')

    def test_waive_recipeset(self):
        with session.begin():
            owner = data_setup.create_user(password=u'asdf')
            job = data_setup.create_completed_job(owner=owner)
            recipeset = job.recipesets[0]
        b = self.browser
        login(b, user=owner.user_name, password='asdf')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath('.//button[normalize-space(string(.))="Waive"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('comment').send_keys('fnord')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath('.//span[@class="label label-warning" and text()="Waived"]')
        with session.begin():
            session.refresh(recipeset)
            self.assertEqual(recipeset.waived, True)
            self.assertEqual(recipeset.comments[-1].comment, u'fnord')
            self.assertEqual(recipeset.comments[-1].user, owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1340689
    def test_can_waive_recipeset_after_clicking_the_comments_link(self):
        with session.begin():
            owner = data_setup.create_user(password=u'password')
            job = data_setup.create_completed_job(owner=owner)
            recipeset = job.recipesets[0]
        b = self.browser
        login(b, user=owner.user_name, password='password')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_class_name('comments-link').click()
        rs_row.find_element_by_xpath('.//button[normalize-space(string(.))="Waive"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('comment').send_keys('fnord')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath('.//span[@class="label label-warning" and text()="Waived"]')
        with session.begin():
            session.refresh(recipeset)
            self.assertEqual(recipeset.waived, True)
            self.assertEqual(recipeset.comments[-1].comment, u'fnord')
            self.assertEqual(recipeset.comments[-1].user, owner)

    def test_unwaive_waived_recipeset(self):
        with session.begin():
            owner = data_setup.create_user(password=u'asdf')
            job = data_setup.create_completed_job(owner=owner)
            recipeset = job.recipesets[0]
            recipeset.waived = True
        b = self.browser
        login(b, user=owner.user_name, password='asdf')
        self.go_to_job_page(job)
        rs_row = b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            % recipeset.t_id)
        rs_row.find_element_by_xpath('.//span[@class="label label-warning" and text()="Waived"]')
        rs_row.find_element_by_xpath('.//button[normalize-space(string(.))="Unwaive"]').click()
        # wait for Waive button to re-appear, indicating that unwaiving is complete
        b.find_element_by_xpath(
            '//tr[td/span[@class="recipeset-id" and normalize-space(string(.))="%s"]]'
            '//button[normalize-space(string(.))="Waive"]'
            % recipeset.t_id)
        with session.begin():
            session.refresh(recipeset)
            self.assertEqual(recipeset.waived, False)

    def test_anonymous_can_see_comments(self):
        with session.begin():
            job = data_setup.create_completed_job(num_recipesets=2)
            # comment on first recipe set, no comments on second recipe set
            job.recipesets[0].comments.append(RecipeSetComment(
                comment=u'something', user=data_setup.create_user()))
        b = self.browser
        self.go_to_job_page(job)
        # first recipe set row should have comments link
        comments_link = b.find_element_by_xpath(
            '//tbody[1]/tr[@class="recipeset"]/td[@class="recipeset-comments"]'
            '/div/a[@class="comments-link"]')
        self.assertEqual(comments_link.text, '1')  # it's actually "1 <commenticon>"
        # second recipe set row should have no comments link
        b.find_element_by_xpath(
            '//tbody[2]/tr[@class="recipeset"]/td[@class="recipeset-comments" and '
            'not(./div/a)]')

    def test_authenticated_user_can_comment(self):
        with session.begin():
            job = data_setup.create_completed_job()
            # no special permissions required to comment
            user = data_setup.create_user(password=u'otheruser')
        comment_text = u'comments are fun'
        b = self.browser
        login(b, user=user.user_name, password='otheruser')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//td[@class="recipeset-comments"]'
                                '/div/a[@class="comments-link"]').click()
        popover = b.find_element_by_class_name('popover')
        popover.find_element_by_name('comment').send_keys(comment_text)
        popover.find_element_by_tag_name('form').submit()
        # check if the commit is in the comments list indicating the comment is submitted
        popover.find_element_by_xpath('//div[@class="comments"]//div[@class="comment"]'
                                      '/p[2][text()="%s"]' % comment_text)
        self.assertEqual(popover.find_element_by_name('comment').text, '')
        with session.begin():
            session.expire_all()
            self.assertEqual(job.recipesets[0].comments[0].user, user)
            self.assertEqual(job.recipesets[0].comments[0].comment, comment_text)
        # comments link should indicate the new comment
        comments_link = b.find_element_by_xpath('//td[@class="recipeset-comments"]'
                                                '/div/a[@class="comments-link"]').text
        self.assertEqual(comments_link, '1')

    def test_popup_comment_box_is_closed_when_clicking_outside(self):
        with session.begin():
            job = data_setup.create_completed_job()
            user = data_setup.create_user(password=u'otheruser')
        b = self.browser
        login(b, user=user.user_name, password='otheruser')
        self.go_to_job_page(job)
        b.find_element_by_xpath('//td[@class="recipeset-comments"]'
                                '/div/a[@class="comments-link"]').click()
        # make sure the popover is open
        b.find_element_by_class_name('popover')
        b.find_element_by_xpath('//h1').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "popover")])]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215030
    def test_html_in_comments_is_escaped(self):
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_completed_job(owner=owner)
        bad_comment = "<script>alert('xss')</script>"
        b = self.browser
        login(b, user=owner.user_name, password='owner')
        self.go_to_job_page(job)
        b.find_element_by_xpath('.//button[normalize-space(string(.))="Waive"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('comment').send_keys(bad_comment)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        # showing the comment should not execute a script
        b.find_element_by_class_name('comments-link').click()
        comment_paragraph = b.find_element_by_xpath(
            '//div[@class="comments"]//div[@class="comment"]/p[text()="%s"]'
            % bad_comment)
        # reload the page, showing the comment should not execute a script
        self.go_to_job_page(job)
        b.find_element_by_class_name('comments-link').click()
        comment_paragraph = b.find_element_by_xpath(
            '//div[@class="comments"]//div[@class="comment"]/p[text()="%s"]'
            % bad_comment)

    def test_can_control_recipe_reviewed_state(self):
        with session.begin():
            owner = data_setup.create_user(password=u'asdf')
            job = data_setup.create_completed_job(owner=owner)
            recipe = job.recipesets[0].recipes[0]
            # Recipe is already reviewed
            recipe.set_reviewed_state(owner, True)
        b = self.browser
        login(b, user=owner.user_name, password='asdf')
        self.go_to_job_page(job)
        recipe_row = b.find_element_by_xpath(
            '//tr[td/a[@class="recipe-id" and normalize-space(string(.))="%s"]]'
            % recipe.t_id)
        reviewed_checkbox = recipe_row.find_element_by_xpath(
            './/input[@type="checkbox" and @title="Reviewed?"]')
        # Checkbox should be checked because the recipe is already reviewed
        self.assertTrue(reviewed_checkbox.is_selected())
        # Un-check it
        reviewed_checkbox.click()
        # The reviewed checkbox violates our UI guidelines about always
        # indicating when a server request is in progress. But there is really
        # nowhere good we can display a progress indicator because the reviewed
        # checkbox is intentionally very unobtrusive.
        # So we have to resort to poll-waiting on the database instead.
        wait_for_condition(lambda: recipe.get_reviewed_state(owner) == False)

    def test_anonymous_cannot_control_recipe_reviewed_state(self):
        with session.begin():
            job = data_setup.create_completed_job()
            recipe = job.recipesets[0].recipes[0]
        b = self.browser
        self.go_to_job_page(job)
        recipe_row = b.find_element_by_xpath(
            '//tr[td/a[@class="recipe-id" and normalize-space(string(.))="%s"]]'
            % recipe.t_id)
        reviewed_checkbox = recipe_row.find_element_by_xpath(
            './/input[@type="checkbox" and @title="Reviewed?"]')
        # Checkbox should not be enabled/checked because user is not logged in
        self.assertFalse(reviewed_checkbox.is_selected())
        self.assertFalse(reviewed_checkbox.is_enabled())

    # https://bugzilla.redhat.com/show_bug.cgi?id=894137
    def test_recipeset_in_url_anchor_is_highlighted(self):
        # When the URL is /jobs/123#set456, RS:456 should be focused and highlighted.
        with session.begin():
            job = data_setup.create_completed_job()
            recipeset = job.recipesets[0]
        b = self.browser
        self.go_to_job_page(job, recipeset=recipeset)
        b.find_element_by_xpath('//tbody[@id="set%s" and @class="highlight"]' % recipeset.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=894137
    def test_old_recipeset_anchors_are_replaced(self):
        with session.begin():
            job = data_setup.create_completed_job()
            recipeset = job.recipesets[0]
        b = self.browser
        b.get(get_server_base() + 'jobs/%s#RS_%s' % (job.id, recipeset.id))
        b.find_element_by_xpath('//tbody[@id="set%s" and @class="highlight"]' % recipeset.id)
        self.assertEquals(b.current_url,
                          get_server_base() + 'jobs/%s#set%s' % (job.id, recipeset.id))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1334552
    def test_recipe_whiteboard_appears_as_markdown(self):
        with session.begin():
            whiteboard = u'[google](http://www.google.com) is a *really* cool site!\n\nDont you agree?'
            job = data_setup.create_job(recipe_whiteboard=whiteboard)
            self.assertEqual(job.recipesets[0].recipes[0].whiteboard, whiteboard)
        b = self.browser
        login(b)
        self.go_to_job_page(job)
        expected_html = u'<a href="http://www.google.com">google</a> is a <em>really</em> cool site!'
        recipe_row = b.find_element_by_xpath("//td/span[@class='recipe-whiteboard']")
        self.assertEquals(expected_html, recipe_row.get_attribute('innerHTML'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1334552
    def test_weird_recipe_whiteboard_content_should_not_be_shown(self):
        with session.begin():
            whiteboard = u'* foo\r * bar\r * none\r'
            job = data_setup.create_job(recipe_whiteboard=whiteboard)
            self.assertEqual(job.recipesets[0].recipes[0].whiteboard, whiteboard)
        b = self.browser
        login(b)
        self.go_to_job_page(job)
        recipe_row = b.find_element_by_xpath("//td/span[@class='recipe-whiteboard']")
        self.assertEquals(recipe_row.get_attribute('innerHTML'), u'')


class NewJobTestWD(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
            data_setup.create_product(product_name=u'the_product')

    # https://bugzilla.redhat.com/show_bug.cgi?id=949777
    def test_invalid_inventory_date_with_equal(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with invalid date value with equal op</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires>
                           <system>
                              <last_inventoried op="=" value="2010-10-10 10:10:10"/>
                           </system>
                           <system_type value="Machine"/>
                        </hostRequires>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        b.find_element_by_xpath("//button[text()='Queue']").click()
        b.find_element_by_xpath('//div[contains(@class, "alert")]'
                                '/h4[contains(text(), "Job failed schema validation")]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=949777
    def test_invalid_inventory_date_with_not_equal(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with invalid date value with equal op</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires>
                           <system>
                              <last_inventoried op="!=" value="2010-10-10 10:10:10"/>
                           </system>
                           <system_type value="Machine"/>
                        </hostRequires>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        b.find_element_by_xpath("//button[text()='Queue']").click()
        b.find_element_by_xpath('//div[contains(@class, "alert")]'
                                '/h4[contains(text(), "Job failed schema validation")]')

    def test_valid_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user()
            submission_delegate = data_setup.create_user(password='password')
            user.submission_delegates[:] = [submission_delegate]

        b = self.browser
        login(b, user=submission_delegate.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job user="%s">
                <whiteboard>job with submission delegate who is allowed</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires>
                           <system_type value="Machine"/>
                        </hostRequires>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''' % user.user_name)
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        b.find_element_by_xpath("//button[text()='Queue']").click()
        flash_text = b.find_element_by_class_name('flash').text
        self.assert_('Success!' in flash_text, flash_text)
        self.assertEqual(b.title, 'My Jobs')

    def test_invalid_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user()
            invalid_delegate = data_setup.create_user(password='password')

        b = self.browser
        login(b, user=invalid_delegate.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job user="%s">
                <whiteboard>job with submission delegate who is not allowed</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires>
                           <system>
                              <last_inventoried op="&gt;" value="2010-10-10"/>
                           </system>
                           <system_type value="Machine"/>
                        </hostRequires>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''' % user.user_name)
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        b.find_element_by_xpath("//button[text()='Queue']").click()
        flash_text = b.find_element_by_class_name('flash').text
        self.assertEquals('Failed to import job because of: %s is not a valid'
                          ' submission delegate for %s' % (
                          invalid_delegate.user_name, user.user_name), flash_text, flash_text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=949777
    def test_valid_inventory_date(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with invalid date value with equal op</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires>
                           <system>
                              <last_inventoried op="&gt;" value="2010-10-10"/>
                           </system>
                           <system_type value="Machine"/>
                        </hostRequires>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        b.find_element_by_xpath("//button[text()='Queue']").click()
        flash_text = b.find_element_by_class_name('flash').text
        self.assert_('Success!' in flash_text, flash_text)
        self.assertEqual(b.title, 'My Jobs')

    # https://bugzilla.redhat.com/show_bug.cgi?id=972412
    def test_invalid_utf8_chars(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('\x89')
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        flash_text = b.find_element_by_class_name('flash').text
        self.assertEquals(flash_text,
                          "Invalid job XML: 'utf8' codec can't decode byte 0x89 "
                          "in position 0: invalid start byte")

    # https://bugzilla.redhat.com/show_bug.cgi?id=883887
    def test_duplicate_packages_are_merged(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'jobs/new')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with duplicate packages</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <packages>
                            <package name="system-config-kdump"/>
                            <package name="system-config-kdump"/>
                        </packages>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_xpath("//input[@id='jobs_filexml']").send_keys(xml_file.name)
        b.find_element_by_xpath("//button[text()='Submit Data']").click()
        b.find_element_by_xpath("//button[text()='Queue']").click()
        flash_text = b.find_element_by_class_name('flash').text
        self.assert_('Success!' in flash_text, flash_text)
        self.assertEqual(b.title, 'My Jobs')


class NewJobTest(WebDriverTestCase):
    maxDiff = None

    @with_transaction
    def setUp(self):
        data_setup.create_product(product_name=u'the_product')
        self.browser = self.get_browser()

    def test_warns_about_xsd_validation_errors(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with invalid hostRequires</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" role="STANDALONE">
                            <params/>
                        </task>
                        <brokenElement/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        self.assertEqual(b.find_element_by_css_selector('.alert-error h4').text,
                         'Job failed schema validation. Please confirm that you want to submit it.')
        b.find_element_by_xpath('//ul[@class="xsd-error-list"]/li')
        b.find_element_by_xpath('//button[text()="Queue despite validation errors"]').click()
        b.find_element_by_xpath('//title[text()="My Jobs"]')
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    def test_refuses_to_accept_unparseable_xml(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with unterminated whiteboard
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assertIn('Failed to import job', flash_message)

    def test_valid_job_xml_doesnt_trigger_xsd_warning(self):
        with session.begin():
            group = data_setup.create_group(group_name=u'somegroup')
            user = data_setup.create_user(password=u'hornet')
            group.add_member(user)

        b = self.browser
        login(b, user=user.user_name, password='hornet')
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        b.find_element_by_id('jobs_filexml').send_keys(
            pkg_resources.resource_filename('bkr.inttest', 'complete-job.xml'))
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=661652
    def test_job_with_excluded_task(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(arch=u'ia64')
            excluded_task = data_setup.create_task(exclude_arches=[u'ia64'])
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with excluded task</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="%s" />
                            <distro_arch op="=" value="ia64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" role="STANDALONE">
                            <params/>
                        </task>
                        <task name="%s" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            ''' % (distro_tree.distro.name, excluded_task.name))
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=689344
    def test_partition_without_fs_doesnt_trigger_validation_warning(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with partition without fs</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition name="/" size="4" type="part"/>
                        </partitions>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=730983
    def test_duplicate_notify_cc_addresses_are_merged(self):
        with session.begin():
            user = data_setup.create_user(password=u'hornet')
        b = self.browser
        login(b, user.user_name, u'hornet')
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with duplicate notify cc addresses</whiteboard>
                <notify>
                    <cc>person@example.invalid</cc>
                    <cc>person@example.invalid</cc>
                </notify>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)
        with session.begin():
            job = Job.query.filter(Job.owner == user).order_by(Job.id.desc()).first()
            self.assertEqual(job.cc, ['person@example.invalid'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=784237
    def test_invalid_email_addresses_are_not_accepted_in_notify_cc(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with invalid notify cc addresses</whiteboard>
                <notify>
                    <cc>asdf</cc>
                </notify>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assertIn('Failed to import job', flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=741170
    # You will need a patched python-xmltramp for this test to pass.
    # Look for python-xmltramp-2.17-8.eso.1 or higher.
    def test_doesnt_barf_on_xmlns(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with namespace prefix declaration</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires xmlns:str="http://exslt.org/strings">
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1112131
    def test_preserves_arbitrary_xml_just_fine(self):
        arbitrary_xml = """
        <p:option xmlns:p="http://example.com/preserve">
          <closed/>
          <cdata attribute="bogus"><![CDATA[<sender>John Smith</sender>]]></cdata>
          <text>just text</text>
          <!-- comment -->
        </p:option>
        """

        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                %s
                <whiteboard>job with arbitrary XML in namespaces</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''' % arbitrary_xml)
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

        with session.begin():
            job = Job.query.all()[-1]
            self.assertMultiLineEqual(arbitrary_xml.strip(), job.extra_xml.strip())

    # https://bugzilla.redhat.com/show_bug.cgi?id=768167
    def test_doesnt_barf_on_xml_encoding_declaration(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''<?xml version="1.0" encoding="utf-8"?>
            <job>
                <whiteboard>job with encoding in XML declaration яяя</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=869455
    # https://bugzilla.redhat.com/show_bug.cgi?id=896622
    def test_recipe_not_added_to_session_too_early(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        # These bugs are triggered by related entites of Recipe (ks_appends,
        # repos, and packages) pulling the recipe into the session too early.
        # So our test job XML has one of each on the recipe and its
        # guestrecipe, to cover all cases.
        xml_file.write('''<?xml version="1.0" encoding="utf-8"?>
            <job>
                <whiteboard>job with package</whiteboard>
                <recipeSet>
                    <recipe>
                        <guestrecipe guestargs="--kvm" guestname="one">
                            <ks_appends>
                                <ks_append>append1</ks_append>
                            </ks_appends>
                            <packages>
                                <package name="package1" />
                            </packages>
                            <repos>
                                <repo name="repo1" url="http://example.com/" />
                            </repos>
                            <distroRequires>
                                <distro_name op="=" value="BlueShoeLinux5-5" />
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/check-install" />
                        </guestrecipe>
                        <ks_appends>
                            <ks_append>append2</ks_append>
                        </ks_appends>
                        <packages>
                            <package name="package2" />
                        </packages>
                        <repos>
                            <repo name="repo2" url="http://example.com/" />
                        </repos>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        flash_message = b.find_element_by_class_name('flash').text
        self.assert_(flash_message.startswith('Success!'), flash_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1171936
    def test_useful_error_message_on_ksmeta_syntax_error(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with ksmeta syntax error</whiteboard>
                <recipeSet>
                    <recipe ks_meta="'">
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          'Failed to import job because of: '
                          'Error parsing ks_meta: No closing quotation')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215020
    def test_xml_external_entities_are_rejected(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Scheduler', 'New Job')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <!DOCTYPE foo [
            <!ELEMENT foo ANY >
            <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
            <job>
                <whiteboard>&xxe;</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        b.find_element_by_id('jobs_filexml').send_keys(xml_file.name)
        b.find_element_by_xpath('//button[text()="Submit Data"]').click()
        b.find_element_by_xpath('//button[text()="Queue"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          'Failed to import job because of: '
                          'XML entity with name &xxe; not permitted')


class CloneJobTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_cloning_recipeset_from_job_with_product(self):
        with session.begin():
            job = data_setup.create_job()
            job.retention_tag = RetentionTag.list_by_requires_product()[0]
            job.product = Product(u'product_name')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'jobs/clone?job_id=%s' % job.id)
        cloned_from_job = b.find_element_by_xpath('//textarea[@name="textxml"]').text
        b.get(get_server_base() + 'jobs/clone?recipeset_id=%s' % job.recipesets[0].id)
        cloned_from_rs = b.find_element_by_xpath('//textarea[@name="textxml"]').text
        self.assertEqual(cloned_from_job, cloned_from_rs)

    def test_cloning_recipeset(self):
        with session.begin():
            job = data_setup.create_job()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'jobs/clone?job_id=%s' % job.id)
        cloned_from_job = b.find_element_by_xpath('//textarea[@name="textxml"]').text
        b.get(get_server_base() + 'jobs/clone?recipeset_id=%s' % job.recipesets[0].id)
        cloned_from_rs = b.find_element_by_xpath('//textarea[@name="textxml"]').text
        self.assertEqual(cloned_from_job, cloned_from_rs)


class TestJobsGrid(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def check_job_row(self, rownum, job_t_id, group):
        b = self.browser
        job_id = b.find_element_by_xpath('//table[@id="widget"]/tbody/tr[%d]/td[1]' % rownum).text
        group_name = b.find_element_by_xpath(
            '//table[@id="widget"]/tbody/tr[%d]/td[3]' % rownum).text
        self.assertEquals(job_id, job_t_id)
        if group:
            self.assertEquals(group_name, group.group_name)
        else:
            self.assertEquals(group_name, "")

    def test_myjobs_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            user2 = data_setup.create_user(password='password')
            group = data_setup.create_group()
            group.add_member(user)
            group.add_member(user2)
            job = data_setup.create_job(owner=user, group=group)
        b = self.browser
        login(b, user=user2.user_name, password='password')
        b.get(get_server_base() + 'jobs/mygroups')
        b.find_element_by_xpath('//title[normalize-space(text())="My Group Jobs"]')
        self.assertTrue(is_text_present(b, job.t_id))
        logout(b)
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'jobs/mygroups')
        b.find_element_by_xpath('//title[normalize-space(text())="My Group Jobs"]')
        self.assertTrue(is_text_present(b, job.t_id))

    def test_myjobs_individual(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            job = data_setup.create_job(owner=user, group=None)
        b = self.browser
        login(b, user=user.user_name, password='password')
        b.find_element_by_link_text('My Jobs').click()
        b.find_element_by_xpath('//title[normalize-space(text())="My Jobs"]')
        self.assertTrue(is_text_present(b, job.t_id))

    def test_myjobs_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user()
            submission_delegate = data_setup.create_user(password='password')
            user.submission_delegates[:] = [submission_delegate]
            job = data_setup.create_job(owner=user, group=None, submitter=submission_delegate)
        b = self.browser
        login(b, user=submission_delegate.user_name, password='password')
        b.find_element_by_link_text('My Jobs').click()
        b.find_element_by_xpath('//title[normalize-space(text())="My Jobs"]')
        self.assertTrue(is_text_present(b, job.t_id))

    def test_jobs_group_column(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group1 = data_setup.create_group(owner=user)
            group2 = data_setup.create_group()
            group2.add_member(user)
            job1 = data_setup.create_job(owner=user, group=None)
            job2 = data_setup.create_job(owner=user, group=group1)
            job3 = data_setup.create_job(owner=user, group=group2)

        b = self.browser

        # jobs/mine
        login(b, user=user.user_name, password='password')
        b.find_element_by_link_text('My Jobs').click()
        b.find_element_by_xpath('//title[normalize-space(text())="My Jobs"]')

        self.check_job_row(rownum=1, job_t_id=job3.t_id, group=group2)
        self.check_job_row(rownum=2, job_t_id=job2.t_id, group=group1)
        self.check_job_row(rownum=3, job_t_id=job1.t_id, group=None)

        # jobs
        logout(b)
        b.get(get_server_base() + 'jobs/')
        self.check_job_row(rownum=1, job_t_id=job3.t_id, group=group2)
        self.check_job_row(rownum=2, job_t_id=job2.t_id, group=group1)
        self.check_job_row(rownum=3, job_t_id=job1.t_id, group=None)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1420106
    def test_renders_whiteboard_as_markdown(self):
        with session.begin():
            job = data_setup.create_job(whiteboard=u'hello & *here* is '
                                                   '[a link](http://example.com/) lol\n\n'
                                                   'with a separate paragraph that is ignored')
        b = self.browser
        b.get(get_server_base() + 'jobs/')
        whiteboard_cell = b.find_element_by_xpath('//table[@id="widget"]/tbody/tr[1]/td[2]')
        self.assertEquals(whiteboard_cell.text, 'hello & here is a link lol')
        self.assertEquals(whiteboard_cell.find_element_by_xpath('./em').text, 'here')
        self.assertEquals(
            whiteboard_cell.find_element_by_xpath('./a').get_attribute('href'),
            'http://example.com/')


class SystemUpdateInventoryHTTPTest(WebDriverTestCase):
    """
    Directly tests the HTTP interface for updating system inventory
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.lc = data_setup.create_labcontroller()
            self.system1 = data_setup.create_system(owner=self.owner,
                                                    arch=[u'i386', u'x86_64'])
            self.system1.lab_controller = self.lc
            self.distro_tree1 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])

    def test_submit_inventory_job(self):
        s = requests.Session()
        response = s.post(get_server_base() + 'jobs/+inventory')
        self.assertEquals(response.status_code, 401)
        s.post(get_server_base() + 'login',
               data={'user_name': self.owner.user_name,
                     'password': 'theowner'}).raise_for_status()
        response = post_json(get_server_base() + 'jobs/+inventory',
                             session=s,
                             data={'fqdn': self.system1.fqdn})
        response.raise_for_status()
        self.assertIn('recipe_id', response.text)

        # Non-existent system
        response = post_json(get_server_base() + 'jobs/+inventory',
                             session=s,
                             data={'fqdn': 'i.donotexist.name'})
        self.assertEquals(response.status_code, 400)
        self.assertIn('System not found: i.donotexist.name', response.text)


class JobHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by the job page.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.job = data_setup.create_job(owner=self.owner,
                                             retention_tag=u'scratch')

    def test_get_job(self):
        response = requests.get(get_server_base() + 'jobs/%s' % self.job.id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['id'], self.job.id)
        self.assertEquals(json['owner']['user_name'], self.owner.user_name)

    def test_get_job_which_does_not_have_submitter(self):
        # A job may not have a submitter prior to Beaker 14.
        # In this case, it should return the owner as the submitter.
        with session.begin():
            job = data_setup.create_job(owner=self.owner)
            job.submitter = None
        response = requests.get(get_server_base() + 'jobs/%s' % job.id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['id'], job.id)
        self.assertEquals(json['submitter']['user_name'], self.owner.user_name)

    def test_get_job_xml(self):
        response = requests.get(get_server_base() + 'jobs/%s.xml' % self.job.id)
        response.raise_for_status()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(
            lxml.etree.tostring(self.job.to_xml(), pretty_print=True, encoding='utf8'),
            response.content)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319#c6
    def test_get_job_xml_without_logs(self):
        response = requests.get(get_server_base() + 'jobs/%s.xml?include_logs=false' % self.job.id)
        response.raise_for_status()
        self.assertNotIn('<log', response.content)

    def test_get_junit_xml(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        response = requests.get(get_server_base() + 'jobs/%s.junit.xml' % self.job.id)
        response.raise_for_status()
        self.assertEquals(response.status_code, 200)
        junitxml = lxml.etree.fromstring(response.content)
        self.assertEqual(junitxml.tag, 'testsuites')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1169838
    def test_trailing_slash_should_return_404(self):
        response = requests.get(get_server_base() + 'jobs/%s/' % self.job.id)
        self.assertEqual(response.status_code, 404)

    def test_set_job_whiteboard(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'jobs/%s' % self.job.id,
                              session=s, data={'whiteboard': 'newwhiteboard'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.whiteboard, 'newwhiteboard')
            self.assertEquals(self.job.activity[0].field_name, u'Whiteboard')
            self.assertEquals(self.job.activity[0].action, u'Changed')
            self.assertEquals(self.job.activity[0].new_value, u'newwhiteboard')

    def test_set_retention_tag_and_product(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=True)
            product = data_setup.create_product()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': product.name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.retention_tag, retention_tag)
            self.assertEquals(self.job.product, product)
            self.assertEquals(self.job.activity[0].field_name, u'Product')
            self.assertEquals(self.job.activity[0].action, u'Changed')
            self.assertEquals(self.job.activity[0].old_value, None)
            self.assertEquals(self.job.activity[0].new_value, product.name)
            self.assertEquals(self.job.activity[1].field_name, u'Retention Tag')
            self.assertEquals(self.job.activity[1].action, u'Changed')
            self.assertEquals(self.job.activity[1].old_value, u'scratch')
            self.assertEquals(self.job.activity[1].new_value, retention_tag.tag)

    def test_cannot_set_product_if_retention_tag_does_not_need_one(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=False)
            product = data_setup.create_product()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': product.name})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            'Cannot change retention tag as it does not support a product',
            response.text)
        # Same thing, but the retention tag is already set and we are just setting the product.
        with session.begin():
            self.job.retention_tag = retention_tag
        response = patch_json(get_server_base() + 'jobs/%s' % self.job.id,
                              session=s, data={'product': product.name})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            'Cannot change product as the current retention tag does not support a product',
            response.text)

    def test_set_retention_tag_without_product(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=False)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.retention_tag, retention_tag)
            self.assertEquals(self.job.product, None)
            self.assertEquals(self.job.activity[0].field_name, u'Retention Tag')
            self.assertEquals(self.job.activity[0].action, u'Changed')
            self.assertEquals(self.job.activity[0].old_value, u'scratch')
            self.assertEquals(self.job.activity[0].new_value, retention_tag.tag)
        # Same thing, but with {product: null} which is equivalent.
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': None})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.retention_tag, retention_tag)
            self.assertEquals(self.job.product, None)

    def test_set_retention_tag_clearing_product(self):
        # The difference here compared with the test case above is that in this
        # case, the job already has a retention tag and a product set, we are
        # changing it to a different retention tag which requires the product
        # to be cleared.
        with session.begin():
            old_retention_tag = data_setup.create_retention_tag(needs_product=True)
            self.job.retention_tag = old_retention_tag
            self.job.product = data_setup.create_product()
            retention_tag = data_setup.create_retention_tag(needs_product=False)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': None})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.retention_tag, retention_tag)
            self.assertEquals(self.job.product, None)
            self.assertEquals(self.job.activity[0].field_name, u'Product')
            self.assertEquals(self.job.activity[0].action, u'Changed')
            self.assertEquals(self.job.activity[0].new_value, None)
            self.assertEquals(self.job.activity[1].field_name, u'Retention Tag')
            self.assertEquals(self.job.activity[1].action, u'Changed')
            self.assertEquals(self.job.activity[1].old_value, old_retention_tag.tag)
            self.assertEquals(self.job.activity[1].new_value, retention_tag.tag)

    def test_cannot_set_retention_tag_without_product_if_tag_needs_one(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=True)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            'Cannot change retention tag as it requires a product',
            response.text)
        # Same thing, but with {product: null} which is equivalent.
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': None})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            'Cannot change retention tag as it requires a product',
            response.text)

    def test_set_product(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=True)
            product = data_setup.create_product()
            self.job.retention_tag = retention_tag
            self.job.product = product
            other_product = data_setup.create_product()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'product': other_product.name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.product, other_product)
            self.assertEquals(self.job.activity[0].field_name, u'Product')
            self.assertEquals(self.job.activity[0].action, u'Changed')
            self.assertEquals(self.job.activity[0].old_value, product.name)
            self.assertEquals(self.job.activity[0].new_value, other_product.name)

    def test_set_cc(self):
        with session.begin():
            self.job.cc = [u'capn-crunch@example.com']
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'cc': ['captain-planet@example.com']})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.job.cc, ['captain-planet@example.com'])
            self.assertEquals(self.job.activity[0].field_name, u'Cc')
            self.assertEquals(self.job.activity[0].action, u'Removed')
            self.assertEquals(self.job.activity[0].old_value, u'capn-crunch@example.com')
            self.assertEquals(self.job.activity[1].field_name, u'Cc')
            self.assertEquals(self.job.activity[1].action, u'Added')
            self.assertEquals(self.job.activity[1].new_value, u'captain-planet@example.com')

    def test_invalid_email_address_in_cc_is_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'jobs/%s' % self.job.id,
                              session=s, data={'cc': ['bork;one1']})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            "Invalid email address u'bork;one1' in cc: "
            "An email address must contain a single @",
            response.text)

    def test_other_users_cannot_delete_job(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        self.assertEquals(response.status_code, 403)
        self.assertEquals('Insufficient permissions: Cannot delete job', response.text)

    def test_delete_job(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.job.is_deleted)

    def test_cannot_delete_running_job(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        self.assertEquals(response.status_code, 400)
        self.assertEquals('Cannot delete running job', response.text)

    def test_cannot_delete_already_deleted_job(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
            self.job.deleted = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        self.assertEquals(response.status_code, 409)
        self.assertEquals('Job has already been deleted', response.text)

    def test_anonymous_cannot_update_status(self):
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             data={'status': u'Cancelled'})
        self.assertEquals(response.status_code, 401)

    def test_other_users_cannot_update_status(self):
        with session.begin():
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEquals(response.status_code, 403)

    def test_submission_delegate_cannot_update_status(self):
        # N.B. submission delegate but *not* submitter
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEquals(response.status_code, 403)

    def test_cancel_job(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.job.update_status()
            self.assertEquals(self.job.status, TaskStatus.cancelled)
            # https://bugzilla.redhat.com/show_bug.cgi?id=995012
            self.assertEquals(self.job.activity[0].field_name, u'Status')
            self.assertEquals(self.job.activity[0].action, u'Cancelled')

    def test_submitter_can_cancel(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
            self.job.submitter = submission_delegate
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    def test_group_member_can_cancel_group_job(self):
        with session.begin():
            other_member = data_setup.create_user(password='other')
            group = data_setup.create_group()
            group.add_member(self.job.owner)
            group.add_member(other_member)
            self.job.group = group
        s = requests.Session()
        requests_login(s, user=other_member, password=u'other')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173376
    def test_clear_rows_in_system_recipe_map(self):
        with session.begin():
            system = data_setup.create_system()
            self.job.recipesets[0].recipes[0].systems[:] = [system]
        # check if rows in system_recipe_map
        self.assertNotEqual(len(self.job.recipesets[0].recipes[0].systems), 0)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.job.recipesets[0].recipes[0].systems), 0)

    def test_get_job_activity(self):
        with session.begin():
            self.job.record_activity(user=self.job.owner, service=u'testdata',
                                     field=u'green', action=u'blorp', new=u'something')
        response = requests.get(get_server_base() +
                                'jobs/%s/activity/' % self.job.id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(len(json['entries']), 1, json['entries'])
        self.assertEquals(json['entries'][0]['user']['user_name'],
                          self.job.owner.user_name)
        self.assertEquals(json['entries'][0]['field_name'], u'green')
        self.assertEquals(json['entries'][0]['action'], u'blorp')
        self.assertEquals(json['entries'][0]['new_value'], u'something')


class RecipeSetHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipe sets used by the job page.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.job = data_setup.create_job(owner=self.owner,
                                             retention_tag=u'scratch', priority=TaskPriority.normal)

    def test_get_recipeset(self):
        response = requests.get(get_server_base() +
                                'recipesets/%s' % self.job.recipesets[0].id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['t_id'], self.job.recipesets[0].t_id)

    def test_anonymous_cannot_change_recipeset(self):
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              data={'priority': u'Low'})
        self.assertEquals(response.status_code, 401)

    def test_other_users_cannot_change_recipeset(self):
        with session.begin():
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Low'})
        self.assertEquals(response.status_code, 403)

    def test_job_owner_can_reduce_priority(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Low'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            recipeset = self.job.recipesets[0]
            self.assertEquals(recipeset.priority, TaskPriority.low)
            self.assertEquals(recipeset.activity[0].field_name, u'Priority')
            self.assertEquals(recipeset.activity[0].action, u'Changed')
            self.assertEquals(recipeset.activity[0].new_value, u'Low')

    def test_job_owner_cannot_increase_priority(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Urgent'})
        self.assertEquals(response.status_code, 403)

    def check_changed_recipeset(self):
        recipeset = self.job.recipesets[0]
        self.assertEquals(recipeset.priority, TaskPriority.urgent)
        self.assertEquals(recipeset.activity[0].user.user_name,
                          data_setup.ADMIN_USER)
        self.assertEquals(recipeset.activity[0].field_name, u'Priority')
        self.assertEquals(recipeset.activity[0].action, u'Changed')
        self.assertEquals(recipeset.activity[0].new_value, u'Urgent')

    def test_admin_can_increase_priority(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Urgent'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.check_changed_recipeset()

    def test_job_owner_can_waive(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'waived': True})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            recipeset = self.job.recipesets[0]
            self.assertEqual(recipeset.waived, True)
            # https://bugzilla.redhat.com/show_bug.cgi?id=995012
            self.assertEqual(recipeset.activity[0].field_name, u'Waived')
            self.assertEqual(recipeset.activity[0].action, u'Changed')
            self.assertEqual(recipeset.activity[0].old_value, u'False')
            self.assertEqual(recipeset.activity[0].new_value, u'True')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1149977
    def test_admin_can_increase_priority_by_tid(self):
        s = requests.Session()
        requests_login(s)
        # by recipe set t_id
        response = patch_json(get_server_base() +
                              'recipesets/by-taskspec/%s' % self.job.recipesets[0].t_id,
                              session=s, data={'priority': u'Urgent'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.check_changed_recipeset()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1149977
    def test_admin_can_increase_priority_by_job_tid(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'recipesets/by-taskspec/%s' % self.job.t_id,
                              session=s, data={'priority': u'Urgent'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.check_changed_recipeset()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497021
    def test_group_member_can_reduce_group_job_priority_by_tid(self):
        with session.begin():
            group = data_setup.create_group()
            group_member = data_setup.create_user(password=u'member')
            group.add_member(group_member)
            self.job.group = group
        s = requests.Session()
        requests_login(s, user=group_member, password=u'member')
        response = patch_json(get_server_base() +
                              'recipesets/by-taskspec/%s' % self.job.t_id,
                              session=s, data={'priority': u'Low'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            recipeset = self.job.recipesets[0]
            self.assertEquals(recipeset.priority, TaskPriority.low)

    def test_update_containing_no_changes_should_silently_do_nothing(self):
        # PATCH request containing attributes with their existing values
        # should succeed and do nothing, including adding no activity records.
        with session.begin():
            recipeset = self.job.recipesets[0]
            recipeset.priority = TaskPriority.normal
            recipeset.waived = False
            self.assertEqual(recipeset.activity, [])
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'recipesets/%s' % recipeset.id,
                              session=s, data={'priority': u'Normal', 'waived': False})
        self.assertEqual(response.status_code, 200)
        with session.begin():
            session.expire_all()
            self.assertEqual(recipeset.priority, TaskPriority.normal)
            self.assertEqual(recipeset.waived, False)
            self.assertEqual(recipeset.activity, [])

    def test_anonymous_cannot_update_status(self):
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             data={'status': u'Cancelled'})
        self.assertEquals(response.status_code, 401)

    def test_other_users_cannot_update_status(self):
        with session.begin():
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEquals(response.status_code, 403)

    def test_submission_delegate_cannot_update_status(self):
        # N.B. submission delegate but *not* submitter
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEquals(response.status_code, 403)

    def test_cancel_recipeset(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.job.update_status()
            recipeset = self.job.recipesets[0]
            self.assertEquals(recipeset.status, TaskStatus.cancelled)
            # https://bugzilla.redhat.com/show_bug.cgi?id=995012
            self.assertEquals(recipeset.activity[0].field_name, u'Status')
            self.assertEquals(recipeset.activity[0].action, u'Cancelled')

    def test_submitter_can_cancel(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
            self.job.submitter = submission_delegate
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    def test_group_member_can_cancel_in_group_job(self):
        with session.begin():
            other_member = data_setup.create_user(password='other')
            group = data_setup.create_group()
            group.add_member(self.job.owner)
            group.add_member(other_member)
            self.job.group = group
        s = requests.Session()
        requests_login(s, user=other_member, password=u'other')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    def test_get_recipeset_comments(self):
        with session.begin():
            commenter = data_setup.create_user(user_name=u'jim')
            self.job.recipesets[0].comments.append(RecipeSetComment(
                user=commenter,
                created=datetime.datetime(2015, 11, 5, 17, 0, 55),
                comment=u'Microsoft and Red Hat to deliver new standard for '
                        u'enterprise cloud experiences'))
        response = requests.get(get_server_base() +
                                'recipesets/%s/comments/' % self.job.recipesets[0].id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(len(json['entries']), 1)
        self.assertEqual(json['entries'][0]['user']['user_name'], u'jim')
        self.assertEqual(json['entries'][0]['created'], u'2015-11-05 17:00:55')
        self.assertIn(u'Microsoft', json['entries'][0]['comment'])

    def test_post_recipeset_comment(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                             'recipesets/%s/comments/' % self.job.recipesets[0].id,
                             session=s, data={'comment': 'we unite on common solutions'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.job.recipesets[0].comments), 1)
            self.assertEqual(self.job.recipesets[0].comments[0].user, self.owner)
            self.assertEqual(self.job.recipesets[0].comments[0].comment,
                             u'we unite on common solutions')
            self.assertEqual(response.json()['id'],
                             self.job.recipesets[0].comments[0].id)

    def test_empty_comment_is_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                             'recipesets/%s/comments/' % self.job.recipesets[0].id,
                             session=s, data={'comment': None})
        self.assertEqual(response.status_code, 400)
        # whitespace-only comment also counts as empty
        response = post_json(get_server_base() +
                             'recipesets/%s/comments/' % self.job.recipesets[0].id,
                             session=s, data={'comment': ' '})
        self.assertEqual(response.status_code, 400)
