from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import Job
from turbogears.database import session


class MaxWhiteboard(SeleniumTestCase):

    @classmethod
    @with_transaction
    def setupClass(cls):
        max = Job.max_by_whiteboard
        c = 0
        cls.whiteboard =u'whiteboard'
        while c <= max:
            data_setup.create_completed_job(whiteboard=cls.whiteboard)
            c += 1
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    def test_max_whiteboard(self):
        sel = self.selenium
        sel.open('matrix')
        sel.select("remote_form_whiteboard", "label=%s" % self.whiteboard )
        sel.click("//option[@value='%s']" % self.whiteboard)
        sel.click("//input[@value='Generate']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("exact:Pass: %s" % Job.max_by_whiteboard))
        self.failUnless(sel.is_text_present("Your whiteboard contains 21 jobs, only %s will be used" % Job.max_by_whiteboard))

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()


