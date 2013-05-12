import unittest, time, re, os
from turbogears.database import session
from bkr.inttest import get_server_base
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present
from bkr.inttest import data_setup


class AddUserWD(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_add_invalid_details_existing_user(self):
        with session.begin():
            existing_name = data_setup.unique_name('user%s')
            existing_email = data_setup.unique_name('me%s@my.com')
            data_setup.create_user(user_name=existing_name,
                email_address=existing_email)

            existing_name2 = data_setup.unique_name('user%s')
            existing_email2 = data_setup.unique_name('me%s@my.com')
            data_setup.create_user(user_name=existing_name2,
                email_address=existing_email2)

        b = self.browser
        login(b)
        b.get(get_server_base() + 'users')
        # Test with duplicate name
        b.find_element_by_name('user.text').send_keys(existing_name)
        b.find_element_by_xpath('//form[@id=\'Search\']').submit()
        b.find_element_by_link_text(existing_name).click()
        b.find_element_by_name('user_name').clear()
        b.find_element_by_name('user_name').send_keys(existing_name2)
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'user_name\']/following-sibling::span').text == \
                'Login name is not unique')
        # Reset back to current name
        b.find_element_by_name('user_name').clear()
        b.find_element_by_name('user_name').send_keys(existing_name)

        # Test with duplicate email
        b.find_element_by_name('email_address').clear()
        b.find_element_by_name('email_address').send_keys(existing_email2)
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'email_address\']/following-sibling::span').text == \
                'Email address is not unique')

        # Verify our exiting details submit ok
        b.find_element_by_name('email_address').clear()
        b.find_element_by_name('email_address').send_keys(existing_email)
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        is_text_present(b, '%s saved' % existing_name)

    def test_add_invalid_details_new_user(self):
        with session.begin():
            existing_name = data_setup.unique_name('user%s')
            existing_email = data_setup.unique_name('thisguysemail%s@my.com')
            data_setup.create_user(user_name=existing_name, password='password',
                email_address=existing_email)
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users')
        b.find_element_by_link_text('Add ( + )').click()

        # Test with all blank fields
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'user_name\']/following-sibling::span').text == \
                'Please enter a value')
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'display_name\']/following-sibling::span').text == \
                'Please enter a value')
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'email_address\']/following-sibling::span').text == \
                'Please enter an email address')

        # Submit valid details to make sure it recovers
        valid_user_1 = data_setup.unique_name('user%s')
        b.find_element_by_name('user_name').send_keys(valid_user_1)
        b.find_element_by_name('display_name').send_keys(valid_user_1)
        b.find_element_by_name('email_address').send_keys(data_setup.unique_name('thisguysemail%s@my.com'))
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        is_text_present(b, '%s saved' % valid_user_1)

        # Enter duplicate user name
        b.get(get_server_base() + 'users')
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_name('user_name').send_keys(existing_name)
        b.find_element_by_name('display_name').send_keys(data_setup.unique_name('display%s'))
        b.find_element_by_name('email_address').send_keys(data_setup.unique_name('thisguysemail%s@my.com'))

        # Check our custom user name validator
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'user_name\']/following-sibling::span').text == \
                'Login name is not unique')

        valid_user_2 = data_setup.unique_name('user%s')
        b.find_element_by_name('user_name').send_keys(valid_user_2)
        b.find_element_by_class_name('submitbutton').click()
        is_text_present(b, '%s saved' % valid_user_2)

        # Check our custom email address validator
        b.get(get_server_base() + 'users')
        b.find_element_by_link_text('Add ( + )').click()
        valid_user_3 = data_setup.unique_name('user%s')
        b.find_element_by_name('user_name').send_keys(valid_user_3)
        b.find_element_by_name('display_name').send_keys(valid_user_3)
        b.find_element_by_name('email_address').send_keys(existing_email)
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        self.assert_(b.find_element_by_xpath('//form[@id=\'User\'] \
            //input[@name=\'email_address\']/following-sibling::span').text == \
                'Email address is not unique')

        # Enter valid email to ensure recovery
        valid_email = data_setup.unique_name('me%s@my.com')
        b.find_element_by_name('email_address').send_keys(valid_email)
        b.find_element_by_xpath('//form[@id=\'User\']').submit()
        is_text_present(b, '%s saved' % valid_user_3)

class AddUser(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login()

    def test_adduser(self):
        user_1_name = data_setup.unique_name('anonymous%s')
        user_1_email = data_setup.unique_name('anonymous%s@my.com')
        user_1_pass = 'password'

        user_2_name = data_setup.unique_name('anonymous%s')
        user_2_email = data_setup.unique_name('anonymous%s@my.com')
        user_2_pass = 'password'

        session.flush()
        sel = self.selenium
        sel.open("")
        sel.click("link=Accounts")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Add ( + )")
        sel.wait_for_page_to_load("30000")
        sel.type("User_user_name", "%s" % user_1_name)
        sel.type("User_display_name", "%s" % user_1_name)
        sel.type("User_email_address", "%s" % user_1_email)
        sel.type("User_password", "%s" % user_1_pass)
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("30000")
        #Test Saved message came up
        self.failUnless(sel.is_text_present("saved"))

        sel.open("users")
        #Test that user 1 is listed as part of users
        self.failUnless(sel.is_text_present("%s" % user_1_name))

        #Add user 2
        sel.click("link=Add ( + )")
        sel.wait_for_page_to_load("30000")
        sel.type("User_user_name", "%s" % user_2_name)
        sel.type("User_display_name", "%s" % user_2_name)
        sel.type("User_email_address", "%s" % user_2_email)
        sel.type("User_password", "%s" % user_2_pass)
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("30000")
        #Test Saved message came up
        self.failUnless(sel.is_text_present("%s saved" % user_2_name))

        sel.open("users")
        #Test that user 2 is listed as part of users
        self.failUnless(sel.is_text_present("%s" % user_2_name))


    def test_disable(self):

        #BEAKER_DISABLE_USER = os.environ.get('BEAKER_TEST_USER_2','disabled')
        user_pass = 'password'
        user_name = 'disabled'
        email = 'disabled@my.com'

        sel = self.selenium
        sel.open("")
        sel.click("link=Accounts")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Add ( + )")
        sel.wait_for_page_to_load("30000")
        sel.type("User_user_name", "%s" % user_name)
        sel.type("User_display_name", "%s" % user_name)
        sel.type("User_email_address", "%s" % email)
        sel.type("User_password", "%s" % user_pass)
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("30000")
        #Test Saved message came up
        self.failUnless(sel.is_text_present("saved"))
        self.logout()

        # First verify you can login as user.
        self.login(user=user_name, password=user_pass)
        self.logout()

        # Login as admin and disable user TEST 1
        self.login()
        sel.open("")
        sel.click("link=Accounts")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % user_name)
        sel.wait_for_page_to_load("30000")
        sel.click("User_disabled")
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("30000")
        self.logout()

        # Try and login as Disabled User
        self.login(user=user_name, password=user_pass)
        self.failUnless(sel.is_text_present("The credentials you supplied were not correct or did not grant access to this resource" ))


    def tearDown(self):
        self.selenium.stop()

if __name__ == "__main__":
    unittest.main()
