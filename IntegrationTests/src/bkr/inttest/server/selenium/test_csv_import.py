#!/usr/bin/python
# vim: set fileencoding=utf-8 :

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.assertions import assert_has_key_with_value
from bkr.server.model import Arch
from turbogears.database import session
import unittest
from tempfile import NamedTemporaryFile

class CSVImportTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def import_csv(self, contents):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'csv/csv_import')
        csv_file = NamedTemporaryFile(prefix=self.__module__)
        csv_file.write(contents)
        csv_file.flush()
        b.find_element_by_name('csv_file').send_keys(csv_file.name)
        b.find_element_by_name('csv_file').submit()

    def test_system(self):
        orig_date_modified = self.system.date_modified
        self.import_csv((u'csv_type,fqdn,location,arch\n'
                u'system,%s,Under my desk,ia64' % self.system.fqdn)
                .encode('utf8'))
        self.failUnless(is_text_present(self.browser, "No Errors"))
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.location, u'Under my desk')
            self.assert_(Arch.by_name(u'ia64') in self.system.arch)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_keyvalue(self):
        orig_date_modified = self.system.date_modified
        self.import_csv((u'csv_type,fqdn,key,key_value,deleted\n'
                u'keyvalue,%s,COMMENT,UTF 8 –,False' % self.system.fqdn)
                .encode('utf8'))
        self.failUnless(is_text_present(self.browser, "No Errors"))
        with session.begin():
            session.refresh(self.system)
            assert_has_key_with_value(self.system, 'COMMENT', u'UTF 8 –')
            self.assert_(self.system.date_modified > orig_date_modified)

if __name__ == "__main__":
    unittest.main()
