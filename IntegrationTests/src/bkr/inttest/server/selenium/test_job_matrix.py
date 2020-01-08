
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import unittest
import logging
import time
import tempfile
from turbogears.database import session
from selenium.webdriver.support.ui import Select
from bkr.server.model import TaskResult
from bkr.inttest.server.webdriver_utils import login, is_text_present, \
        delete_and_confirm, click_menu_item
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import Job

class TestJobMatrixWebDriver(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.job_whiteboard = data_setup.unique_name(u'foobarhi %s')
        self.recipe_whiteboard = data_setup.unique_name(u'sdfjkljk%s')
        self.passed_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=TaskResult.pass_,
                recipe_whiteboard=self.recipe_whiteboard)

        self.browser = self.get_browser()

    def test_max_whiteboard(self):
        max = Job.max_by_whiteboard
        c = 0
        whiteboard =u'whiteboard'
        with session.begin():
            while c <= max:
                data_setup.create_completed_job(whiteboard=whiteboard)
                c += 1
        b = self.browser
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % whiteboard).click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        self.failUnless(is_text_present(b, "Your whiteboard contains %d jobs, only %s will be used" % (c, Job.max_by_whiteboard)))

    def test_whiteboard_filtering(self):
        whiteboard = u'Colonel Tear Won'
        with session.begin():
            data_setup.create_completed_job(whiteboard=whiteboard)
        b = self.browser
        b.get(get_server_base() + 'matrix')
        b.find_element_by_id('remote_form_whiteboard_filter')\
            .send_keys('this will not find anything')
        b.find_element_by_id('remote_form_do_filter').click()
        # Wait for our empty list of whiteboards to come back
        b.find_element_by_xpath('//select[@name="whiteboard" and not(./option)]')
        # Now filter for a real whiteboard
        b.find_element_by_id('remote_form_whiteboard_filter').clear()
        b.find_element_by_id('remote_form_whiteboard_filter')\
            .send_keys(whiteboard[:len(whiteboard) // 2])
        b.find_element_by_id('remote_form_do_filter').click()
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % whiteboard)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1302857
    def test_whiteboard_filtering_handles_whiteboards_with_embedded_newlines(self):
        whiteboard = u' Colonel Tear\n\tWon'
        with session.begin():
            data_setup.create_completed_job(whiteboard=whiteboard)
        b = self.browser
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % whiteboard).click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        b.find_element_by_link_text('Pass: 1')

    def test_deleted_whiteboard_not_shown(self):
        b = self.browser
        with session.begin():
            owner = data_setup.create_user(password='password')
            whiteboard = u'To be deleted %d' % int(time.time() * 1000)
            self.passed_job.owner = owner
            self.passed_job.whiteboard = whiteboard
        login(b, user=owner.user_name, password='password')
        b.get(get_server_base() + 'matrix')
        whiteboard_options = b.find_element_by_xpath("//select[@name='whiteboard']").text

        # Confirm the whitebaoard is there before we delete it
        self.assert_(self.passed_job.whiteboard in whiteboard_options)

        #Now delete the only job with that whiteboard
        with session.begin():
            self.passed_job.deleted = datetime.datetime.utcnow()

        # Confirm it is no longer there
        b.get(get_server_base() + 'matrix')
        whiteboard_options = b.find_element_by_xpath("//select[@name='whiteboard']").text
        self.assert_(self.passed_job.whiteboard not in whiteboard_options)

    def test_deleted_job_results_not_shown(self):
        with session.begin():
            data_setup.create_completed_job(
                    whiteboard=self.job_whiteboard, result=TaskResult.fail,
                    recipe_whiteboard=self.recipe_whiteboard)
            data_setup.create_completed_job(
                    whiteboard=self.job_whiteboard, result=TaskResult.warn,
                    recipe_whiteboard=self.recipe_whiteboard)
            owner = data_setup.create_user(password='password')
            self.passed_job.owner = owner
        b = self.browser
        login(b, user=owner.user_name, password='password')
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' in report_text)

        # Delete Job
        with session.begin():
            self.passed_job.deleted = datetime.datetime.utcnow()

        # Assert it is no longer there
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' not in report_text)

    def test_nacked_recipe_results_not_shown(self):
        with session.begin():
            data_setup.create_completed_job(
                    whiteboard=self.job_whiteboard, result=TaskResult.fail,
                    recipe_whiteboard=self.recipe_whiteboard)
            data_setup.create_completed_job(
                    whiteboard=self.job_whiteboard, result=TaskResult.warn,
                    recipe_whiteboard=self.recipe_whiteboard)
            owner = data_setup.create_user(password='password')
            self.passed_job.owner = owner
        b = self.browser
        login(b, user=owner.user_name, password='password')
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath("//input[@name='toggle_nacks_on']").click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' in report_text)

        # Nack Recipe
        with session.begin():
            self.passed_job.recipesets[0].waived = True

        # Assert it is no longer there
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath("//input[@name='toggle_nacks_on']").click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' not in report_text)

    def test_single_job(self):
        with session.begin():
            unique_whiteboard = data_setup.unique_name('whiteboard%s')
            non_unique_whiteboard = data_setup.unique_name('whiteboard%s')
            non_unique_rwhiteboard = data_setup.unique_name('rwhiteboard%s')
            distro_tree = data_setup.create_distro_tree(arch=u'i386')
            for i in range(0,9):
                data_setup.create_completed_job(
                        whiteboard=non_unique_whiteboard, result=TaskResult.pass_,
                        recipe_whiteboard=non_unique_rwhiteboard,
                        distro_tree=distro_tree)

            single_job = data_setup.create_completed_job(
                    whiteboard=unique_whiteboard, result=TaskResult.pass_,
                    recipe_whiteboard=data_setup.unique_name('rwhiteboard%s'),
                    distro_tree=distro_tree)

        b = self.browser
        b.get(get_server_base() + 'matrix')
        # No need to filter the whiteboard, we just created the jobs so they
        # will be at the top of the list of whiteboards.
        b.find_element_by_xpath("//select/option[@value='%s']" % unique_whiteboard).click()
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        b.find_element_by_link_text('Pass: 1').click()
        # Should take us to Executed Tasks filtered by whiteboard.
        # There should only be one task in the results.
        tasks_table = b.find_element_by_css_selector('table.tasks')
        task_ids = [e.text for e in tasks_table.find_elements_by_xpath(
                'tbody/tr/td[1][@class="task"]')]
        self.assertEquals(task_ids, [single_job.recipesets[0].recipes[0].tasks[0].t_id])

        # Test by job id
        # See https://bugzilla.redhat.com/show_bug.cgi?id=803713
        with session.begin():
            single_job_2 = data_setup.create_completed_job(
                    whiteboard=non_unique_whiteboard, result=TaskResult.pass_,
                    recipe_whiteboard=non_unique_rwhiteboard,
                    distro_tree=distro_tree)
        b = self.browser
        b.get(get_server_base() + 'matrix')
        b.find_element_by_id('remote_form_job_ids').send_keys(str(single_job_2.id))
        b.find_element_by_xpath('//button[@type="submit" and text()="Generate"]').click()
        b.find_element_by_link_text('Pass: 1').click()
        # Should take us to Executed Tasks filtered by whiteboard and job ID.
        # There should only be one task in the results.
        tasks_table = b.find_element_by_css_selector('table.tasks')
        task_ids = [e.text for e in tasks_table.find_elements_by_xpath(
                'tbody/tr/td[1][@class="task"]')]
        self.assertEquals(task_ids, [single_job_2.recipesets[0].recipes[0].tasks[0].t_id])

