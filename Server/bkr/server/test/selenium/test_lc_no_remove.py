from bkr.server.test import selenium
from bkr.server.test import data_setup
from turbogears.database import session

class NoRemove(selenium.SeleniumTestCase):

    @classmethod
    def setupClass(cls):
        data_setup.create_labcontroller()
        session.flush()
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()

    def test_no_remove(self):
        sel = self.selenium
        self.login()
        sel.open('labcontrollers')
        sel.wait_for_page_to_load('3000')
        body_text = sel.get_text('//body')
        self.assert_('Remove' not in body_text)


