#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from turbogears.database import session
from bkr.inttest import data_setup
import unittest, time, os


class SystemOwnerTake(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()

        with session.begin():
            self.manual_system = data_setup.create_system(status=u'Manual')
            self.manual_system.shared = True
            self.user = data_setup.create_user(password='password')
            self.manual_system.owner = self.user
            lc = data_setup.create_labcontroller(u'test-lc')
            data_setup.add_system_lab_controller(self.manual_system,lc)
        self.login(user=self.user.user_name,password='password')

    def tearDown(self):
        self.selenium.stop()

    def test_owner_manual_system(self):
        sel = self.selenium
        sel.open("")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        self.assert_(sel.is_text_present("Take"))
        sel.click("link=Take")
        sel.wait_for_page_to_load('30000')
        self.assert_("Reserved %s" % self.manual_system.fqdn in sel.get_text('//body'))


class SystemGroupUserTake(SeleniumTestCase):

    """
    Tests the following scenarios for take in both Automated and Manual machines:
    * System with no groups - regular user
    * System has group, user not in group
    * System has group, user in group
    """

    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()

        with session.begin():
            self.automated_system = data_setup.create_system()
            self.automated_system.shared = True
            self.manual_system = data_setup.create_system(status=u'Manual')
            self.manual_system.shared = True
            self.group = data_setup.create_group() 
            self.user = data_setup.create_user(password='password')
            self.wrong_group = data_setup.create_group()
            self.user2 = data_setup.create_user(password=u'password')
            lc = data_setup.create_labcontroller(u'test-lc')
            data_setup.add_system_lab_controller(self.automated_system,lc)
            data_setup.add_system_lab_controller(self.manual_system,lc)
            session.flush()
            self.distro_tree = data_setup.create_distro_tree()
        self.login(user=self.user.user_name,password='password')

    def test_schedule_provision_system_has_user(self):
        with session.begin():
            self.automated_system.user = self.user2
        self.logout()
        self.login() # login as admin
        sel = self.selenium
        sel.open("view/%s/" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        sel.click("link=Provision")
        try: self.failUnless(sel.is_text_present("Schedule provision"))
        except AssertionError, e: self.verificationErrors.append('Admin has no schedule provision option when system is in use')

    def test_schedule_provision_system_has_user_with_group(self): 
        with session.begin():
            self.automated_system.user = self.user2
            data_setup.add_user_to_group(self.user,self.group)
            data_setup.add_group_to_system(self.automated_system,self.group)
        self.logout() 
        self.login(user=self.user.user_name,password='password') # login as admin
        sel = self.selenium
        sel.open("view/%s/" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        sel.click("link=Provision")
        try: self.failUnless(sel.is_text_present("Schedule provision"))
        except AssertionError, e: self.verificationErrors.append('Systemgroup has no schedule provision option when system is in use')


    def test_system_no_group(self):
        #Auto Machine
        sel = self.selenium
        sel.open("")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("Take")) #Automated should not have Take for this user
        except AssertionError, e: self.verificationErrors.append('Take is present on automated machine with no groups')

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        sel.open('user_change?id=%s' % self.automated_system.id)
        sel.wait_for_page_to_load("30000")
        self.assert_('You were unable to change the user for %s' % self.automated_system.fqdn in sel.get_text('//body'))
   

        #Manual machine
        #import pdb;pdb.set_trace()
        sel.open("")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Take")) #Should have Take for this machine
        except AssertionError, e: self.verificationErrors.append('Take is not present on manual machine with no groups')
        self._do_take(self.manual_system.fqdn)

    def test_system_has_group(self):
        #Automated machine
        with session.begin():
            data_setup.add_group_to_system(self.automated_system,self.group) # Add systemgroup
        sel = self.selenium
        sel.open("")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("Take")) #Should not be here
        except AssertionError, e: self.verificationErrors.append('Take is present on automated machine with group')

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        sel.open('user_change?id=%s' % self.automated_system.id)
        sel.wait_for_page_to_load("30000")
        self.assert_('You were unable to change the user for %s' % self.automated_system.fqdn in sel.get_text('//body'))

        try:
            self._do_schedule_provision(self.automated_system.fqdn,reraise=True) #Should not be able to provision either
        except AssertionError, e: #Hmm, this is actually a good thing!
            pass
        else:
            self.verificationErrors.append('System with group should not have  \
            schedule provision option for not group members')

        #Manual machine
        with session.begin():
            data_setup.add_group_to_system(self.manual_system, self.group) # Add systemgroup
        sel = self.selenium
        sel.open("")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("Take")) #Should not be here
        except AssertionError, e: self.verificationErrors.append('Take is present on manual machine with group')

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        sel.open('user_change?id=%s' % self.manual_system.id)
        sel.wait_for_page_to_load("30000")
        self.assert_('You were unable to change the user for %s' % self.manual_system.fqdn in sel.get_text('//body'))

        try:
            self._do_schedule_provision(self.manual_system.fqdn, reraise=True) #Should not be able to provision either
        except AssertionError, e: #Hmm, this is actually a good thing!
            pass
        else:
            self.verificationErrors.append('System with group should not have  \
            schedule provision option for not group members')

    def test_system_group_user_group(self):
        #Automated machine
        with session.begin():
            data_setup.add_group_to_system(self.automated_system, self.group) # Add systemgroup
            data_setup.add_user_to_group(self.user, self.wrong_group) # Add user to group
        sel = self.selenium
        self.logout()
        self.login(user=self.user.user_name, password='password')
        sel.open("")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn) #this tests the click! 
        sel.wait_for_page_to_load("30000")
        self.assertEqual("%s" % self.automated_system.fqdn, sel.get_title()) #ensure the page has opened
        try: self.failUnless(not sel.is_text_present("Take")) #Should be not here
        except AssertionError, e: self.verificationErrors.\
            append('Take is available to automated machine with system group privs' )

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        sel.open('user_change?id=%s' % self.automated_system.id)
        sel.wait_for_page_to_load("30000")
        self.assert_('You were unable to change the user for %s' % self.automated_system.fqdn in sel.get_text('//body'))

        with session.begin():
            self.user.groups = [self.group]

        sel.open("")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Take")) #Should be here
        except AssertionError, e: self.verificationErrors.\
            append('Take is not available to automated machine with system group pirvs' )
        self._do_schedule_provision(self.automated_system.fqdn)

        # Now can I actually take it?
        sel.open("")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        self._do_take(self.automated_system.fqdn)

        #Manual machine
        with session.begin():
            data_setup.add_group_to_system(self.manual_system, self.group) # Add systemgroup
        sel = self.selenium
        sel.open("")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Take")) #Should be here
        except AssertionError, e: self.verificationErrors.append('Take is not here for manual machine with system group privs')
        self._do_schedule_provision(self.manual_system.fqdn)

        # Now can I actually take it?
        sel.open("")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.submit('id=simpleform')
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        self._do_take(self.manual_system.fqdn)

    def _do_take(self, system_fqdn):
        sel = self.selenium
        sel.click('link=Take')
        sel.wait_for_page_to_load("30000")
        try:
            self.assertEquals(sel.get_text('css=.flash'), 'Reserved %s' % system_fqdn)
        except AssertionError, e:
            self.verificationErrors.append(e)

    def _do_schedule_provision(self,system_fqdn,reraise=False):
        #Check we can do a schedule provision as well
        sel = self.selenium
        sel.click("link=Provision")

        try:
            self.failUnless(sel.is_text_present("Schedule provision"))
        except AssertionError, e:
            if reraise:
                raise
            self.verificationErrors.append('No Schedule provision option for system %s' % system_fqdn)
        sel.select("provision_prov_install", "label=%s" % self.distro_tree)
        sel.click("//button[text()='Schedule provision']")
        sel.wait_for_page_to_load("30000")
        try:
            self.failUnless(sel.is_text_present("Success!"))
        except AssertionError, e:
            if reraise:
                raise
            self.verificationErrors.append('Did not succesfully create job')


    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
