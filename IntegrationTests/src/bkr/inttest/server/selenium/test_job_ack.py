from nose.plugins.skip import SkipTest
from turbogears.database import session
from bkr.inttest import get_server_base, stop_process, start_process, \
    edit_file, CONFIG_FILE
from bkr.inttest.server.webdriver_utils import login, logout
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup


class JobAckTest(WebDriverTestCase):

    @classmethod
    def setupClass(cls):
        cls.password = 'password'
        with session.begin():
            cls.user_1 = data_setup.create_user(password=cls.password)
            cls.user_2 = data_setup.create_user(password=cls.password)
            cls.user_3 = data_setup.create_user(password=cls.password)
            cls.job = data_setup.create_completed_job(owner=cls.user_1)
            cls.group = data_setup.create_group()
        cls.browser = cls.get_browser()

    @classmethod
    def teardownClass(cls):
        cls.browser.quit()

    def test_ackability(self):
        # XXX If this test gets any more complicated, we should break
        # it up
        b = self.browser
        login(b, user=self.user_1.user_name, password=self.password)
        b.get(get_server_base() + 'jobs/%d' % self.job.id)
         #This tests that the ack is there for owner
        b.find_element_by_name("response_box_%d" % self.job.recipesets[0].id)
        logout(b)
        # Not there for non owner
        login(b, user=self.user_2.user_name, password=self.password)
        b.get(get_server_base() + 'jobs/%d' % self.job.id)
        b.find_element_by_xpath("//td[normalize-space(text())='RS:%s' and "
            "not(./input[@name='response_box_%s'])]" % (
            self.job.recipesets[0].id, self.job.recipesets[0].id))
        # Is there for job owner's group co-member.
        with session.begin():
            data_setup.add_user_to_group(self.user_1, self.group)
            data_setup.add_user_to_group(self.user_3, self.group)
        logout(b)
        login(b, user=self.user_3.user_name, password=self.password)
        b.get(get_server_base() + 'jobs/%d' % self.job.id)
        b.find_element_by_xpath("//input[@name='response_box_%s']" %
            self.job.recipesets[0].id)

        # There for job's group member
        with session.begin():
            self.job.group = self.group
            self.user_2.groups.append(self.group)
        logout(b)
        login(b, user=self.user_2.user_name, password=self.password)
        b.get(get_server_base() + 'jobs/%s' % self.job.id)
        b.find_element_by_name("response_box_%s" % self.job.recipesets[0].id)

        # XXX This whole block can go away with BZ#1000861
        # This tests that we can't ack the recipeset
        try:
            stop_process('gunicorn')
        except ValueError:
            # It seems gunicorn is not a running process
            raise SkipTest('Can only run this test against gunicorn')
        try:
            tmp_config = edit_file(CONFIG_FILE,
                'beaker.deprecated_job_group_permissions.on = True',
                'beaker.deprecated_job_group_permissions.on = False')
            start_process('gunicorn', env={'BEAKER_CONFIG_FILE': tmp_config.name})

            b.find_element_by_xpath("//td[normalize-space(text())='RS:%s' and "
                "not(./input[@name='response_box_%s'])]" % (
                self.job.recipesets[0].id, self.job.recipesets[0].id))
        finally:
            stop_process('gunicorn')
            start_process('gunicorn')
