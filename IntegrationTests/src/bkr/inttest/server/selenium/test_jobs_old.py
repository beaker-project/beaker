# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import re
from turbogears.database import session
from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from bkr.server.model import GuestRecipe


# OLD, DEPRECATED JOB PAGE ONLY

class TestViewJob(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_group_job(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            user.use_old_job_page = True
            group = data_setup.create_group()
            job = data_setup.create_job(group=group)
        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        b.find_element_by_link_text("%s" % job.group).click()
        b.find_element_by_xpath('.//h1[normalize-space(text())="%s"]' % \
                                group.group_name)

    def test_cc_list(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            user.use_old_job_page = True
            job = data_setup.create_job(owner=user,
                                        cc=[u'laika@mir.su', u'tereshkova@kosmonavt.su'])
        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base())
        b.find_element_by_link_text('My Jobs').click()
        b.find_element_by_link_text(job.t_id).click()
        b.find_element_by_xpath('//td[.//text()="%s"]' % job.t_id)
        self.assertEqual(
            # value of cell beside "CC" cell
            b.find_element_by_xpath('//table//td'
                                    '[preceding-sibling::th[1]/text() = "CC"]').text,
            'laika@mir.su; tereshkova@kosmonavt.su')

    def test_edit_job_whiteboard(self):
        with session.begin():
            user = data_setup.create_user(password=u'asdf')
            user.use_old_job_page = True
            job = data_setup.create_job(owner=user)
        b = self.browser
        login(b, user=user.user_name, password='asdf')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        new_whiteboard = 'new whiteboard value %s' % int(time.time())
        b.find_element_by_xpath(
            '//td[preceding-sibling::th[1]/text()="Whiteboard"]'
            '//a[text()="(Edit)"]').click()
        b.find_element_by_name('whiteboard').clear()
        b.find_element_by_name('whiteboard').send_keys(new_whiteboard)
        b.find_element_by_xpath('//form[@id="job_whiteboard_form"]'
                                '//button[@type="submit"]').click()
        b.find_element_by_xpath(
            '//form[@id="job_whiteboard_form"]//div[@class="msg success"]')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        b.find_element_by_xpath('//input[@name="whiteboard" and @value="%s"]'
                                % new_whiteboard)

    def test_datetimes_are_localised(self):
        with session.begin():
            user = data_setup.create_user(password=u'asdf')
            user.use_old_job_page = True
            job = data_setup.create_completed_job()
        b = self.browser
        login(b, user=user.user_name, password='asdf')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.check_datetime_localised(b.find_element_by_xpath(
            '//table//td'
            '[preceding-sibling::th[1]/text() = "Queued"]').text)
        self.check_datetime_localised(b.find_element_by_xpath(
            '//table//td'
            '[preceding-sibling::th[1]/text() = "Started"]').text)
        self.check_datetime_localised(b.find_element_by_xpath(
            '//table//td'
            '[preceding-sibling::th[1]/text() = "Finished"]').text)

    def test_invalid_datetimes_arent_localised(self):
        with session.begin():
            user = data_setup.create_user(password=u'asdf')
            user.use_old_job_page = True
            job = data_setup.create_job()
        b = self.browser
        login(b, user=user.user_name, password='asdf')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.assertEquals(
            b.find_element_by_xpath('//table//td'
                                    '[preceding-sibling::th[1]/text() = "Finished"]').text,
            '')

    # https://bugzilla.redhat.com/show_bug.cgi?id=706435
    def test_task_result_datetimes_are_localised(self):
        with session.begin():
            user = data_setup.create_user(password=u'asdf')
            user.use_old_job_page = True
            job = data_setup.create_completed_job()
        b = self.browser
        login(b, user=user.user_name, password='asdf')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        recipe_id = job.recipesets[0].recipes[0].id
        b.find_element_by_xpath(
            '//div[@id="recipe%s"]//a[text()="Show Results"]' % recipe_id).click()
        b.find_element_by_xpath(
            '//div[@id="recipe-%d-results"]//table' % recipe_id)
        recipe_task_start, recipe_task_finish, recipe_task_duration = \
            b.find_elements_by_xpath(
                '//div[@id="recipe-%d-results"]//table'
                '/tbody/tr[1]/td[3]/div' % recipe_id)
        self.check_datetime_localised(recipe_task_start.text.strip())
        self.check_datetime_localised(recipe_task_finish.text.strip())
        self.check_datetime_localised(b.find_element_by_xpath(
            '//div[@id="recipe-%d-results"]//table'
            '/tbody/tr[2]/td[3]' % recipe_id).text)

    def check_datetime_localised(self, dt):
        self.assert_(re.match(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d [-+]\d\d:\d\d$', dt),
                     '%r does not look like a localised datetime' % dt)

    # https://bugzilla.redhat.com/show_bug.cgi?id=881387
    def test_guestrecipes_appear_after_host(self):
        with session.begin():
            user = data_setup.create_user(password=u'asdf')
            user.use_old_job_page = True
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
        login(b, user=user.user_name, password='asdf')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        recipe_order = [elem.text for elem in b.find_elements_by_xpath(
            '//a[@class="recipe-id"]')]
        self.assertEquals(recipe_order, [host.t_id, guest.t_id])

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_job_activities_view(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job_owner.use_old_job_page = True
            job = data_setup.create_job(owner=job_owner)
            job.record_activity(user=job_owner, service=u'test',
                                field=u'test', action='change',
                                old='old', new='new')
        login(self.browser, user=job_owner.user_name, password=u'owner')
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        b.find_element_by_link_text("Toggle Job history").click()
        activity_row = b.find_element_by_xpath('//table[@id="job_history_datagrid"]/tbody/tr[1]')
        activity_row.find_element_by_xpath('./td[2][text()="%s"]' % u'test')
        activity_row.find_element_by_xpath('./td[4][text()="%s"]' % 'Job: %s' % job.id)
        activity_row.find_element_by_xpath('./td[6][text()="%s"]' % u'change')


class JobAttributeChangeTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def check_can_change_product(self, job, new_product):
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        Select(b.find_element_by_id('job_product')) \
            .select_by_visible_text(new_product.name)
        b.find_element_by_xpath('//div[text()="Product has been updated"]')

    def check_cannot_change_product(self, job):
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.assertFalse(b.find_element_by_id('job_product').is_enabled())

    def check_can_change_retention_tag(self, job, new_tag):
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        Select(b.find_element_by_id('job_retentiontag')) \
            .select_by_visible_text(new_tag)
        b.find_element_by_xpath('//div[text()="Tag has been updated"]')

    def check_cannot_change_retention_tag(self, job):
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        self.assertFalse(b.find_element_by_id('job_retentiontag').is_enabled())

    def test_job_owner_can_change_product(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job_owner.use_old_job_page = True
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'active',
                                        product=data_setup.create_product())
            new_product = data_setup.create_product()
        login(self.browser, user=job_owner.user_name, password=u'owner')
        self.check_can_change_product(job, new_product)

    def test_group_member_can_change_product_for_group_job(self):
        with session.begin():
            group = data_setup.create_group()
            job_owner = data_setup.create_user()
            group_member = data_setup.create_user(password=u'group_member')
            group_member.use_old_job_page = True
            group.add_member(job_owner)
            group.add_member(group_member)
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'active',
                                        product=data_setup.create_product(),
                                        group=group)
            new_product = data_setup.create_product()
        login(self.browser, user=group_member.user_name, password=u'group_member')
        self.check_can_change_product(job, new_product)

    def test_other_user_cannot_change_product(self):
        with session.begin():
            other_user = data_setup.create_user(password=u'other_user')
            other_user.use_old_job_page = True
            job = data_setup.create_job(retention_tag=u'active',
                                        product=data_setup.create_product())
        login(self.browser, user=other_user.user_name, password=u'other_user')
        self.check_cannot_change_product(job)

    def test_job_owner_can_change_retention_tag(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job_owner.use_old_job_page = True
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'scratch')
        login(self.browser, user=job_owner.user_name, password=u'owner')
        self.check_can_change_retention_tag(job, '60days')

    def test_group_member_can_change_retention_tag_for_group_job(self):
        with session.begin():
            group = data_setup.create_group()
            job_owner = data_setup.create_user()
            group_member = data_setup.create_user(password=u'group_member')
            group_member.use_old_job_page = True
            group.add_member(job_owner)
            group.add_member(group_member)
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'scratch',
                                        group=group)
        login(self.browser, user=group_member.user_name, password=u'group_member')
        self.check_can_change_retention_tag(job, '60days')

    def test_other_user_cannot_change_retention_tag(self):
        with session.begin():
            other_user = data_setup.create_user(password=u'other_user')
            other_user.use_old_job_page = True
            job = data_setup.create_job(retention_tag=u'scratch')
        login(self.browser, user=other_user.user_name, password=u'other_user')
        self.check_cannot_change_retention_tag(job)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1022333
    def test_change_retention_tag_clearing_product(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job_owner.use_old_job_page = True
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'active',
                                        product=data_setup.create_product())
        login(self.browser, user=job_owner.user_name, password=u'owner')
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        Select(b.find_element_by_id('job_retentiontag')) \
            .select_by_visible_text('scratch')
        b.find_element_by_xpath('//button[text()="Clear product"]').click()
        b.find_element_by_xpath('//div[text()="Tag has been updated"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_retention_tag_change(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job_owner.use_old_job_page = True
            job = data_setup.create_job(owner=job_owner,
                                        retention_tag=u'scratch')
        login(self.browser, user=job_owner.user_name, password=u'owner')
        self.check_can_change_retention_tag(job, '60days')
        with session.begin():
            self.assertEquals(job.activity[0].service, u'WEBUI')
            self.assertEquals(job.activity[0].field_name, 'Retention Tag')
            self.assertEquals(job.activity[0].object_name(), 'Job: %s' % job.id)
            self.assertEquals(job.activity[0].old_value, u'scratch')
            self.assertEquals(job.activity[0].new_value, u'60days')

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_priority_change(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job_owner.use_old_job_page = True
            job = data_setup.create_job(owner=job_owner)
        login(self.browser, user=job_owner.user_name, password=u'owner')
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        Select(b.find_element_by_id('priority_recipeset_%s' % job.recipesets[0].id)) \
            .select_by_visible_text('Low')
        b.find_element_by_xpath('//msg[text()="Priority has been updated"]')
        with session.begin():
            self.assertEquals(job.recipesets[0].activity[0].service, u'WEBUI')
            self.assertEquals(job.recipesets[0].activity[0].field_name, 'Priority')
            self.assertEquals(job.recipesets[0].activity[0].object_name(),
                              'RecipeSet: %s' % job.recipesets[0].id)
            self.assertEquals(job.recipesets[0].activity[0].old_value, u'Normal')
            self.assertEquals(job.recipesets[0].activity[0].new_value, u'Low')
