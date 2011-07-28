#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
from turbogears.database import session
from bkr.server.model import Group

class JobDelete(SeleniumTestCase):
    
    
    def setUp(self):
        self.password = 'password'
        self.user = data_setup.create_user(password=self.password)
        self.job_to_delete = data_setup.create_completed_job(owner=self.user)
        self.recipe_to_delete = self.job_to_delete.recipesets[0].recipes[0]
        self.job_to_delete_2 = data_setup.create_completed_job(owner=self.user)
        self.recipe_to_delete_2 = self.job_to_delete_2
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_admin(self):
        self.user.groups.append(Group.by_name(u'admin'))
        session.flush()
        self.job_delete()
        self.job_delete_jobpage()
        self.user.groups.remove(Group.by_name(u'admin'))
        session.flush()

    def test_not_admin(self):
        self.job_delete()
        self.job_delete_jobpage()

    def job_delete(self):
        sel = self.selenium
        try:
            self.logout()
        except Exception:
            pass
        self.login(user=self.user,password=self.password)
        sel.open('jobs/mine')
        sel.select("jobsearch_0_table", "label=Id")
        sel.select("jobsearch_0_operation", "label=is")
        sel.type("jobsearch_0_value", "%s" % self.job_to_delete.id)
        sel.click("Search")
        sel.wait_for_page_to_load('3000')
        sel.click("delete_J:%s" % self.job_to_delete.id)
        self.wait_and_try(lambda: self.failUnless(sel.is_text_present("Are you sure")))
        sel.click("//button[@type='button']")
        self.wait_and_try(lambda: self.assert_(self.job_to_delete.t_id not in sel.get_text('//body')))
        sel.open('recipes/%s' % self.recipe_to_delete.id)
        sel.wait_for_page_to_load('3000')
        self.assert_('Invalid R:%s, has been deleted' % self.recipe_to_delete.id in sel.get_text('//body'))

    def job_delete_jobpage(self):
        sel = self.selenium
        try:
            self.logout()
        except Exception:
            pass
        self.login(user=self.user, password=self.password)
        sel.open('jobs/%s' % self.job_to_delete_2.id)
        sel.wait_for_page_to_load('3000')
        sel.click("delete_J:%s" % self.job_to_delete_2.id)
        self.wait_and_try(lambda: self.failUnless(sel.is_text_present("Are you sure you want to perform delete?")))
        self.wait_and_try(lambda: sel.click("//button[@type='button']"))
        self.wait_and_try(lambda: self.failUnless(sel.is_text_present("Succesfully deleted J:%s" % self.job_to_delete_2.id)))
 

    def teardown(self):
        self.selenium.stop()





