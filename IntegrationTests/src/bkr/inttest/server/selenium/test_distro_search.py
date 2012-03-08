#!/usr/bin/python
from selenium.webdriver.support.ui import Select
from bkr.server.model import LabControllerDistro
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import get_server_base, is_text_present
from bkr.inttest import data_setup
from turbogears.database import session

class Search(WebDriverTestCase):
    
    @classmethod
    def setupClass(cls):
        cls.distro_one_name = data_setup.unique_name(u'nametest%s')
        cls.distro_one_breed = u'breedtest1'
        cls.distro_one_osmajor = u'osmajortest1'
        cls.distro_one_osminor = u'1'
        cls.distro_one_virt = True
        cls.distro_one_arch = u'ia64'
        cls.distro_one_tags = None

        cls.distro_one = data_setup.create_distro(name=cls.distro_one_name, breed=cls.distro_one_breed,
            osmajor=cls.distro_one_osmajor, osminor = cls.distro_one_osminor,
            arch=cls.distro_one_arch, virt=cls.distro_one_virt,
            tags =cls.distro_one_tags)


        cls.distro_two_name = data_setup.unique_name(u'nametest%s')
        cls.distro_two_breed = u'breedtest2'
        cls.distro_two_osmajor = u'osmajortest2'
        cls.distro_two_osminor = u'2'
        cls.distro_two_virt = True
        cls.distro_two_arch = u'i386'
        cls.distro_two_tags = None

        cls.distro_two = data_setup.create_distro(name=cls.distro_two_name, breed=cls.distro_two_breed,
            osmajor=cls.distro_two_osmajor, osminor = cls.distro_two_osminor,
            arch=cls.distro_two_arch, virt=cls.distro_two_virt,
            tags =cls.distro_two_tags)

        cls.distro_three_name = data_setup.unique_name(u'nametest%s')
        cls.distro_three_breed = u'breedtest3'
        cls.distro_three_osmajor = u'osmajortest3'
        cls.distro_three_osminor = u'3'
        cls.distro_three_virt = False
        cls.distro_three_arch = u's390'
        cls.distro_three_tags = None

        cls.distro_three = data_setup.create_distro(name=cls.distro_three_name, breed=cls.distro_three_breed,
            osmajor=cls.distro_three_osmajor, osminor = cls.distro_three_osminor,
            arch=cls.distro_three_arch, virt=cls.distro_three_virt,
            tags =cls.distro_three_tags)
        session.flush()
        cls.browser = cls.get_browser()

    def test_correct_items_count(self):
        lc_1 = data_setup.create_labcontroller()
        lc_2 = data_setup.create_labcontroller()
        distro_name = data_setup.unique_name(u'distroname%s')
        distro_breed = data_setup.unique_name(u'distrobreed%s')
        distro_osmajor = data_setup.unique_name(u'osmajor%s')
        distro_osminor = u'2'
        distro_virt = True
        distro_arch = u'i386'
        distro_tags = None

        distro = data_setup.create_distro(name=distro_name, breed=distro_breed,
            osmajor=distro_osmajor, osminor=distro_osminor,
            arch=distro_arch, virt=distro_virt,
            tags=distro_tags)
        session.flush()
        distro.lab_controller_assocs[:] = [LabControllerDistro(lab_controller=lc_1), LabControllerDistro(lab_controller=lc_2)]

        b = self.browser
        b.get(get_server_base() + 'distros')
        b.find_element_by_name('simplesearch').send_keys(distro.name)
        b.find_element_by_name('search').click()
        self.assert_(is_text_present(b, 'Items found: 1'))

    def test_distro_search(self):
        b = self.browser
        """
        SimpleSearch
        START
        """
        b.get(get_server_base() + 'distros')
        b.find_element_by_name('simplesearch').send_keys(self.distro_one.name)
        b.find_element_by_name('search').click()
        distro_search_result = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_(self.distro_one.name in distro_search_result)
        self.assert_(self.distro_two.name not in distro_search_result)
        self.assert_(self.distro_three.name not in distro_search_result)
        """
        END
        """
        """
        Arch -> is -> ia64
        START
        """
        b.find_element_by_id('advancedsearch').click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='Arch']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="distrosearch_0_value"]').send_keys(self.distro_one_arch)
        b.find_element_by_name('Search').click()
        distro_search_result_2 = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_(self.distro_one.name in distro_search_result_2)
        self.assert_(self.distro_two.name not in distro_search_result_2)
        self.assert_(self.distro_three.name not in distro_search_result_2)
        """
        END
        """
        """
        Arch -> is -> i386
        START
        """
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='Arch']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is']").click()
        b.find_element_by_name('distrosearch-0.value').clear()
        b.find_element_by_name('distrosearch-0.value').send_keys(self.distro_two_arch)
        b.find_element_by_name('Search').click()
        distro_search_result_3 = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_(self.distro_two.name in distro_search_result_3) 
        self.assert_(self.distro_one.name not in distro_search_result_3) 
        self.assert_(self.distro_three.name not in distro_search_result_3) 
        """
        END
        """
        """
        Arch -> is not -> i386
        START
        """
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='Arch']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is not']").click()
        b.find_element_by_name('distrosearch-0.value').clear()
        b.find_element_by_name('distrosearch-0.value').send_keys(self.distro_two_arch)
        b.find_element_by_name('Search').click()
        distro_search_result_4 = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_(self.distro_one.name in distro_search_result_4)
        self.assert_(self.distro_three.name in distro_search_result_4)
        self.assert_(self.distro_two.name not in distro_search_result_4)
        """
        END
        """
        """
        Breed -> is ->
        START
        """
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='Breed']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is']").click()
        b.find_element_by_name('distrosearch-0.value').clear()
        b.find_element_by_name('distrosearch-0.value').send_keys('%s' % self.distro_one.breed)
        b.find_element_by_name('Search').click()
        distro_search_result_5 = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_(self.distro_one.name in distro_search_result_5)
        self.assert_(self.distro_two.name not in distro_search_result_5)
        self.assert_(self.distro_three.name not in distro_search_result_5)
        """
        END
        """
        """
        Virt -> is -> True
        START
        """
        b.find_element_by_xpath("//select[@id='distrosearch_0_table']/option[@value='Virt']").click()
        b.find_element_by_xpath("//select[@id='distrosearch_0_operation']/option[@value='is']").click()
        b.find_element_by_name('distrosearch-0.value').send_keys('True')
        b.find_element_by_name('Search').click()
        distro_search_result_6 = \
            b.find_element_by_xpath('//table[@id="widget"]').text
        self.assert_(self.distro_one.name in distro_search_result_6)
        self.assert_(self.distro_two.name in distro_search_result_6)
        self.assert_(self.distro_three.name not in distro_search_result_6)
        """
        END
        """

    @classmethod
    def teardownClass(cls):
        cls.browser.quit()


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
                .select_by_visible_text('Arch')
        Select(b.find_element_by_name('distrosearch-0.operation'))\
                .select_by_visible_text('is not')
        b.find_element_by_name('distrosearch-0.value').send_keys('x86_64')
        b.find_element_by_xpath('//form[@name="distrosearch"]//input[@type="submit"]').click()

        self.assertEquals(Select(b.find_element_by_name('distrosearch-0.table'))
                .first_selected_option.text,
                'Arch')
        self.assertEquals(Select(b.find_element_by_name('distrosearch-0.operation'))
                .first_selected_option.text,
                'is not')
        self.assertEquals(b.find_element_by_name('distrosearch-0.value')
                .get_attribute('value'),
                'x86_64')
