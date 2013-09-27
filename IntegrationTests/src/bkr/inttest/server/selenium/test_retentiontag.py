from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base

class RetentionTagTestWD(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_edit(self):
        with session.begin():
            tag = data_setup.create_retention_tag()
            tag.expire_in_days = 30
            tag.needs_product = True
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text(tag.tag).click()
        b.find_element_by_name('tag').clear()
        b.find_element_by_name('tag').send_keys('pink-fluffy-unicorns')
        b.find_element_by_name('expire_in_days').clear()
        b.find_element_by_name('expire_in_days').send_keys('60')
        self.assertTrue(b.find_element_by_name('needs_product').is_selected())
        b.find_element_by_name('needs_product').click()
        b.find_element_by_id('Retention Tag').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        with session.begin():
            session.refresh(tag)
            self.assertEquals(tag.tag, u'pink-fluffy-unicorns')
            self.assertEquals(tag.expire_in_days, 60)
            self.assertEquals(tag.needs_product, False)

    def test_cannot_change_tag_name_to_an_existing_tag(self):
        with session.begin():
            existing_tag = data_setup.create_retention_tag()
            tag_to_edit = data_setup.create_retention_tag()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text(tag_to_edit.tag).click()
        b.find_element_by_name('tag').clear()
        b.find_element_by_name('tag').send_keys(existing_tag.tag)
        b.find_element_by_id('Retention Tag').submit()
        b.find_element_by_xpath('//div[@class="control-group error" and .//input[@name="tag"]]'
                '//span[string(.)="Retention tag already exists"]')

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
        self.failUnless(sel.is_text_present('Retention tag already exists'))
