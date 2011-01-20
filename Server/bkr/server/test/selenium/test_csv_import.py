#!/usr/bin/python
# vim: set fileencoding=utf-8 :

import bkr.server.test.selenium
from bkr.server.test import data_setup
from bkr.server.test.assertions import assert_has_key_with_value
from bkr.server.model import Arch
from turbogears.database import session
import unittest
from tempfile import NamedTemporaryFile

class CSVImportTest(bkr.server.test.selenium.SeleniumTestCase):

    def setUp(self):
        self.system = data_setup.create_system()
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def import_csv(self, contents):
        sel = self.selenium
        sel.open("")
        self.login()
        sel.click("link=Import")
        sel.wait_for_page_to_load("3000")
        csv_file = NamedTemporaryFile(prefix=self.__module__)
        csv_file.write(contents)
        csv_file.flush()
        sel.type("import_csv_file", csv_file.name)
        sel.click("//input[@value='Import CSV']")
        sel.wait_for_page_to_load("3000")

    def test_system(self):
        orig_date_modified = self.system.date_modified
        self.import_csv((u'csv_type,fqdn,location,arch\n'
                u'system,%s,Under my desk,ia64' % self.system.fqdn)
                .encode('utf8'))
        sel = self.selenium
        self.failUnless(sel.is_text_present("No Errors"))
        session.refresh(self.system)
        self.assertEquals(self.system.location, u'Under my desk')
        self.assert_(Arch.by_name(u'ia64') in self.system.arch)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_keyvalue(self):
        orig_date_modified = self.system.date_modified
        self.import_csv((u'csv_type,fqdn,key,key_value,deleted\n'
                u'keyvalue,%s,COMMENT,UTF 8 –,False' % self.system.fqdn)
                .encode('utf8'))
        sel = self.selenium
        self.failUnless(sel.is_text_present("No Errors"))
        session.refresh(self.system)
        assert_has_key_with_value(self.system, 'COMMENT', u'UTF 8 –')
        self.assert_(self.system.date_modified > orig_date_modified)

if __name__ == "__main__":
    unittest.main()
