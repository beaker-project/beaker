from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import is_text_present, login
from bkr.inttest import data_setup, get_server_base
from turbogears.database import session


class Cancel(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.password = 'password'
            self.user = data_setup.create_user(password=self.password)
            self.job = data_setup.create_job(owner=self.user)
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_cancel_recipeset_group_job(self):
        b = self.browser
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user(password='password')
            user.groups.append(group)
            self.job.group = group
        login(b, user.user_name, 'password')
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="recipeset"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled recipeset %s"
            % self.job.recipesets[0].id))

    def test_cancel_group_job(self):
        b = self.browser
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user(password='password')
            user.groups.append(group)
            self.job.group = group
        login(b, user.user_name, 'password')
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="job-action-container"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled job %s"
            % self.job.id))

    def test_owner_cancel_job(self):
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="job-action-container"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled job %s"
            % self.job.id))

    def test_owner_cancel_recipeset(self):
        b = self.browser
        login(b, self.user.user_name, self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_xpath('//div[@class="recipeset"]//a[text()="Cancel"]').click()
        b.find_element_by_xpath("//input[@value='Yes']").click()
        self.assertTrue(is_text_present(b, "Successfully cancelled recipeset %s"
            % self.job.recipesets[0].id))
