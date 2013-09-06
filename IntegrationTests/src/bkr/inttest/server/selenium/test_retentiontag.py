from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup


class RetentionTagTest(SeleniumTestCase):

    @classmethod
    def setupClass(cls):
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()

    def test_tag_delete(self):
        with session.begin():
            default_tag = data_setup.create_retention_tag(default=True)
            tag_with_job = data_setup.create_retention_tag(default=False)
            new_job = data_setup.create_job()
            new_job.retention_tag = tag_with_job
            non_default_tag = data_setup.create_retention_tag(default=False)
        try:
            self.login()
        except: pass
        sel = self.selenium
        sel.open('retentiontag/delete/%s' % default_tag.id)
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present("%s is not applicable for deletion" % default_tag.tag))

        sel.open('retentiontag/delete/%s' % tag_with_job.id)
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present("%s is not applicable for deletion" % tag_with_job.tag))

        sel.open('retentiontag/delete/%s' % non_default_tag.id)
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present("Succesfully deleted %s" % non_default_tag.tag))

    def test_tag_add(self):
        try:
            self.login()
        except: pass
        tag_to_add = 'foo'
        sel = self.selenium
        sel.open("retentiontag/admin")
        sel.click("link=Add")
        sel.wait_for_page_to_load("30000")
        sel.type("Retention Tag_tag", "%s" % tag_to_add)
        sel.select("Retention Tag_default", "label=True")
        sel.click("Retention Tag_needs_product")

        sel.click("//button[text()='Save']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("OK"))
        self.failUnless(sel.is_text_present("%s" % tag_to_add))

        tag_to_add = 'bar'
        sel.open("retentiontag/admin")
        sel.click("link=Add")
        sel.wait_for_page_to_load("30000")
        sel.type("Retention Tag_tag", "%s"% tag_to_add)
        sel.select("Retention Tag_default", "label=False")
        sel.click("//button[text()='Save']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("OK"))
        self.failUnless(sel.is_text_present("%s" % tag_to_add))
        sel.click("link=%s" % tag_to_add)
        sel.wait_for_page_to_load('30000')
        self.assertEqual("off", sel.get_value("Retention Tag_needs_product"))

        sel.open("retentiontag/admin")
        sel.click("link=Add")
        sel.wait_for_page_to_load("30000")
        sel.type("Retention Tag_tag", "%s" % tag_to_add)
        sel.select("Retention Tag_default", "label=False")
        sel.click("//button[text()='Save']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Problem saving tag %s" % tag_to_add))
