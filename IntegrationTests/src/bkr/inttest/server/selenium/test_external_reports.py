from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import get_server_base

class ExternalReportTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def _insert(self, b, name, url, description):
        b.get(get_server_base() + 'reports/external/new')
        b.find_element_by_name('name').send_keys(name)
        b.find_element_by_name('url').send_keys(url)
        b.find_element_by_name('description').send_keys(description)
        b.find_element_by_id('form').submit()

    def test_insert(self):
        b = self.browser
        login(b)
        self._insert(b, 'New Report', 'http://blah.com', 'Description is this')
        b.find_element_by_xpath('//h2[text()="External Reports"]')
        self.assertEquals(b.find_element_by_class_name('flash').text, 'New Report saved')
        # Check the following element exists
        b.find_element_by_xpath("//div[@class='external-report']/h3/a[text()='New Report']")

    def test_can_delete(self):
        b = self.browser
        login(b)
        self._insert(b, 'ToDelete', 'http://unique1', 'UniqueDescription1')
        delete_link =  b.find_element_by_xpath("//div[@class='external-report']/form[preceding-sibling::h3/a[text()='ToDelete']]/a[text()='Delete ( - )']")
        delete_link.click()
        b.find_element_by_xpath("//button[@type='button' and text()='Yes']").click()
        page_text = b.find_element_by_xpath('//body').text
        # This should cover determining if the report is really gone
        self.assertTrue('UniqueDescription1' not in page_text)
        b.find_element_by_xpath('//h2[text()="External Reports"]')
        self.assertEquals(b.find_element_by_class_name('flash').text, 'Deleted report ToDelete')

    def test_can_edit(self):
        b = self.browser
        login(b)
        self._insert(b, 'Report1', 'http://blag.com', '')
        edit_link =  b.find_element_by_xpath("//div[@class='external-report']/a[text()='Edit' and preceding-sibling::h3/a[text()='Report1']]")
        edit_link.click()
        b.find_element_by_name('description').send_keys('A description')
        b.find_element_by_id('form').submit()
        b.find_element_by_xpath("//div[@class='external-report']/p[normalize-space(text())='A description' and preceding-sibling::h3/a[text()='Report1']]")
