# Beaker
#
# Copyright (c) 2010 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import unittest
import logging
import time
import tempfile
from turbogears.database import session
from selenium.webdriver.support.ui import WebDriverWait
from bkr.server.model import TaskResult
from bkr.inttest.server.webdriver_utils import login, is_text_present, delete_and_confirm
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import Job, Response, RecipeSetResponse

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
        b.find_element_by_xpath('//input[@value="Generate"]').click()
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
        b.get(get_server_base() + 'jobs/%s' % self.passed_job.id)
        delete_and_confirm(b, "//form[@action='delete_job_page']")

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
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' in report_text)

        # Delete Job
        b.get(get_server_base() + 'jobs/%s' % self.passed_job.id)
        delete_and_confirm(b, "//form[@action='delete_job_page']")

        # Assert it is no longer there
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
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
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' in report_text)

        # Nack Recipe
        with session.begin():
            response = Response.by_response('nak')
            self.passed_job.recipesets[0].nacked = RecipeSetResponse(response_id=response.id)

        # Assert it is no longer there
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath("//input[@name='toggle_nacks_on']").click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
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
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        b.find_element_by_link_text('Pass: 1').click()
        task_id = b.find_element_by_xpath('//table[position()=2]//tr[position()=2]/td').text
        self.assertEqual(task_id,
            single_job.recipesets[0].recipes[0].tasks[0].t_id)

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
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        b.find_element_by_link_text('Pass: 1').click()

        # This tests that we are indeed only looking at one recipe task.
        task_spec_columns = b.find_elements_by_xpath('//table[2]//tr/td[1]')
        failed = True
        for col in task_spec_columns:
            if col and col.text.strip():
                self.assertEqual(col.text, single_job_2.recipesets[0].recipes[0].tasks[0].t_id)
                failed=False
        self.assert_(not failed)

    def tearDown(self):
        b = self.browser.quit()

class TestJobMatrix(SeleniumTestCase):

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
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_generate_by_whiteboard(self):
        sel = self.selenium
        sel.open('matrix')
        sel.wait_for_page_to_load('30000')
        sel.select('whiteboard', self.job_whiteboard)
        sel.click('//select[@name="whiteboard"]//option[@value="%s"]'
                % self.job_whiteboard)
        sel.click('//input[@value="Generate"]')
        sel.wait_for_page_to_load('30000')
        body = sel.get_text('//body')
        self.assert_('Pass: 1' in body)
        with session.begin():
            new_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=TaskResult.pass_,
                recipe_whiteboard=self.recipe_whiteboard)
        sel.click('//input[@value="Generate"]')
        sel.wait_for_page_to_load('30000')
        body_2 = sel.get_text('//body')
        self.assert_('Pass: 2' in body_2)

        #Try with multiple whiteboards
        with session.begin():
            another_new_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard_2, result=TaskResult.pass_,
                recipe_whiteboard=self.recipe_whiteboard)
        sel.open('matrix')
        sel.wait_for_page_to_load('30000')
        sel.add_selection("whiteboard", "label=%s" % self.job_whiteboard)
        sel.add_selection("whiteboard", "label=%s" % self.job_whiteboard_2)
        sel.click('//input[@value="Generate"]')
        sel.wait_for_page_to_load('30000')
        body = sel.get_text('//body')
        self.assert_('Pass: 3' in body)

    def test_it(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=Matrix')
        sel.wait_for_page_to_load('30000')
        sel.type('remote_form_whiteboard_filter', self.job_whiteboard)
        sel.click('//input[@value="Generate"]')
        sel.wait_for_page_to_load('30000')
        # why are both .select and .click necessary?? weird
        # Because there are two fields and we need to know from which we are
        # generating our result
        sel.select('whiteboard', 'label=%s' % self.job_whiteboard)
        sel.click('//select[@name="whiteboard"]//option[@value="%s"]'
                % self.job_whiteboard)
        sel.click('//input[@value="Generate"]')
        sel.wait_for_page_to_load('30000')

        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[1]/th[1]"), 'Task')
        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[1]/th[2]"),
            'i386')
        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[1]/th[3]"),
            'ia64')
        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[1]/th[4]"),
            'x86_64')

        body = sel.get_text("//table[@id='matrix_datagrid']/tbody")
        self.assert_('Pass: 1' in body)
        self.assert_('Warn: 1' in body)
        self.assert_('Fail: 1' in body)

        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[2]/th[2]"),
            '%s' % self.recipe_whiteboard)
        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[2]/th[3]"),
            '%s' % self.recipe_whiteboard)
        self.assertEqual(sel.get_text("//div[@class='dataTables_scrollHeadInner']/table[1]/thead/tr[2]/th[4]"),
            '%s' % self.recipe_whiteboard)
        sel.click('link=Pass: 1')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Executed Tasks')
        self.assertEqual(sel.get_value('whiteboard'), self.recipe_whiteboard)
        self.assertEqual(sel.get_text('//table[@class="list"]/tbody/tr[2]/td[1]'),
                self.passed_job.recipesets[0].recipes[0].tasks[0].t_id)
        sel.go_back()
        sel.wait_for_page_to_load('30000')
        sel.click('link=Warn: 1')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Executed Tasks')
        self.assertEqual(sel.get_value('whiteboard'), self.recipe_whiteboard)
        self.assertEqual(sel.get_text('//table[@class="list"]/tbody/tr[2]/td[1]'),
                self.warned_job.recipesets[0].recipes[0].tasks[0].t_id)
        sel.go_back()
        sel.wait_for_page_to_load('30000')

        sel.click('link=Fail: 1')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Executed Tasks')
        self.assertEqual(sel.get_value('whiteboard'), self.recipe_whiteboard)
        self.assertEqual(sel.get_text('//table[@class="list"]/tbody/tr[2]/td[1]'),
                self.failed_job.recipesets[0].recipes[0].tasks[0].t_id)
