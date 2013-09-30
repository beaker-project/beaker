from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import delete_and_confirm, \
    get_server_base, is_text_present, login, wait_for_animation
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session
from bkr.server.model import Group

# XXX Merge into test_jobs.py
class JobDeleteWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.password = 'password'
            self.user = data_setup.create_user(password=self.password)
            self.job_to_delete = data_setup. \
                create_completed_job(owner=self.user)
            self.job_to_delete_2 = data_setup. \
                create_completed_job(owner=self.user)
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_submission_delegate_with_group(self):
        with session.begin():
            group = data_setup.create_group()
            self.job_to_delete.group = group
            self.job_to_delete_2.group = group
        self.test_submission_delegate()

    def test_submission_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.user.submission_delegates[:] = [submission_delegate]
        login(self.browser, submission_delegate.user_name, 'password')
        # Go to the jobs page and search for our job
        job = self.job_to_delete
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text("Show Search Options").click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('jobsearch-0.table'))\
                .select_by_visible_text('Id')
        Select(b.find_element_by_name('jobsearch-0.operation'))\
                .select_by_visible_text('is')
        b.find_element_by_name('jobsearch-0.value').clear()
        b.find_element_by_name('jobsearch-0.value'). \
            send_keys('%s' % job.id)
        b.find_element_by_id('searchform').submit()
        # We are only a submission delegate, not the submitter,
        # check we cannot delete
        action_text = b.find_element_by_xpath("//td[preceding-sibling::td/"
            "a[normalize-space(text())='%s']]/"
            "div[contains(@class, 'job-action-container')]" % job.t_id).text
        self.assertTrue('Delete' not in action_text)
        # Now go to the individual job page to test for the lack
        # of a 'Delete' link
        b.get(get_server_base() + 'jobs/%d' % \
            job.id)
        action_text = b. \
            find_element_by_xpath("//div[contains(@class, 'job-action-container')]").text
        self.assertTrue('Delete' not in action_text)

        # Ok add our delegates as the submitters
        with session.begin():
            self.job_to_delete.submitter = submission_delegate
            self.job_to_delete_2.submitter = submission_delegate
        # Now let's see if we can do some deleting
        self.job_delete_jobpage(self.job_to_delete_2)
        self.job_delete(self.job_to_delete)

    def test_group_job_member(self):
        with session.begin():
            new_user = data_setup.create_user(password='password')
            group = data_setup.create_group()
            new_user.groups.append(group)
            self.job_to_delete.group = group
            self.job_to_delete_2.group = group
        login(self.browser, new_user.user_name, 'password')
        self.job_delete_jobpage(self.job_to_delete_2)
        self.job_delete(self.job_to_delete)

    def test_admin(self):
        login(self.browser)
        self.job_delete(self.job_to_delete)
        self.job_delete_jobpage(self.job_to_delete_2)

    def test_not_admin(self):
        login(self.browser, user=self.user.user_name, password=self.password)
        self.job_delete(self.job_to_delete)
        self.job_delete_jobpage(self.job_to_delete_2)

    def job_delete_jobpage(self, job):
        b = self.browser
        b.get(get_server_base() + 'jobs/%d' % \
            job.id)
        delete_and_confirm(b, "//form[@action='delete_job_page']")
        self.assertTrue(is_text_present(b, "Succesfully deleted J:%s" %
            job.id))

    def job_delete(self, job):
        b = self.browser
        b.get(get_server_base() + 'jobs')
        b.find_element_by_link_text("Show Search Options").click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('jobsearch-0.table'))\
                .select_by_visible_text('Id')
        Select(b.find_element_by_name('jobsearch-0.operation'))\
                .select_by_visible_text('is')
        b.find_element_by_name('jobsearch-0.value').clear()
        b.find_element_by_name('jobsearch-0.value'). \
            send_keys('%s' % job.id)
        b.find_element_by_id('searchform').submit()

        delete_and_confirm(b, "//tr[td/a[normalize-space(text())='%s']]" % job.t_id)
        b.find_element_by_xpath("//table[@id='widget']//"
            "a[not(normalize-space(text())='%s')]" % job.t_id)
        recipe = job.recipesets[0].recipes[0]
        b.get(get_server_base() + 'recipes/%d' % recipe.id)
        warn_text = b.find_element_by_class_name('flash').text
        self.assertTrue('Invalid R:%s, has been deleted' %
            recipe.id in warn_text)
