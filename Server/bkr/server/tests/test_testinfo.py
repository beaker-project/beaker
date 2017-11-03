
# encoding: utf8

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import tempfile
import unittest
from bkr.server.testinfo import get_namespace_for_package, parse_string, \
        TestInfo, StrictParser, ParserError, ParserWarning

class NamespaceTests(unittest.TestCase):
    def test_package_not_found(self):
        "Ensure that we get None for the namespace of an unrecognized package"
        self.assertEquals(None, get_namespace_for_package('foobar'))

    def test_simple_packages(self):
        "Ensure that we get expected namespaces back for some simple packages"
        self.assertEquals('desktop', get_namespace_for_package('evolution'))
        self.assertEquals('tools', get_namespace_for_package('gcc'))

class NameFieldTests(unittest.TestCase):
    def test_name(self):
        "Ensure Name field is parsed correctly"
        ti = parse_string(u"Name: /CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_name, u"/CoreOS/cups/foo/bar")

class PathFieldTests(unittest.TestCase):
    def test_path_absolute(self):
        "Ensure absolute Path field is parsed correctly"
        ti = parse_string(u"Path: /mnt/tests/CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_path, u"/mnt/tests/CoreOS/cups/foo/bar")

    def test_path_relative(self):
        "Ensure relative Path field is parsed correctly"
        ti = parse_string(u"Path: CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_path, u"/mnt/tests/CoreOS/cups/foo/bar")

class DescriptionFieldTests(unittest.TestCase):
    def test_description(self):
        "Ensure Description field is parsed correctly"
        ti = parse_string(u"Description: Ensure that the thingummy frobnicates the doohickey", raise_errors=False)
        self.assertEquals(ti.test_description, u"Ensure that the thingummy frobnicates the doohickey")

    def test_description_with_colon(self):
        "Ensure Description field containing a colon is parsed correctly"
        ti = parse_string(u"Description: This test is from http://foo/bar", raise_errors=False)
        self.assertEquals(ti.test_description, u"This test is from http://foo/bar")

class ReleasesFieldTests(unittest.TestCase):
    def test_releases(self):
        "Ensure Releases field is parsed correctly"
        ti = parse_string(u"Releases: FC5 FC6", raise_errors=False)
        self.assertEquals(ti.releases, [u'FC5', u'FC6'])

class ArchitecturesFieldTests(unittest.TestCase):
    def test_architectures(self):
        "Ensure Architectures field is parsed correctly"
        ti = parse_string(u"Architectures: i386 x86_64", raise_errors=False)
        self.assertEquals(ti.test_archs, [u"i386", u"x86_64"])

    def test_architectures_after_releases(self):
        "Ensure that an Architectures field following a Releases field is parsed correctly"
        ti = parse_string(u"""
        Releases: FC5 FC6
        Architectures: i386 x86_64""", raise_errors=False)
        self.assertEquals(ti.releases, [u'FC5', u'FC6'])
        self.assertEquals(ti.test_archs, [u"i386", u"x86_64"])

class RhtsOptionsFieldTests(unittest.TestCase):
    def test_rhtsoptions(self):
        "Ensure RhtsOptions field is parsed correctly"
        ti = parse_string(u"RhtsOptions: Compatible", raise_errors=False)
        self.assertEquals(ti.options, [u"Compatible"])

    def test_multi_options(self):
        "Ensure RhtsOptions field is parsed correctly"
        ti = parse_string(u"RhtsOptions: Compatible -CompatService -StrongerAVC", raise_errors=False)
        self.assertEquals(ti.options, [u"Compatible", u"-CompatService", u"-StrongerAVC"])

    def test_rhtsoptions_minus(self):
        "Ensure RhtsOptions field parses options preceded with dash correctly"
        ti = parse_string(u"RhtsOptions: -Compatible", raise_errors=False)
        self.assertEquals(ti.options, [u"-Compatible"])

    def test_rhtsoption_bad_value(self):
        "Ensure RhtsOptions field captures bad input"
        self.assertRaises(ParserError, parse_string, u"RhtsOptions: Compat", raise_errors=True)

    def test_rhtsoption_duplicate(self):
        "Ensure RhtsOptions field captures duplicate entries"
        self.assertRaises(ParserError, parse_string, u"RhtsOptions: Compatible\nRhtsOptions: -Compatible", raise_errors=True)

class EnvironmentFieldTests(unittest.TestCase):
    def test_environment(self):
        "Ensure Environment field is parsed correctly"
        ti = parse_string(u"Environment: VAR1=VAL1\nEnvironment: VAR2=Value with spaces - 2", raise_errors=False)
        self.assertEquals(ti.environment["VAR1"], u"VAL1")
        self.assertEquals(ti.environment["VAR2"], u"Value with spaces - 2")

    def test_environment_duplicate_key(self):
        "Ensure Environment field captures duplicate keys"
        self.assertRaises(ParserError, parse_string, u"Environment: VAR1=VAL1\nEnvironment: VAR1=Value with spaces - 2", raise_errors=True)

    def test_environment_bad_key(self):
        "Ensure Environment field captures bad keys"
        self.assertRaises(ParserError, parse_string, u"Environment: VAR =VAL1", raise_errors=True)

class NotifyFieldTests(unittest.TestCase):
    def test_notify(self):
        "Ensure Notify field is deprecated"
        self.assertRaises(ParserWarning, parse_string, u"Notify: everyone in a 5-mile radius", raise_errors=True)

class OwnerFieldTests(unittest.TestCase):
    def test_owner_example(self):
        "Ensure that the example Owner field is parsed correctly"
        ti = parse_string(u"Owner: John Doe <jdoe@redhat.com>", raise_errors=False)
        self.assertEquals(ti.owner, u"John Doe <jdoe@redhat.com>")

    def test_owner_example2(self):
        "Ensure that other Owner fields are parsed correctly"
        ti = parse_string(u"Owner: Jane Doe <jdoe@fedoraproject.org>", raise_errors=False)
        self.assertEquals(ti.owner, u"Jane Doe <jdoe@fedoraproject.org>")

    # https://bugzilla.redhat.com/show_bug.cgi?id=723159
    def test_owner_with_hyphen(self):
        parser = StrictParser(raise_errors=True)
        parser.handle_owner('Owner', u'Endre Balint-Nagy <endre@redhat.com>')
        self.assertEquals(parser.info.owner, u'Endre Balint-Nagy <endre@redhat.com>')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1491658
    def test_non_ascii_owner(self):
        parser = StrictParser(raise_errors=True)
        parser.handle_owner('Owner', u'Gęśla Jaźń <gj@example.com>')
        self.assertEquals(parser.info.owner, u'Gęśla Jaźń <gj@example.com>')

class PriorityFieldTests(unittest.TestCase):
    def test_priority(self):
        "Ensure Priority field is parsed correctly"
        ti = parse_string(u"Priority: Manual", raise_errors=False)
        self.assertEquals(ti.priority, u"Manual")

class BugFieldTests(unittest.TestCase):
    def test_single_bug(self):
        "Ensure a single Bug field works"
        ti = parse_string(u"Bug: 123456", raise_errors=False)
        self.assertEquals(ti.bugs, [123456])

    def test_single_bugs(self):
        "Ensure a single Bugs field works"
        ti = parse_string(u"Bugs: 123456", raise_errors=False)
        self.assertEquals(ti.bugs, [123456])

    def test_multiple_bugs(self):
        "Ensure that multiple values for a Bugs field work"
        ti = parse_string(u"Bugs: 123456 456123", raise_errors=False)
        self.assertEquals(ti.bugs, [123456, 456123])

    def test_multiple_bug_lines(self):
        "Ensure that multiple Bug and Bugs lines work"
        ti = parse_string(u"""Bugs: 123456 456123
        Bug: 987654 456789""", raise_errors=False)
        self.assertEquals(ti.bugs, [123456, 456123, 987654, 456789])

    def test_blank_bug(self):
        "Ensure a blank Bug field is handled"
        ti = parse_string(u"Bug: ", raise_errors=False)
        self.assertEquals(ti.bugs, [])

class TestVersionFieldTests(unittest.TestCase):
    def test_testversion(self):
        "Ensure TestVersion field is parsed correctly"
        ti = parse_string(u"TestVersion: 1.1", raise_errors=False)
        self.assertEquals(ti.testversion, u"1.1")

class LicenseFieldTests(unittest.TestCase):
    def test_license(self):
        "Ensure License field is parsed correctly"
        ti = parse_string(u"License: GPL", raise_errors=False)
        self.assertEquals(ti.license, u"GPL")

class TestTimeFieldTests(unittest.TestCase):
    def test_testtime_seconds(self):
        "Ensure TestTime field can handle seconds"
        ti = parse_string(u"TestTime: 5", raise_errors=False)
        self.assertEquals(ti.avg_test_time, 5)

    def test_testtime_minutes(self):
        "Ensure TestTime field can handle minutes"
        ti = parse_string(u"TestTime: 10m", raise_errors=False)
        self.assertEquals(ti.avg_test_time, 600)

    def test_testtime_hours(self):
        "Ensure TestTime field can handle hours"
        ti = parse_string(u"TestTime: 2h", raise_errors=False)
        self.assertEquals(ti.avg_test_time, (2*60*60))

class RequiresFieldTests(unittest.TestCase):
    def test_single_line_requires(self):
        "Ensure Requires field is parsed correctly"
        ti = parse_string(u"Requires: evolution dogtail", raise_errors=False)
        self.assertEquals(ti.requires, [u'evolution', u'dogtail'])

    def test_multiline_requires(self):
        "Ensure we can handle multiple Requires lines"
        ti = parse_string(u"""Requires: evolution dogtail
        Requires: foo bar""", raise_errors=False)
        self.assertEquals(ti.requires, [u'evolution', u'dogtail', u'foo', u'bar'])

    def test_requires_with_case_differences(self):
        "Ensure Requires field is parsed correctly"
        ti = parse_string(u"Requires: opencryptoki openCryptoki", raise_errors=False)
        self.assertEquals(ti.requires, [u'opencryptoki', u'openCryptoki'])

class RunForFieldTests(unittest.TestCase):
    def test_single_line_runfor(self):
        "Ensure RunFor field is parsed correctly"
        ti = parse_string(u"RunFor: evolution dogtail", raise_errors=False)
        self.assertEquals(ti.runfor, [u'evolution', u'dogtail'])

    def test_multiline_runfor(self):
        "Ensure we can handle multiple RunFor lines"
        ti = parse_string(u"""RunFor: evolution dogtail
        RunFor: foo bar""", raise_errors=False)
        self.assertEquals(ti.runfor, [u'evolution', u'dogtail', u'foo', u'bar'])

class TypeFieldTests(unittest.TestCase):
    def test_single_line_type(self):
        "Ensure Type field is parsed correctly"
        ti = parse_string(u"Type: Crasher Regression", raise_errors=False)
        self.assertEquals(ti.types, [u'Crasher', u'Regression'])

    def test_multiline_type(self):
        "Ensure we can handle multiple Type lines"
        ti = parse_string(u"""Type: Crasher Regression
        Type: Performance Stress""", raise_errors=False)
        self.assertEquals(ti.types, [u'Crasher', u'Regression', u'Performance', u'Stress'])

class NeedPropertyFieldTests(unittest.TestCase):
    def test_single_line_needproperty(self):
        "Ensure NeedProperty field is parsed correctly"
        ti = parse_string(u"NeedProperty: PROCESSORS > 1", raise_errors=False)
        self.assertEquals(ti.need_properties, [(u"PROCESSORS", u">", u"1")])

    def test_multiline_needproperty(self):
        "Ensure we can handle multiple NeedProperty lines"
        ti = parse_string(u"""
        NeedProperty: CAKE = CHOCOLATE
        NeedProperty: SLICES > 3
        """, raise_errors=False)
        self.assertEquals(ti.need_properties, [(u"CAKE", u"=", u"CHOCOLATE"), (u"SLICES", u">", u"3")])

class DestructiveFieldTests(unittest.TestCase):
    def test_destructive(self):
        ti = parse_string(u"Destructive: yes", raise_errors=False)
        self.assertEquals(ti.destructive, True)

class SiteConfigDeclarationTests(unittest.TestCase):
    """Unit tests for the SiteConfig declaration"""

    def test_relative_siteconfig_without_name(self):
        "Ensure that a relative SiteConfig declaration without a Name is handled with a sane error"
        self.assertRaises(ParserError, parse_string, u"SiteConfig(server): Hostname of server", raise_errors=True)

    def test_flat_relative_siteconfig(self):
        "Ensure that relative SiteConfig declarations without nesting work"
        ti = parse_string(u"""
        Name: /desktop/evolution/mail/imap/authentication/ssl
        SiteConfig(server): Hostname of server
        SiteConfig(username): Username to use
        SiteConfig(password): Password to use
        """, raise_errors=False)
        self.assertEquals(ti.siteconfig, [(u'/desktop/evolution/mail/imap/authentication/ssl/server', u"Hostname of server"),
                                          (u'/desktop/evolution/mail/imap/authentication/ssl/username', u"Username to use"),
                                          (u'/desktop/evolution/mail/imap/authentication/ssl/password', u"Password to use")
                                          ])

    def test_nested_relative_siteconfig(self):
        "Ensure that a relative SiteConfig declaration containing a path works"
        ti = parse_string(u"""
        Name: /desktop/evolution/mail/imap/authentication
        SiteConfig(ssl/server): Hostname of server to try SSL auth against
        SiteConfig(ssl/username): Username to use for SSL auth
        SiteConfig(ssl/password): Password to use for SSL auth
        SiteConfig(tls/server): Hostname of server to try TLS auth against
        SiteConfig(tls/username): Username to use for TLS auth
        SiteConfig(tls/password): Password to use for TLS auth
        """, raise_errors=False)
        self.assertEquals(ti.siteconfig, [(u'/desktop/evolution/mail/imap/authentication/ssl/server', u"Hostname of server to try SSL auth against"),
                                          (u'/desktop/evolution/mail/imap/authentication/ssl/username', u"Username to use for SSL auth"),
                                          (u'/desktop/evolution/mail/imap/authentication/ssl/password', u"Password to use for SSL auth"),
                                          (u'/desktop/evolution/mail/imap/authentication/tls/server', u"Hostname of server to try TLS auth against"),
                                          (u'/desktop/evolution/mail/imap/authentication/tls/username', u"Username to use for TLS auth"),
                                          (u'/desktop/evolution/mail/imap/authentication/tls/password', u"Password to use for TLS auth")
                                          ])

    def test_absolute_siteconfig(self):
        "Ensure that an absolute SiteConfig declaration works"
        ti = parse_string(u"""SiteConfig(/stable-servers/ldap/hostname): Location of stable LDAP server to use""", raise_errors=False)
        self.assertEquals(ti.siteconfig, [(u'/stable-servers/ldap/hostname', u'Location of stable LDAP server to use')])

    #def test_siteconfig_comment(self):
    #    "Ensure that comments are stripped as expected from descriptions"
    #    ti = parse_string("SiteConfig(/foo/bar): Some value # hello world", raise_errors=False)
    #    self.assertEquals(ti.siteconfig, [('/foo/bar', "Some value")])

    def test_siteconfig_whitespace(self):
        "Ensure that whitespace is stripped as expected from descriptions"
        ti = parse_string(u"SiteConfig(/foo/bar):        Some value    ", raise_errors=False)
        self.assertEquals(ti.siteconfig, [(u'/foo/bar', u"Some value")])

    def test_output_relative_siteconfig(self):
        "Ensure that the output methods collapse redundant paths in relative SiteConfig declarations"
        ti = TestInfo()
        ti.test_name = u'/foo/bar'
        ti.siteconfig = [(u'/foo/bar/baz/fubar', u'Dummy value')]
        self.assertEquals(ti.generate_siteconfig_lines(), u"SiteConfig(baz/fubar): Dummy value\n")


class IntegrationTests(unittest.TestCase):
    def test_example_file(self):
        "Ensure a full example file is parsed correctly"
        ti = parse_string(u"""\
# Test comment
Owner:        Jane Doe <jdoe@redhat.com>
Name:         /examples/coreutils/example-simple-test
Path:         /mnt/tests/examples/coreutils/example-simple-test
Description:  This test ensures that cafés are generated and validated correctly
TestTime:     1m
TestVersion:  1.1
License:      GPL
RunFor:       coreutils
Requires:     coreutils python
        """, raise_errors=True)
        self.assertEquals(ti.owner, u"Jane Doe <jdoe@redhat.com>")
        self.assertEquals(ti.test_name, u"/examples/coreutils/example-simple-test")
        self.assertEquals(ti.test_path, u"/mnt/tests/examples/coreutils/example-simple-test")
        self.assertEquals(ti.test_description, u"This test ensures that cafés are generated and validated correctly")
        self.assertEquals(ti.avg_test_time, 60)
        self.assertEquals(ti.testversion, u"1.1")
        self.assertEquals(ti.license, u"GPL")
        self.assertEquals(ti.runfor, [u"coreutils"])
        self.assertEquals(ti.requires, [u"coreutils", u"python"])

    def test_output_testinfo(self):
        "Output an example file, then ensure it is parsed succesfully"
        ti1 = parse_string(u"""\
# Test comment
Owner:        Jane Doe <jdoe@redhat.com>
Name:         /examples/coreutils/example-simple-test
Path:         /mnt/tests/examples/coreutils/example-simple-test
Description:  This test ensures that cafés are generated and validated correctly
TestTime:     1m
TestVersion:  1.1
License:      GPL
Destructive:  yes
RunFor:       coreutils
Requires:     coreutils python
NeedProperty: CAKE = CHOCOLATE
NeedProperty: SLICES > 3
SiteConfig(server): Hostname of server
SiteConfig(username): Username to use
SiteConfig(password): Password to use
SiteConfig(ssl/server): Hostname of server to try SSL auth against
SiteConfig(ssl/username): Username to use for SSL auth
SiteConfig(ssl/password): Password to use for SSL auth
SiteConfig(tls/server): Hostname of server to try TLS auth against
SiteConfig(tls/username): Username to use for TLS auth
SiteConfig(tls/password): Password to use for TLS auth
SiteConfig(/stable-servers/ldap/hostname): Location of stable LDAP server to use
        """, raise_errors=True)
        file = tempfile.NamedTemporaryFile(mode='w')
        ti1.output(file)
        file.flush()

        ti2 = parse_string(open(file.name).read().decode('utf8'))
        self.assertEquals(ti2.owner, u"Jane Doe <jdoe@redhat.com>")
        self.assertEquals(ti2.test_name, u"/examples/coreutils/example-simple-test")
        self.assertEquals(ti2.test_path, u"/mnt/tests/examples/coreutils/example-simple-test")
        self.assertEquals(ti2.test_description, u"This test ensures that cafés are generated and validated correctly")
        self.assertEquals(ti2.avg_test_time, 60)
        self.assertEquals(ti2.testversion, u"1.1")
        self.assertEquals(ti2.license, u"GPL")
        self.assertEquals(ti2.destructive, True)
        self.assertEquals(ti2.runfor, [u"coreutils"])
        self.assertEquals(ti2.requires, [u"coreutils", u"python"])
        self.assertEquals(ti2.need_properties, [(u'CAKE', u'=', u'CHOCOLATE'), (u'SLICES', u'>', u'3')])
        self.assertEquals(ti2.siteconfig, [(u'/examples/coreutils/example-simple-test/server', u'Hostname of server'),
                                           (u'/examples/coreutils/example-simple-test/username', u'Username to use'),
                                           (u'/examples/coreutils/example-simple-test/password', u'Password to use'),
                                           (u'/examples/coreutils/example-simple-test/ssl/server', u'Hostname of server to try SSL auth against'),
                                           (u'/examples/coreutils/example-simple-test/ssl/username', u'Username to use for SSL auth'),
                                           (u'/examples/coreutils/example-simple-test/ssl/password', u'Password to use for SSL auth'),
                                           (u'/examples/coreutils/example-simple-test/tls/server', u'Hostname of server to try TLS auth against'),
                                           (u'/examples/coreutils/example-simple-test/tls/username', u'Username to use for TLS auth'),
                                           (u'/examples/coreutils/example-simple-test/tls/password', u'Password to use for TLS auth'),
                                           (u'/stable-servers/ldap/hostname', u'Location of stable LDAP server to use')])
