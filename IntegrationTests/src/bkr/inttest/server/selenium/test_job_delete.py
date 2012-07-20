#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session
from bkr.server.model import Group

class JobDelete(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.password = 'password'
        self.user = data_setup.create_user(password=self.password)
        self.job_to_delete = data_setup.create_completed_job(owner=self.user)
        self.job_to_delete_2 = data_setup.create_completed_job(owner=self.user)
        self.recipe_to_delete = self.job_to_delete.recipesets[0].recipes[0]
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_admin(self):
        self.login()
        self.job_delete()
        self.job_delete_jobpage()

    def test_not_admin(self):
        self.login(user=self.user, password=self.password)
        self.job_delete()
        self.job_delete_jobpage()

    def job_delete(self):
        sel = self.selenium
        sel.open('jobs')
        sel.wait_for_page_to_load('30000')
        sel.select("jobsearch_0_table", "label=Id")
        sel.select("jobsearch_0_operation", "label=is")
        sel.type("jobsearch_0_value", "%s" % self.job_to_delete.id)
        sel.click("Search")
        sel.wait_for_page_to_load('30000')
        sel.click("//td[preceding-sibling::td/a[normalize-space(text())='%s']]"
            "/div/a[normalize-space(text())='Delete']" % self.job_to_delete.t_id)
        self.wait_and_try(lambda:
            self.failUnless(sel.is_text_present("Are you sure")))
        sel.click("//button[@type='button' and text()='Yes']")
        self.wait_and_try(lambda:
            self.assert_(self.job_to_delete.t_id not in sel.get_text('//body')))
        sel.open('recipes/%s' % self.recipe_to_delete.id)
        sel.wait_for_page_to_load('30000')
        self.assert_('Invalid R:%s, has been deleted' %
            self.recipe_to_delete.id in sel.get_text('//body'))

    def job_delete_jobpage(self):
        sel = self.selenium
        sel.open('jobs/%s' % self.job_to_delete_2.id)
        sel.wait_for_page_to_load('30000')
        sel.click("//form[@action='delete_job_page']"
            "/a[normalize-space(text())='Delete']")
        self.wait_and_try(lambda:
            self.failUnless(sel.is_text_present(
            "Are you sure you want to delete this?")))
        sel.click("//button[@type='button' and text()='Yes']")
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present(
            "Succesfully deleted J:%s" % self.job_to_delete_2.id))

    def teardown(self):
        self.selenium.stop()
