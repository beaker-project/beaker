from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session


class SearchJobs(SeleniumTestCase):


    @classmethod
    @with_transaction
    def setUpClass(cls):
        cls.running_job = data_setup.create_job()
        cls.queued_job = data_setup.create_job()
        cls.completed_job = data_setup.create_completed_job()
        data_setup.mark_job_queued(cls.queued_job)
        data_setup.mark_job_running(cls.running_job)
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()

    def test_quick_search(self):
        sel = self.selenium
        sel.open('jobs')
        sel.wait_for_page_to_load("30000")
        # Test Queued and only Queued job is shown
        sel.click("//button[@value='Status-is-Queued']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_text("//table[@id='widget']/tbody/tr[1]/td[1]"),
                'J:%s' % self.queued_job.id)
        queued_table_text = sel.get_text("//table[@id='widget']")
        self.assert_('J:%s' % self.running_job.id not in queued_table_text)
        self.assert_('J:%s' % self.completed_job.id not in queued_table_text)

        # Test Running and only Running job is shown
        sel.click("//button[@value='Status-is-Running']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_text("//table[@id='widget']/tbody/tr[1]/td[1]"),
                'J:%s' % self.running_job.id)
        running_table_text = sel.get_text("//table[@id='widget']")
        self.assert_('J:%s' % self.queued_job.id not in running_table_text)
        self.assert_('J:%s' % self.completed_job.id not in running_table_text)

        # Test Completed and only Completed job is shown
        sel.click("//button[@value='Status-is-Completed']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_text("//table[@id='widget']/tbody/tr[1]/td[1]"),
                'J:%s' % self.completed_job.id)
        completed_table_text = sel.get_text("//table[@id='widget']")
        self.assert_('J:%s' % self.running_job.id not in completed_table_text)
        self.assert_('J:%s' % self.queued_job.id not in completed_table_text)




