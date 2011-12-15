#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session

class Search(SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.distro_one_name = u'nametest1'
        self.distro_one_breed = u'breedtest1'
        self.distro_one_osmajor = u'osmajortest1'
        self.distro_one_osminor = u'1'
        self.distro_one_virt = True
        self.distro_one_arch = u'ia64'
        self.distro_one_tags = None

        self.distro_one = data_setup.create_distro(name=self.distro_one_name, breed=self.distro_one_breed,
            osmajor=self.distro_one_osmajor, osminor = self.distro_one_osminor,
            arch=self.distro_one_arch, virt=self.distro_one_virt,
            tags =self.distro_one_tags)


        self.distro_two_name = u'nametest2'
        self.distro_two_breed = u'breedtest2'
        self.distro_two_osmajor = u'osmajortest2'
        self.distro_two_osminor = u'2'
        self.distro_two_virt = True
        self.distro_two_arch = u'i386'
        self.distro_two_tags = None

        self.distro_two = data_setup.create_distro(name=self.distro_two_name, breed=self.distro_two_breed,
            osmajor=self.distro_two_osmajor, osminor = self.distro_two_osminor,
            arch=self.distro_two_arch, virt=self.distro_two_virt,
            tags =self.distro_two_tags)

        self.distro_three_name = u'nametest3'
        self.distro_three_breed = u'breedtest3'
        self.distro_three_osmajor = u'osmajortest3'
        self.distro_three_osminor = u'3'
        self.distro_three_virt = False
        self.distro_three_arch = u's390'
        self.distro_three_tags = None

        self.distro_three = data_setup.create_distro(name=self.distro_three_name, breed=self.distro_three_breed,
            osmajor=self.distro_three_osmajor, osminor = self.distro_three_osminor,
            arch=self.distro_three_arch, virt=self.distro_three_virt,
            tags =self.distro_three_tags)
        session.flush()
        self.selenium.start()

    def test_distro_search(self):
        sel = self.selenium
        sel = self.selenium

        """
        SimpleSearch 
        START
        """
        sel.open("distros/")
        sel.type("simplesearch", "%s" % self.distro_one.name)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        try: 
            self.failUnless(sel.is_text_present("%s" % self.distro_one.name))
        except AssertionError, e: 
            self.verificationErrors.append(\
            unicode('1.Searching by %s, did not find %s' % \
            (self.distro_one.name,self.distro_one.name)))

        try: 
            self.failUnless(not sel.is_text_present("%s" % self.distro_two.name))
        except AssertionError, e: 
            self.verificationErrors.append(\
            unicode('2.Searching by %s, found %s' % \
            (self.distro_one.name,self.distro_two.name)))

        try:
            self.failUnless(not sel.is_text_present("%s" % self.distro_three.name))
        except AssertionError, e: 
            self.verificationErrors.append(\
            unicode('3.Searching by %s, found %s' % \
            (self.distro_one.name,self.distro_three.name)))
        """ 
        END
        """

        """
        Arch -> is -> ia64
        START
        """
        sel.click("advancedsearch")
        sel.select("distrosearch_0_table", "label=Arch")
        sel.type("distrosearch_0_value", "%s" % self.distro_one_arch)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: 
            self.failUnless(sel.is_text_present("%s" % self.distro_one.name))
        except AssertionError, e:
            self.verificationErrors.append( \
            unicode('4.Searching by %s, did not find %s' % \
            (self.distro_one_arch,self.distro_one.name)))

        try: 
            self.failUnless(not sel.is_text_present("%s" % self.distro_two.name))
        except AssertionError, e: 
            self.verificationErrors.append( \
            unicode('5.Searching by %s, found %s' % \
            (self.distro_one_arch,self.distro_two.name)))

        try: 
            self.failUnless(not sel.is_text_present("%s" % self.distro_three.name))
        except AssertionError, e: self.verificationErrors.append( \
            unicode('6.Searching by %s, did not find %s' % \
            (self.distro_one_arch,self.distro_three.name)))
        """
        END
        """
        """
        Arch -> is -> i386
        START
        """
        sel.select("distrosearch_0_table", "label=Arch")
        sel.select("distrosearch_0_operation", "label=is")
        sel.type("distrosearch_0_value", "%s" % self.distro_two_arch)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try:
            self.failUnless(sel.is_text_present("%s" % self.distro_two.name))
        except AssertionError, e:
            self.verificationErrors.append(\
            unicode('7.Searching by %s, did not find %s' % \
            (self.distro_two_arch, self.distro_two.name)))

        try:
            self.failUnless(not sel.is_text_present("%s" % self.distro_one.name))
        except AssertionError, e:
            self.verificationErrors.append(\
            unicode('8.Searching by %s, found %s' % \
            (self.distro_two_arch, self.distro_one.name)))

        try:
            self.failUnless(not sel.is_text_present("%s" % self.distro_three.name))
        except AssertionError, e:
            self.verificationErrors.append(\
            unicode('9.Searching by %s, found %s' % \
            (self.distro_two_arch, self.distro_three.name)))
        """
        END
        """

        """
        Arch -> is not -> i386
        """
        sel.select("distrosearch_0_table", "label=Arch")
        sel.select("distrosearch_0_operation", "label=is not")
        sel.type("distrosearch_0_value", "%s" % self.distro_two_arch)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: 
            self.failUnless(sel.is_text_present("%s" % self.distro_one.name))
        except AssertionError, e: 
            self.verificationErrors.append(\
            unicode('10.Searching by %s, did not find %s' % \
            (self.distro_two_arch,self.distro_one.name)))

        try: 
            self.failUnless(sel.is_text_present("%s" % self.distro_three.name))
        except AssertionError, e: self.verificationErrors.append(\
            unicode('11.Searching by %s, did not find %s' % \
            (self.distro_two_arch, self.distro_three.name)))

        try: 
            self.failUnless(not sel.is_text_present("%s" % self.distro_two.name))
        except AssertionError, e: self.verificationErrors.append(\
            unicode('12.Searching by %s, found %s' % \
            (self.distro_two_arch, self.distro_two.name)))
        """
        END
        """
        """
        Breed -> is -> 
        """
        sel.select("distrosearch_0_table", "label=Breed")
        sel.select("distrosearch_0_operation", "label=is")
        sel.type("distrosearch_0_value", "%s" % self.distro_one.breed)
        sel.click("Search") 
        sel.wait_for_page_to_load("30000")
        try: 
            self.failUnless(sel.is_text_present("%s" % self.distro_one.name))
        except AssertionError, e: self.verificationErrors.append(\
            unicode('13.Failed to find %s when searching for Breed %s' % \
            (self.distro_one.name, self.distro_one.breed)))

        try: 
            self.failUnless(not sel.is_text_present("%s" % self.distro_two.name))
        except AssertionError, e: self.verificationErrors.append(\
            unicode('14.Found %s when searching for Breed %s' % \
            (self.distro_two.name, self.distro_one.breed)))

        try: 
            self.failUnless(not sel.is_text_present("%s" % self.distro_three.name))
        except AssertionError, e: self.verificationErrors.append(\
            unicode('15.Failed to find %s when searching for Breed %s' % \
            (self.distro_three.name, self.distro_one.breed)))
        #END

        sel.select("distrosearch_0_table", "label=Virt")
        sel.select("distrosearch_0_operation", "label=is")
        sel.select("distrosearch_0_value", "label=True")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("%s" % self.distro_one.name))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("%s" % self.distro_two.name))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(not sel.is_text_present("%s" % self.distro_three.name))
        except AssertionError, e: self.verificationErrors.append(str(e))

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
