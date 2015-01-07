
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from bkr.server.model import session, OSMajor, Arch

def go_to_edit_osmajor(browser, osmajor_name):
    browser.get(get_server_base() + 'osversions')
    browser.find_element_by_name('osversion.text').send_keys(osmajor_name)
    browser.find_element_by_xpath('//form[@id="Search"]').submit()
    browser.find_element_by_xpath('//table[@id="widget"]/tbody/tr[1]'
            '/td[1]/a[text()="%s"]' % osmajor_name).click()

class OSVersionsTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    # https://bugzilla.redhat.com/show_bug.cgi?id=972397
    def test_sort_grid_doesnt_blow_up(self):
        b = self.browser
        b.get(get_server_base() + 'osversions/')
        b.find_element_by_xpath("//th/a[normalize-space(text())='Alias']").click()
        b.find_element_by_xpath("//title[text()='OS Versions']")

    # https://bugzilla.redhat.com/show_bug.cgi?id=860870
    def test_displayalphaos(self):
        with session.begin():
            data_setup.create_distro(osmajor=u'LinuxLinux1.1')
        b = self.browser
        b.get(get_server_base() + 'osversions')
        b.find_element_by_link_text('L').click()
        self.assert_(b.find_elements_by_link_text('LinuxLinux1.1'))

    def test_edit_osmajor_install_options(self):
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'LinuxLinux2.1', arch=u'ia64')
            data_setup.create_distro_tree(osmajor=u'LinuxLinux2.1', arch=u'ppc64')
        b = self.browser
        # set them from scratch
        go_to_edit_osmajor(b, 'LinuxLinux2.1')
        b.find_element_by_xpath('//*[@id="install_options_all"]'
                '//div[normalize-space(label/text())="Kickstart Metadata"]'
                '//input').send_keys('one')
        b.find_element_by_xpath('//*[@id="install_options_all"]'
                '//div[normalize-space(label/text())="Kernel Options"]'
                '//input').send_keys('two')
        b.find_element_by_xpath('//*[@id="install_options_all"]'
                '//div[normalize-space(label/text())="Kernel Options Post"]'
                '//input').send_keys('three')
        b.find_element_by_xpath('//*[@id="install_options_ppc64"]'
                '//div[normalize-space(label/text())="Kickstart Metadata"]'
                '//input').send_keys('four')
        b.find_element_by_xpath('//*[@id="install_options_ppc64"]'
                '//div[normalize-space(label/text())="Kernel Options"]'
                '//input').send_keys('five')
        b.find_element_by_xpath('//*[@id="install_options_ppc64"]'
                '//div[normalize-space(label/text())="Kernel Options Post"]'
                '//input').send_keys('six')
        b.find_element_by_xpath('//button[text()="Save Changes"]').click()
        self.assertEquals(
                b.find_element_by_class_name('flash').text,
                'Install options saved for LinuxLinux2.1')
        # check everything is saved
        with session.begin():
            o = OSMajor.by_name(u'LinuxLinux2.1')
            ia64 = Arch.by_name(u'ia64')
            ppc64 = Arch.by_name(u'ppc64')
            self.assertEquals(set(o.install_options_by_arch.keys()),
                    set([None, ia64, ppc64]),
                    o.install_options_by_arch)
            self.assertEquals(o.install_options_by_arch[None].ks_meta, 'one')
            self.assertEquals(o.install_options_by_arch[None].kernel_options, 'two')
            self.assertEquals(o.install_options_by_arch[None].kernel_options_post, 'three')
            self.assertEquals(o.install_options_by_arch[ia64].ks_meta, '')
            self.assertEquals(o.install_options_by_arch[ia64].kernel_options, '')
            self.assertEquals(o.install_options_by_arch[ia64].kernel_options_post, '')
            self.assertEquals(o.install_options_by_arch[ppc64].ks_meta, 'four')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options, 'five')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options_post, 'six')
        # now edit the existing options
        go_to_edit_osmajor(b, 'LinuxLinux2.1')
        input = b.find_element_by_xpath('//*[@id="install_options_ppc64"]'
                '//div[normalize-space(label/text())="Kickstart Metadata"]'
                '//input')
        self.assertEquals(input.get_attribute('value'), 'four')
        input.clear()
        input.send_keys('something else')
        input = b.find_element_by_xpath('//*[@id="install_options_ppc64"]'
                '//div[normalize-space(label/text())="Kernel Options"]'
                '//input')
        self.assertEquals(input.get_attribute('value'), 'five')
        input.clear()
        input.send_keys('something else')
        input = b.find_element_by_xpath('//*[@id="install_options_ppc64"]'
                '//div[normalize-space(label/text())="Kernel Options Post"]'
                '//input')
        self.assertEquals(input.get_attribute('value'), 'six')
        input.clear()
        input.send_keys('something else')
        b.find_element_by_xpath('//button[text()="Save Changes"]').click()
        self.assertEquals(
                b.find_element_by_class_name('flash').text,
                'Install options saved for LinuxLinux2.1')
        # check they are updated
        with session.begin():
            session.expunge_all()
            o = OSMajor.by_name(u'LinuxLinux2.1')
            ppc64 = Arch.by_name(u'ppc64')
            self.assertEquals(o.install_options_by_arch[ppc64].ks_meta,
                    'something else')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options,
                    'something else')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options_post,
                    'something else')

    #https://bugzilla.redhat.com/show_bug.cgi?id=975644
    def test_edit_osmajor_alias(self):
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'LinuxLinux2.1', arch=u'ia64')

        b = self.browser
        go_to_edit_osmajor(b, 'LinuxLinux2.1')
        b.find_element_by_xpath('//input[@id="form_alias"]').send_keys('linux21')
        b.find_element_by_xpath('//button[text()="Edit OSMajor"]').submit()
        self.assertEquals(
            b.find_element_by_class_name('flash').text,
            'Changes saved for LinuxLinux2.1')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173362
    def test_cannot_save_duplicate_alias(self):
        with session.begin():
            existing = u'OrangeBucketLinux7'
            existing_alias = u'OBL7'
            OSMajor.lazy_create(osmajor=existing).alias = existing_alias
            data_setup.create_distro_tree(osmajor=u'YellowSpaceshipLinux1')
        b = self.browser
        go_to_edit_osmajor(b, 'YellowSpaceshipLinux1')
        b.find_element_by_xpath('//input[@id="form_alias"]')\
                .send_keys(existing_alias)
        b.find_element_by_xpath('//button[text()="Edit OSMajor"]').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Cannot save alias OBL7, it is already used by OrangeBucketLinux7')
        go_to_edit_osmajor(b, 'YellowSpaceshipLinux1')
        b.find_element_by_xpath('//input[@id="form_alias"]')\
                .send_keys(existing)
        b.find_element_by_xpath('//button[text()="Edit OSMajor"]').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Cannot save alias OrangeBucketLinux7, '
                'it is already used by OrangeBucketLinux7')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173362
    def test_clearing_alias_stores_null(self):
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'YellowSpaceshipLinux2')
            osmajor = OSMajor.by_name(u'YellowSpaceshipLinux2')
            osmajor.alias = u'YSL2'
        b = self.browser
        go_to_edit_osmajor(b, 'YellowSpaceshipLinux2')
        b.find_element_by_xpath('//input[@id="form_alias"]').clear()
        b.find_element_by_xpath('//button[text()="Edit OSMajor"]').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Changes saved for YellowSpaceshipLinux2')
        with session.begin():
            session.refresh(osmajor)
            self.assertEquals(osmajor.alias, None) # not ''
