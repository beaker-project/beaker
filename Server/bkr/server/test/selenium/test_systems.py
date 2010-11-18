# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import unittest
import logging
from urlparse import urljoin
from urllib import urlencode, urlopen, quote
import lxml.etree
import rdflib.graph
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.server.test import data_setup, get_server_base
from bkr.server.model import User

def atom_xpath(expr):
    return lxml.etree.XPath(expr, namespaces={'atom': 'http://www.w3.org/2005/Atom'})

class TestSystemsGrid(SeleniumTestCase):

    def setUp(self):
        data_setup.create_system()
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_atom_feed_link_is_present(self):
        sel = self.selenium
        sel.open('')
        self.assertEqual(sel.get_xpath_count('/html/head/link[@rel="feed" '
                'and @title="Atom feed" and contains(@href, "tg_format=atom")]'),
                '1')

class TestSystemsAtomFeed(unittest.TestCase):

    def feed_contains_system(self, feed, fqdn):
        xpath = atom_xpath('/atom:feed/atom:entry/atom:title[text()="%s"]' % fqdn)
        return len(xpath(feed))

    def test_all_systems(self):
        systems = [data_setup.create_system() for _ in range(3)]
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        for system in systems:
            self.assert_(self.feed_contains_system(feed, system.fqdn))

    def test_link_to_rdfxml(self):
        system = data_setup.create_system()
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        href_xpath = atom_xpath(
                '/atom:feed/atom:entry[atom:title/text()="%s"]'
                '/atom:link[@rel="alternate" and @type="application/rdf+xml"]/@href'
                % system.fqdn)
        href, = href_xpath(feed)
        self.assertEqual(href,
                '%sview/%s?tg_format=rdfxml' % (get_server_base(), system.fqdn))

    def test_link_to_turtle(self):
        system = data_setup.create_system()
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        href_xpath = atom_xpath(
                '/atom:feed/atom:entry[atom:title/text()="%s"]'
                '/atom:link[@rel="alternate" and @type="application/x-turtle"]/@href'
                % system.fqdn)
        href, = href_xpath(feed)
        self.assertEqual(href,
                '%sview/%s?tg_format=turtle' % (get_server_base(), system.fqdn))

    def test_filter_by_group(self):
        data_setup.create_system(fqdn='nogroup.system')
        self.group = data_setup.create_group()
        data_setup.create_system(fqdn='grouped.system').groups.append(self.group)
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'systemsearch-0.table': 'System/Group',
                'systemsearch-0.operation': 'is',
                'systemsearch-0.value': self.group.group_name}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assert_(not self.feed_contains_system(feed, 'nogroup.system'))
        self.assert_(self.feed_contains_system(feed, 'grouped.system'))

class TestSystemView(SeleniumTestCase):

    slow = True

    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def go_to_system_view(self):
        sel = self.selenium
        sel.open('')
        sel.type('simplesearch', self.system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('3000')
        sel.click('link=%s' % self.system.fqdn)
        sel.wait_for_page_to_load('3000')

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.assertEquals(self.selenium.get_title(), self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=623603
    # see also TestRecipeView.test_can_report_problem
    def test_can_report_problem(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('link=(Report problem)')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(self.selenium.get_title(),
                'Report a problem with %s' % self.system.fqdn)

class TestSystemViewRDF(unittest.TestCase):

    slow = True

    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)
        session.flush()

    def test_turtle(self):
        rdf_url = urljoin(get_server_base(),
                'view/%s?%s' % (quote(self.system.fqdn.encode('utf8')),
                    urlencode({'tg_format': 'turtle'})))
        graph = rdflib.graph.Graph()
        graph.parse(location=rdf_url, format='n3')
        self.assert_(len(graph) >= 9)

    def test_rdfxml(self):
        rdf_url = urljoin(get_server_base(),
                'view/%s?%s' % (quote(self.system.fqdn.encode('utf8')),
                    urlencode({'tg_format': 'rdfxml'})))
        graph = rdflib.graph.Graph()
        graph.parse(location=rdf_url, format='xml')
        self.assert_(len(graph) >= 9)

class ReserveSystemXmlRpcTest(XmlRpcTestCase):

    def test_cannot_reserve_when_not_logged_in(self):
        system = data_setup.create_system()
        session.flush()
        server = self.get_server()
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_(e.faultString.startswith(
                    'turbogears.identity.exceptions.IdentityFailure'))

    def test_cannot_reserve_automated_system(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_('Cannot reserve system with status Automated'
                    in e.faultString)

    def test_cannot_reserve_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(owner=user, status=u'Manual', shared=True)
        system.user = User.by_user_name(data_setup.ADMIN_USER)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_(e.faultString.startswith('bkr.server.bexceptions.BX'))

    def test_reserve_system(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        self.assert_(system.user is None)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
        session.refresh(system)
        self.assertEqual(system.user, user)
        reserved_activity = system.activity[-1]
        self.assertEqual(reserved_activity.action, 'Reserved')
        self.assertEqual(reserved_activity.field_name, 'User')
        self.assertEqual(reserved_activity.user, user)
        self.assertEqual(reserved_activity.new_value, user.user_name)
        self.assertEqual(reserved_activity.service, 'XMLRPC')
