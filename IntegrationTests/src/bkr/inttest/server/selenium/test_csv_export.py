
# vim: set fileencoding=utf-8 :

from turbogears.database import session
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.server.model import Provision, ProvisionFamily, ProvisionFamilyUpdate
import csv
import requests

class CSVExportTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def get_csv(self, csv_type):
        self.click_submenu_item('Reports', 'CSV')
        b = self.browser
        b.find_element_by_xpath('//input[@name="csv_type" and @value="%s"]' % csv_type).click()
        # XXX We can't actually submit the form here, because the browser will 
        # show us a download dialog which WebDriver can't handle. So we just 
        # fetch it directly instead, re-using the browser's session cookies.
        url = get_server_base() + ('csv/action_export?csv_type=%s' % csv_type)
        cookies = dict((cookie['name'], cookie['value']) for cookie in b.get_cookies())
        request = requests.get(url, cookies=cookies)
        request.raise_for_status()
        return request.raw

    # https://bugzilla.redhat.com/show_bug.cgi?id=747767
    def test_export_install_options(self):
        system = data_setup.create_system(arch=u'i386')
        distro = data_setup.create_distro(arch=u'i386')
        system.provisions[distro.arch] = Provision(
                arch=distro.arch, ks_meta=u'some_ks_meta_var=1',
                kernel_options=u'some_kernel_option=1',
                kernel_options_post=u'some_kernel_option=2')
        system.provisions[distro.arch]\
            .provision_families[distro.osversion.osmajor] = \
                ProvisionFamily(osmajor=distro.osversion.osmajor,
                    ks_meta=u'some_ks_meta_var=2', kernel_options=u'some_kernel_option=3',
                    kernel_options_post=u'some_kernel_option=4')
        system.provisions[distro.arch]\
            .provision_families[distro.osversion.osmajor]\
            .provision_family_updates[distro.osversion] = \
                ProvisionFamilyUpdate(osversion=distro.osversion,
                    ks_meta=u'some_ks_meta_var=3', kernel_options=u'some_kernel_option=5',
                    kernel_options_post=u'some_kernel_option=6')
        session.flush()

        self.login()
        csv_request = self.get_csv('install')
        csv_rows = [row for row in csv.DictReader(csv_request) if row['fqdn'] == system.fqdn]
        self.assertEquals(csv_rows[0]['arch'], 'i386')
        self.assertEquals(csv_rows[0]['family'], '')
        self.assertEquals(csv_rows[0]['update'], '')
        self.assertEquals(csv_rows[0]['ks_meta'], 'some_ks_meta_var=1')
        self.assertEquals(csv_rows[0]['kernel_options'], 'some_kernel_option=1')
        self.assertEquals(csv_rows[0]['kernel_options_post'], 'some_kernel_option=2')
        self.assertEquals(csv_rows[1]['arch'], 'i386')
        self.assertEquals(csv_rows[1]['family'], unicode(distro.osversion.osmajor))
        self.assertEquals(csv_rows[1]['update'], '')
        self.assertEquals(csv_rows[1]['ks_meta'], 'some_ks_meta_var=2')
        self.assertEquals(csv_rows[1]['kernel_options'], 'some_kernel_option=3')
        self.assertEquals(csv_rows[1]['kernel_options_post'], 'some_kernel_option=4')
        self.assertEquals(csv_rows[2]['arch'], 'i386')
        self.assertEquals(csv_rows[2]['family'], unicode(distro.osversion.osmajor))
        self.assertEquals(csv_rows[2]['update'], unicode(distro.osversion.osminor))
        self.assertEquals(csv_rows[2]['ks_meta'], 'some_ks_meta_var=3')
        self.assertEquals(csv_rows[2]['kernel_options'], 'some_kernel_option=5')
        self.assertEquals(csv_rows[2]['kernel_options_post'], 'some_kernel_option=6')

    def test_export_install_options_with_null_options(self):
        system = data_setup.create_system(arch=u'i386')
        distro = data_setup.create_distro(arch=u'i386')
        system.provisions[distro.arch] = Provision(
                arch=distro.arch, ks_meta=u'some_ks_meta_var=3',
                kernel_options=None, kernel_options_post=None)
        system.provisions[distro.arch]\
            .provision_families[distro.osversion.osmajor] = \
                ProvisionFamily(osmajor=distro.osversion.osmajor,
                    ks_meta=None, kernel_options=u'some_kernel_option=7',
                    kernel_options_post=None)
        system.provisions[distro.arch]\
            .provision_families[distro.osversion.osmajor]\
            .provision_family_updates[distro.osversion] = \
                ProvisionFamilyUpdate(osversion=distro.osversion,
                    ks_meta=None, kernel_options=None,
                    kernel_options_post=u'some_kernel_option=8')
        session.flush()

        self.login()
        csv_request = self.get_csv('install')
        csv_rows = [row for row in csv.DictReader(csv_request) if row['fqdn'] == system.fqdn]
        self.assertEquals(csv_rows[0]['arch'], 'i386')
        self.assertEquals(csv_rows[0]['family'], '')
        self.assertEquals(csv_rows[0]['update'], '')
        self.assertEquals(csv_rows[0]['ks_meta'], 'some_ks_meta_var=3')
        self.assertEquals(csv_rows[0]['kernel_options'], '')
        self.assertEquals(csv_rows[0]['kernel_options_post'], '')
        self.assertEquals(csv_rows[1]['arch'], 'i386')
        self.assertEquals(csv_rows[1]['family'], unicode(distro.osversion.osmajor))
        self.assertEquals(csv_rows[1]['update'], '')
        self.assertEquals(csv_rows[1]['ks_meta'], '')
        self.assertEquals(csv_rows[1]['kernel_options'], 'some_kernel_option=7')
        self.assertEquals(csv_rows[1]['kernel_options_post'], '')
        self.assertEquals(csv_rows[2]['arch'], 'i386')
        self.assertEquals(csv_rows[2]['family'], unicode(distro.osversion.osmajor))
        self.assertEquals(csv_rows[2]['update'], unicode(distro.osversion.osminor))
        self.assertEquals(csv_rows[2]['ks_meta'], '')
        self.assertEquals(csv_rows[2]['kernel_options'], '')
        self.assertEquals(csv_rows[2]['kernel_options_post'], 'some_kernel_option=8')

    def test_export_systems_unicode(self):
        system = data_setup.create_system(lender=u'Möbius')
        session.flush()
        self.login()
        csv_request = self.get_csv('system')
        csv_rows = [row for row in csv.DictReader(csv_request) if row['fqdn'] == system.fqdn]
        self.assertEquals(csv_rows[0]['lender'].decode('utf8'), u'Möbius')
