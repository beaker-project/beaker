from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, with_transaction, get_server_base
from turbogears.database import session

class SearchJobsWD(WebDriverTestCase):


    @classmethod
    @with_transaction
    def setUpClass(cls):
        cls.running_job = data_setup.create_job()
        cls.queued_job = data_setup.create_job()
        cls.completed_job = data_setup.create_completed_job()
        data_setup.mark_job_queued(cls.queued_job)
        data_setup.mark_job_running(cls.running_job)
        cls.browser = cls.get_browser()

    @classmethod
    def teardownClass(cls):
        cls.browser.quit()

    def test_search_email(self):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_id('advancedsearch').click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Owner/Email']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]'). \
            send_keys(self.running_job.owner.email_address)
        b.find_element_by_name('Search').click()
        job_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_('J:%s' % self.running_job.id in job_search_result)

    def test_search_owner(self):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_id('advancedsearch').click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Owner/Username']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]'). \
            send_keys(self.running_job.owner.user_name)
        b.find_element_by_name('Search').click()
        job_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_('J:%s' % self.running_job.id in job_search_result)

    def test_quick_search(self):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_xpath("//button[@value='Status-is-Queued']").click()
        b.find_element_by_xpath("//table[@id='widget']/tbody/tr/td/a[normalize-space(text())='J:%s']" % self.queued_job.id)
        queued_table_text = b.find_element_by_xpath("//table[@id='widget']").text
        self.assert_('J:%s' % self.running_job.id not in queued_table_text)
        self.assert_('J:%s' % self.completed_job.id not in queued_table_text)

        b.get(get_server_base() + 'jobs')
        b.find_element_by_xpath("//button[@value='Status-is-Running']").click()
        b.find_element_by_xpath("//table[@id='widget']/tbody/tr/td/a[normalize-space(text())='J:%s']" % self.running_job.id)
        running_table_text = b.find_element_by_xpath("//table[@id='widget']").text
        self.assert_('J:%s' % self.queued_job.id not in running_table_text)
        self.assert_('J:%s' % self.completed_job.id not in running_table_text)

        b.get(get_server_base() + 'jobs')
        b.find_element_by_xpath("//button[@value='Status-is-Completed']").click()
        b.find_element_by_xpath("//table[@id='widget']/tbody/tr/td/a[normalize-space(text())='J:%s']" % self.completed_job.id)
        completed_table_text = b.find_element_by_xpath("//table[@id='widget']").text
        self.assert_('J:%s' % self.queued_job.id not in completed_table_text)
        self.assert_('J:%s' % self.running_job.id not in completed_table_text)
