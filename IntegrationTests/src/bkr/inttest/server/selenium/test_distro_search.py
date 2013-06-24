#!/usr/bin/python
from datetime import datetime, timedelta
from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import get_server_base, is_text_present, \
        wait_for_animation
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session


class Search(WebDriverTestCase):
    
    @classmethod
    @with_transaction
    def setupClass(cls):
        # Each distro needs to have a tree in some lab controller, otherwise it 
        # won't show up in search results.
        data_setup.create_labcontroller()

        cls.distro_one_name = data_setup.unique_name(u'nametest%s')
        cls.distro_one_osmajor = u'osmajortest1'
        cls.distro_one_osminor = u'1'
        cls.distro_one_tags = None

        cls.distro_one = data_setup.create_distro(name=cls.distro_one_name,
            osmajor=cls.distro_one_osmajor, osminor = cls.distro_one_osminor,
            tags =cls.distro_one_tags)
        data_setup.create_distro_tree(distro=cls.distro_one)
        # Two days in the future
        cls.distro_one.date_created = datetime.utcnow() + timedelta(days=2)
        cls.distro_two_name = data_setup.unique_name(u'nametest%s')
        cls.distro_two_osmajor = u'osmajortest2'
        cls.distro_two_osminor = u'2'
        cls.distro_two_tags = None

        cls.distro_two = data_setup.create_distro(name=cls.distro_two_name,
            osmajor=cls.distro_two_osmajor, osminor = cls.distro_two_osminor,
            tags =cls.distro_two_tags)
        data_setup.create_distro_tree(distro=cls.distro_two)

        cls.distro_three_name = data_setup.unique_name(u'nametest%s')
        cls.distro_three_osmajor = u'osmajortest3'
        cls.distro_three_osminor = u'3'
        cls.distro_three_tags = None

        cls.distro_three = data_setup.create_distro(name=cls.distro_three_name,
            osmajor=cls.distro_three_osmajor, osminor = cls.distro_three_osminor,
            tags =cls.distro_three_tags)
        data_setup.create_distro_tree(distro=cls.distro_three)

    def setUp(self):
        self.browser = self.get_browser()

    # https://bugzilla.redhat.com/show_bug.cgi?id=972397
    def test_sort_grid_doesnt_blow_up(self):
        b = self.browser
        b.get(get_server_base() + 'distros/')
        # See if they blow up (They shouldn't)
        b.find_element_by_xpath("//a[@class='head_list' and normalize-space(text())='OS Major Version']").click()
        b.find_element_by_xpath("//a[@class='head_list' and normalize-space(text())='OS Minor Version']").click()
        b.find_element_by_xpath("//title[text()='Distros']")

    def test_correct_items_count(self):
        with session.begin():
            lc_1 = data_setup.create_labcontroller()
            lc_2 = data_setup.create_labcontroller()
            distro_name = data_setup.unique_name(u'distroname%s')
            distro_osmajor = data_setup.unique_name(u'osmajor%s')
            distro_osminor = u'2'
            distro_tags = None

            distro = data_setup.create_distro(name=distro_name,
                osmajor=distro_osmajor, osminor=distro_osminor,
                tags=distro_tags)
            data_setup.create_distro_tree(distro=distro)

        b = self.browser
        b.get(get_server_base() + 'distros')
        b.find_element_by_name('simplesearch').send_keys(distro.name)
        b.find_element_by_name('search').click()
        self.assert_(is_text_present(b, 'Items found: 1'))

    def check_search_results(self, present, absent):
        for distro in absent:
            self.browser.find_element_by_xpath('//table[@id="widget" and '
                    'not(.//td[1]/a/text()="%s")]' % distro.id)
        for distro in present:
            self.browser.find_element_by_xpath('//table[@id="widget" and '
                    './/td[1]/a/text()="%s"]' % distro.id)

    def test_simple_search(self):
        b = self.browser
        b.get(get_server_base() + 'distros')
        b.find_element_by_name('simplesearch').send_keys(self.distro_one.name)
        b.find_element_by_name('search').click()
        self.check_search_results(present=[self.distro_one],
                absent=[self.distro_two, self.distro_three])

    def test_search_by_osmajor(self):
        b = self.browser
        b.get(get_server_base() + 'distros')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='OSMajor']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').clear()
        # This also tests that whitespace does not foil us
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').send_keys('  osmajortest1 ')
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_one],
                absent=[self.distro_two, self.distro_three])

    def test_search_by_osminor(self):
        b = self.browser
        b.get(get_server_base() + 'distros')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='OSMinor']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').send_keys('1')
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_one],
                absent=[self.distro_two, self.distro_three])

    def test_search_by_created(self):
        b = self.browser
        b.get(get_server_base() + 'distros')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='Created']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='after']").click()
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').clear()
        now_and_1 = datetime.utcnow() + timedelta(days=1)
        now_and_1_string = now_and_1.strftime('%Y-%m-%d')
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').send_keys(now_and_1_string)
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_one],
                absent=[self.distro_two, self.distro_three])

    def tearDown(self):
        self.browser.quit()


class SearchOptionsTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=770109
    def test_search_options_are_maintained_after_submitting(self):
        b = self.browser
        b.get(get_server_base() + 'distros/')
        b.find_element_by_link_text('Toggle Search').click()
        Select(b.find_element_by_name('distrosearch-0.table'))\
                .select_by_visible_text('Name')
        Select(b.find_element_by_name('distrosearch-0.operation'))\
                .select_by_visible_text('is not')
        b.find_element_by_name('distrosearch-0.value').send_keys('RHEL-6.2')
        b.find_element_by_xpath('//form[@name="distrosearch"]//input[@type="submit"]').click()

        self.assertEquals(Select(b.find_element_by_name('distrosearch-0.table'))
                .first_selected_option.text,
                'Name')
        self.assertEquals(Select(b.find_element_by_name('distrosearch-0.operation'))
                .first_selected_option.text,
                'is not')
        self.assertEquals(b.find_element_by_name('distrosearch-0.value')
                .get_attribute('value'),
                'RHEL-6.2')