class TestJobMatrix(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.job_whiteboard = u'DanC says hi %d' % int(time.time() * 1000)
        self.recipe_whiteboard = u'breakage lol \'#&^!<'
        self.job_whiteboard_2 = u'rmancy says bye %d' % int(time.time() * 1000)
        self.passed_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=TaskResult.pass_,
                recipe_whiteboard=self.recipe_whiteboard,
                distro_tree=data_setup.create_distro_tree(arch=u'i386'))
        self.warned_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=TaskResult.warn,
                recipe_whiteboard=self.recipe_whiteboard,
                distro_tree=data_setup.create_distro_tree(arch=u'ia64'))
        self.failed_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=TaskResult.fail,
                recipe_whiteboard=self.recipe_whiteboard,
                distro_tree=data_setup.create_distro_tree(arch=u'x86_64'))
        self.browser = self.get_browser()

    def test_generate_by_whiteboard(self):
        b = self.browser
        b.get(get_server_base() + 'matrix/')
        Select(b.find_element_by_name('whiteboard'))\
            .select_by_visible_text(self.job_whiteboard)
        b.find_element_by_xpath('//button[text()="Generate"]').click()
        b.find_element_by_xpath('//table[@id="matrix_datagrid"]'
                '//td[normalize-space(string(.))="Pass: 1"]')
        with session.begin():
            new_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=TaskResult.pass_,
                recipe_whiteboard=self.recipe_whiteboard)
        b.find_element_by_xpath('//button[text()="Generate"]').click()
        b.find_element_by_xpath('//table[@id="matrix_datagrid"]'
                '//td[normalize-space(string(.))="Pass: 2"]')

        #Try with multiple whiteboards
        with session.begin():
            another_new_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard_2, result=TaskResult.pass_,
                recipe_whiteboard=self.recipe_whiteboard)
        b.get(get_server_base() + 'matrix/')
        whiteboard = Select(b.find_element_by_name('whiteboard'))
        whiteboard.select_by_visible_text(self.job_whiteboard)
        whiteboard.select_by_visible_text(self.job_whiteboard_2)
        b.find_element_by_xpath('//button[text()="Generate"]').click()
        b.find_element_by_xpath('//table[@id="matrix_datagrid"]'
                '//td[normalize-space(string(.))="Pass: 3"]')
