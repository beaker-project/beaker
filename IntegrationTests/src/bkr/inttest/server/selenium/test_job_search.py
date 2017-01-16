
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import wait_for_animation, \
    check_job_search_results
from bkr.inttest import data_setup, with_transaction, get_server_base
from turbogears.database import session
from bkr.server.model import Product, RetentionTag

class SearchJobsWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.running_job = data_setup.create_job()
            self.queued_job = data_setup.create_job()
            self.completed_job = data_setup.create_completed_job()
            data_setup.mark_job_queued(self.queued_job)
            data_setup.mark_job_running(self.running_job)
        self.browser = self.get_browser()

    def test_search_group(self):
        with session.begin():
            group = data_setup.create_group()
            whiteboard = data_setup.unique_name(u'whiteboard%s')
            job = data_setup.create_job(group=group, whiteboard=whiteboard)
            job2 = data_setup.create_job(whiteboard=whiteboard)

        b = self.browser
        # Ensures that both jobs are present
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Whiteboard']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='jobsearch_0_value']"). \
            send_keys(whiteboard)
        b.find_element_by_id('searchform').submit()
        check_job_search_results(b, present=[job, job2])

        # Now do the actual test
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Group']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='jobsearch_0_value']").clear()
        b.find_element_by_xpath("//input[@id='jobsearch_0_value']"). \
            send_keys(job.group.group_name)
        b.find_element_by_id('searchform').submit()
        check_job_search_results(b, present=[job], absent=[job2])

    def test_search_tag(self):
        with session.begin():
            my_job = data_setup.create_job()
            new_tag = RetentionTag(tag=data_setup.unique_name('mytag%s'))
            my_job.retention_tag = new_tag
        b = self.browser

        # Test with tag.
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Tag']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_value']/"
            "option[normalize-space(text())='%s']" % new_tag.tag).click()
        b.find_element_by_id('searchform').submit()
        job_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_('J:%s' % my_job.id in job_search_result)


    def test_search_product(self):
        with session.begin():
            my_job = data_setup.create_job()
            new_product = Product(name=data_setup.unique_name('myproduct%s'))
            my_job.product = new_product
        b = self.browser

        # Test with product.
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Product']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_value']/"
            "option[normalize-space(text())='%s']" % new_product.name).click()
        b.find_element_by_id('searchform').submit()
        job_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_('J:%s' % my_job.id in job_search_result)

        with session.begin():
            my_job.product = None

        # Test without product
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Product']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_value']/"
            "option[normalize-space(text())='None']").click()

        b.find_element_by_link_text('Add').click()

        b.find_element_by_xpath("//select[@id='jobsearch_1_table'] \
            /option[@value='Id']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_1_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='jobsearch_1_value']"). \
            send_keys(str(my_job.id))
        b.find_element_by_id('searchform').submit()
        job_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text

        self.assert_('J:%s' % my_job.id in job_search_result)

    def test_search_email(self):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Owner/Email']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]'). \
            send_keys(self.running_job.owner.email_address)
        b.find_element_by_id('searchform').submit()
        job_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_('J:%s' % self.running_job.id in job_search_result)

    def test_search_owner(self):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_table'] \
            /option[@value='Owner/Username']").click()
        b.find_element_by_xpath("//select[@id='jobsearch_0_operation'] \
            /option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="jobsearch_0_value"]'). \
            send_keys(self.running_job.owner.user_name)
        b.find_element_by_id('searchform').submit()
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

    def test_simple_search(self):
        with session.begin():
            group = data_setup.create_group()
            whiteboard = data_setup.unique_name(u'default_search%s')
            job = data_setup.create_job(whiteboard=whiteboard)

        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_xpath("//form[@id='simpleform']/input").\
            send_keys("default_search")
        b.find_element_by_xpath("//form[@id='simpleform']/button[text()='Search']").click()
        whiteboard_search = b.find_element_by_xpath("//table[@id='widget']/tbody/tr[1]/td[2]").text
        self.assertEqual(whiteboard_search, whiteboard)

    def test_search_id_if_text_starts_with_job_prefix(self):
        with session.begin():
            job = data_setup.create_job()
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_xpath("//form[@id='simpleform']/input").\
            send_keys(job.t_id)
        b.find_element_by_xpath("//form[@id='simpleform']/button[text()='Search']").click()
        id_search = b.find_element_by_xpath("//table[@id='widget']/tbody/tr[1]/td[2]").text
        self.assertEqual(job.whiteboard, id_search)


