#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import turbogears as tg
from lxml import etree

class TestMOTD(SeleniumTestCase):
    
    @classmethod
    def setupClass(cls):
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    def test_motd(self):
        f = open(tg.config.get('beaker.motd'), 'rb')
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(f,parser)
        the_motd = etree.tostring(tree, method='text')
        f.close()
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('30000')
        body = sel.get_text('//body')
        self.assert_(the_motd in body)


    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()
