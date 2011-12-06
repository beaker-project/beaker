from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session

class RemoveLabController(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.lc = data_setup.create_labcontroller(fqdn=u'1111')
        self.system.lab_controller = self.lc
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login()

    def teardown(self):
        self.selenium.stop()

    def test_remove_and_add(self):
        sel = self.selenium
        #Remove
        sel.open("labcontrollers/")
        sel.wait_for_page_to_load('30000')
        sel.click("//a[@onclick=\"has_watchdog('%s')\"]" % self.lc.id)
        sel.wait_for_page_to_load("30000")

        self.failUnless(sel.is_text_present("exact:%s Removed" % self.lc))
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.lab_controller is None)
        #Re add
        sel.open("labcontrollers/")
        sel.wait_for_page_to_load('30000')
        sel.click("//a[@href='unremove?id=%s']" % self.lc.id)
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present("Succesfully re-added %s" % self.lc.fqdn))


    def test_system_page(self):
        sel = self.selenium
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')
        lcs = sel.get_text('//form//table/tbody/tr[10]') #The Lab Controller td
        self.failUnless('%s' % self.lc.fqdn in lcs)
        self.failUnless(self.system.lab_controller is self.lc)

        # Remove it
        sel.open("labcontrollers/")
        sel.wait_for_page_to_load('30000')
        sel.click("//a[@onclick=\"has_watchdog('%s')\"]" % self.lc.id)
        sel.wait_for_page_to_load("30000")

        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')
        lcs = sel.get_text('//form//table/tbody/tr[10]')
        self.failUnless('%s' % self.lc.fqdn not in lcs)
        with session.begin():
            session.refresh(self.system)
            self.failUnless(not self.system.lab_controller)

        # Re add it
        sel.open("labcontrollers/")
        sel.wait_for_page_to_load('30000')
        sel.click("//a[@href='unremove?id=%s']" % self.lc.id)
        sel.wait_for_page_to_load('30000')
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')
        sel.select("form_lab_controller_id", "label=%s" % self.lc.fqdn)
        sel.click("link=Save Changes")
        sel.wait_for_page_to_load('30000')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.lab_controller is self.lc)
