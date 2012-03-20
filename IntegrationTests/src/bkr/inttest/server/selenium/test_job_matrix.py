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
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, get_server_base
from bkr.server.model import Response, RecipeSetResponse

class TestJobMatrixWebDriver(WebDriverTestCase):


    def setUp(self):
        self.job_whiteboard = data_setup.unique_name(u'foobarhi %s')
        self.recipe_whiteboard = data_setup.unique_name(u'sdfjkljk%s')
        self.passed_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Pass',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'i386'))

        session.flush()
        self.browser = self.get_browser()

    def test_deleted_whiteboard_not_shown(self):
        b = self.browser
        owner = data_setup.create_user(password='password')
        whiteboard = u'To be deleted %d' % int(time.time() * 1000)
        self.passed_job.owner = owner
        self.passed_job.whiteboard = whiteboard
        session.flush()
        login(b, user=owner.user_name, password='password')
        b.get(get_server_base() + 'matrix')
        whiteboard_options = b.find_element_by_xpath("//select[@name='whiteboard']").text

        # Confirm the whitebaoard is there before we delete it
        self.assert_(self.passed_job.whiteboard in whiteboard_options)

        #Now delete the only job with that whiteboard
        b.get(get_server_base() + 'jobs/%s' % self.passed_job.id)
        b.find_element_by_id('delete_J:%s' % self.passed_job.id).click()
        b.find_element_by_xpath("//button[@type='button']").click()

        # Confirm it is no longer there
        b.get(get_server_base() + 'matrix')
        whiteboard_options = b.find_element_by_xpath("//select[@name='whiteboard']").text
        self.assert_(self.passed_job.whiteboard not in whiteboard_options)

    def test_deleted_job_results_not_shown(self):
        data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Fail',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'i386'))
        data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Warn',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'i386'))
        session.flush()
        b = self.browser
        owner = data_setup.create_user(password='password')
        self.passed_job.owner = owner
        session.flush()
        login(b, user=owner.user_name, password='password')
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' in report_text)

        # Delete Job
        b.get(get_server_base() + 'jobs/%s' % self.passed_job.id)
        b.find_element_by_id('delete_J:%s' % self.passed_job.id).click()
        b.find_element_by_xpath("//button[@type='button']").click()

        # Assert it is no longer there
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' not in report_text)

    def test_nacked_recipe_results_not_shown(self):
        data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Fail',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'i386'))
        data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Warn',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'i386'))
        session.flush()
        b = self.browser
        owner = data_setup.create_user(password='password')
        self.passed_job.owner = owner 
        session.flush()
        login(b, user=owner.user_name, password='password')
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath("//input[@name='toggle_nacks_on']").click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' in report_text)

        # Nack Recipe
        response = Response.by_response('nak')
        self.passed_job.recipesets[0].nacked = RecipeSetResponse(response_id=response.id)
        session.flush()

        # Assert it is no longer there
        b.get(get_server_base() + 'matrix')
        b.find_element_by_xpath("//select[@name='whiteboard']/option[@value='%s']" % self.job_whiteboard).click()
        b.find_element_by_xpath("//input[@name='toggle_nacks_on']").click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        report_text = b.find_element_by_xpath("//div[@id='matrix-report']").text
        self.assert_('Pass: 1' not in report_text)

    def test_single_job(self):
        unique_whiteboard = data_setup.unique_name('whiteboard%s')
        non_unique_whiteboard = data_setup.unique_name('whiteboard%s')
        non_unique_rwhiteboard = data_setup.unique_name('rwhiteboard%s')
        distro = data_setup.create_distro(arch=u'i386')
        for i in range(0,9):
            data_setup.create_completed_job(
                    whiteboard=non_unique_whiteboard, result=u'Pass',
                    recipe_whiteboard=non_unique_rwhiteboard,
                    distro=distro)

        single_job = data_setup.create_completed_job(
                whiteboard=unique_whiteboard, result=u'Pass',
                recipe_whiteboard=data_setup.unique_name('rwhiteboard%s'),
                distro=distro)
        session.flush()
        b = self.browser
        b.get(get_server_base() + 'matrix')
        b.find_element_by_name('whiteboard_filter').send_keys(unique_whiteboard)
        b.find_element_by_name('do_filter').click()
        # With the following click() I often got a:
        # "StaleElementReferenceException: Element not found in the cache -
        # perhaps the page has changed since it was looked up"
        # I could do the retry in a loop, but this is qicker and simpler
        from time import sleep
        sleep(2)
        b.find_element_by_xpath("//select/option[@value='%s']" % unique_whiteboard).click()
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        b.find_element_by_link_text('Pass: 1').click()
        task_id = b.find_element_by_xpath('//table[position()=2]//tr[position()=2]/td').text
        self.assertEqual(task_id,
            single_job.recipesets[0].recipes[0].tasks[0].t_id)

        # Test by job id
        # See https://bugzilla.redhat.com/show_bug.cgi?id=803713
        single_job_2 = data_setup.create_completed_job(
                whiteboard=non_unique_whiteboard, result=u'Pass',
                recipe_whiteboard=non_unique_rwhiteboard,
                distro=distro)
        session.flush()
        b = self.browser
        b.get(get_server_base() + 'matrix')
        b.find_element_by_id('remote_form_job_ids').send_keys(str(single_job_2.id))
        b.find_element_by_xpath('//input[@value="Generate"]').click()
        b.find_element_by_link_text('Pass: 1').click()
        # This gets the last element, which shold also be the first element
        task_id = b.find_element_by_xpath('//table[position()=2]//tr[position()=(last() - 1)]/td').text
        self.assertEqual(task_id,
            single_job_2.recipesets[0].recipes[0].tasks[0].t_id)

    def tearDown(self):
        b = self.browser.quit()


