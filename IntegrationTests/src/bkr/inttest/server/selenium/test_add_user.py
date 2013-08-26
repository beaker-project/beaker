from turbogears.database import session
from bkr.inttest import get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present, \
        click_menu_item, logout
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
        b.find_element_by_link_text('Add').click()

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
        b.find_element_by_link_text('Add').click()
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
        b.find_element_by_link_text('Add').click()
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

class AddUser(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def tearDown(self):
        self.browser.quit()

    def test_adduser(self):
        user_1_name = data_setup.unique_name('anonymous%s')
        user_1_email = data_setup.unique_name('anonymous%s@my.com')
        user_1_pass = 'password'

        user_2_name = data_setup.unique_name('anonymous%s')
        user_2_email = data_setup.unique_name('anonymous%s@my.com')
        user_2_pass = 'password'

        b = self.browser
        b.get(get_server_base())
        click_menu_item(b, 'Admin', 'Accounts')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('user_name').send_keys(user_1_name)
        b.find_element_by_name('display_name').send_keys(user_1_name)
        b.find_element_by_name('email_address').send_keys(user_1_email)
        b.find_element_by_name('password').send_keys(user_1_pass)
        b.find_element_by_id('User').submit()
        #Test Saved message came up
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s saved' % user_1_name)

        b.get(get_server_base() + 'users')
        #Test that user 1 is listed as part of users
        self.failUnless(is_text_present(b, user_1_name))

        #Add user 2
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('user_name').send_keys(user_2_name)
        b.find_element_by_name('display_name').send_keys(user_2_name)
        b.find_element_by_name('email_address').send_keys(user_2_email)
        b.find_element_by_name('password').send_keys(user_2_pass)
        b.find_element_by_id('User').submit()
        #Test Saved message came up
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s saved' % user_2_name)

        b.get(get_server_base() + 'users')
        #Test that user 2 is listed as part of users
        self.failUnless(is_text_present(b, user_2_name))


    def test_disable(self):
        user_pass = 'password'
        user_name = 'disabled'
        email = 'disabled@my.com'

        b = self.browser
        b.get(get_server_base())
        click_menu_item(b, 'Admin', 'Accounts')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('user_name').send_keys(user_name)
        b.find_element_by_name('display_name').send_keys(user_name)
        b.find_element_by_name('email_address').send_keys(email)
        b.find_element_by_name('password').send_keys(user_pass)
        b.find_element_by_id('User').submit()
        #Test Saved message came up
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s saved' % user_name)
        logout(b)

        # First verify you can login as user.
        login(b, user=user_name, password=user_pass)
        logout(b)

        # Login as admin and disable user TEST 1
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Admin', 'Accounts')
        b.find_element_by_link_text(user_name).click()
        b.find_element_by_name('disabled').click()
        b.find_element_by_id('User').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s saved' % user_name)
        logout(b)

        # Try and login as Disabled User
        login(b, user=user_name, password=user_pass)
        self.failUnless(is_text_present(b, "The credentials you supplied were not correct or did not grant access to this resource" ))
