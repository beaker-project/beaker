
from turbogears.database import session
from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup
from bkr.server.model import User, DistroActivity, SystemActivity

class JobAckTest(SeleniumTestCase):
    
    @classmethod
    def setupClass(cls):
        cls.password = 'password'
        cls.user_1 = data_setup.create_user(password=cls.password)
        cls.user_2 = data_setup.create_user(password=cls.password)
        cls.job = data_setup.create_completed_job(owner=cls.user_1)
        cls.group = data_setup.create_group()
        session.flush()
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    def test_ackability(self):
        sel = self.selenium
        try:
            self.logout()
        except Exception:
            pass
        self.login(user=self.user_1, password=self.password)
        sel.open('jobs/%s' % self.job.id)
        sel.wait_for_page_to_load('3000')
        sel.click("widget_1") #This tests that the ack is there for owner

        try:
            self.logout()
        except Exception:
            pass
        self.login(user=self.user_2, password=self.password)
        sel.open('jobs/%s' % self.job.id)
        sel.wait_for_page_to_load('3000')
        try:
            sel.click("widget_1") #Tests that it's not available for non owner
            raise AssertionError('Non owner and non group membetr can ack')
        except Exception:
            pass

        data_setup.add_user_to_group(self.user_1,self.group)
        data_setup.add_user_to_group(self.user_2,self.group)
        session.flush()
        sel.open('jobs/%s' % self.job.id)
        sel.wait_for_page_to_load('3000')
        sel.click("widget_1") #This tests that the ack is there group memeber


    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()