class TestJobMatrix(SeleniumTestCase):
    def setUp(self):
        self.job_whiteboard = u'DanC says hi %d' % int(time.time() * 1000)
        self.recipe_whiteboard = u'breakage lol \'#&^!<'
        self.job_whiteboard_2 = u'rmancy says bye %d' % int(time.time() * 1000)
        self.passed_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Pass',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'i386'))
        self.warned_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Warn',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'ia64'))
        self.failed_job = data_setup.create_completed_job(
                whiteboard=self.job_whiteboard, result=u'Fail',
                recipe_whiteboard=self.recipe_whiteboard,
                distro=data_setup.create_distro(arch=u'x86_64'))
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_filter_button(self):
        sel = self.selenium
        sel.open('matrix')
        sel.wait_for_page_to_load('30000')
        sel.type("remote_form_whiteboard_filter", self.job_whiteboard[:int(len(self.job_whiteboard) /2)])
        sel.click("remote_form_do_filter")
        self.wait_and_try(lambda: self.assert_(self.job_whiteboard in sel.get_text('//select[@id="remote_form_whiteboard"]')))

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
        new_job = data_setup.create_completed_job(
            whiteboard=self.job_whiteboard, result=u'Pass',
            recipe_whiteboard=self.recipe_whiteboard,
            distro=data_setup.create_distro(arch=u'i386'))
        session.flush()
        sel.click('//input[@value="Generate"]')
        sel.wait_for_page_to_load('30000')
        body_2 = sel.get_text('//body')
        self.assert_('Pass: 2' in body_2)

        #Try with multiple whiteboards
        another_new_job = data_setup.create_completed_job(
            whiteboard=self.job_whiteboard_2, result=u'Pass',
            recipe_whiteboard=self.recipe_whiteboard,
            distro=data_setup.create_distro(arch=u'i386'))
        session.flush()
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

        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table[@class=' FixedColumns_Cloned'].0.0"), 'Task')
        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table.0.1"),
            'i386')
        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table.0.2"),
            'ia64')
        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table.0.3"),
            'x86_64')

        # get_table('matrix_datagrid') doesn't seem to return anything
        # possibly because of elements inside table
        body = sel.get_text("//table[@id='matrix_datagrid']/tbody")
        self.assert_('Pass: 1' in body)
        self.assert_('Warn: 1' in body)
        self.assert_('Fail: 1' in body)

        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table.1.1"),
            '%s' % self.recipe_whiteboard)
        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table.1.2"),
            '%s' % self.recipe_whiteboard)
        self.assertEqual(sel.get_table("//div[@class='dataTables_scrollHeadInner']/table.1.3"),
            '%s' % self.recipe_whiteboard)
        sel.click('link=Pass: 1')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Executed Tasks')
        self.assertEqual(sel.get_value('whiteboard'), self.recipe_whiteboard)
        self.assertEqual(sel.get_table('css=.list.1.0'),
                self.passed_job.recipesets[0].recipes[0].tasks[0].t_id)
        sel.go_back()
        sel.wait_for_page_to_load('30000')
        sel.click('link=Warn: 1')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Executed Tasks')
        self.assertEqual(sel.get_value('whiteboard'), self.recipe_whiteboard)
        self.assertEqual(sel.get_table('css=.list.1.0'),
                self.warned_job.recipesets[0].recipes[0].tasks[0].t_id)
        sel.go_back()
        sel.wait_for_page_to_load('30000')

        sel.click('link=Fail: 1')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Executed Tasks')
        self.assertEqual(sel.get_value('whiteboard'), self.recipe_whiteboard)
        self.assertEqual(sel.get_table('css=.list.1.0'),
                self.failed_job.recipesets[0].recipes[0].tasks[0].t_id)
