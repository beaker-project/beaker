
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
        ti = parse_string("Name: /CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_name, "/CoreOS/cups/foo/bar")

class PathFieldTests(unittest.TestCase):
    def test_path_absolute(self):
        "Ensure absolute Path field is parsed correctly"
        ti = parse_string("Path: /mnt/tests/CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_path, "/mnt/tests/CoreOS/cups/foo/bar")

    def test_path_relative(self):
        "Ensure relative Path field is parsed correctly"
        ti = parse_string("Path: CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_path, "/mnt/tests/CoreOS/cups/foo/bar")

class DescriptionFieldTests(unittest.TestCase):
    def test_description(self):
        "Ensure Description field is parsed correctly"
        ti = parse_string("Description: Ensure that the thingummy frobnicates the doohickey", raise_errors=False)
        self.assertEquals(ti.test_description, "Ensure that the thingummy frobnicates the doohickey")

    def test_description_with_colon(self):
        "Ensure Description field containing a colon is parsed correctly"
        ti = parse_string("Description: This test is from http://foo/bar", raise_errors=False)
        self.assertEquals(ti.test_description, "This test is from http://foo/bar")

class ReleasesFieldTests(unittest.TestCase):
    def test_releases(self):
        "Ensure Releases field is parsed correctly"
        ti = parse_string("Releases: FC5 FC6", raise_errors=False)
        self.assertEquals(ti.releases, ['FC5', 'FC6'])

class ArchitecturesFieldTests(unittest.TestCase):
    def test_architectures(self):
        "Ensure Architectures field is parsed correctly"
        ti = parse_string("Architectures: i386 x86_64", raise_errors=False)
        self.assertEquals(ti.test_archs, ["i386", "x86_64"])

    def test_architectures_after_releases(self):
        "Ensure that an Architectures field following a Releases field is parsed correctly"
        ti = parse_string("""
        Releases: FC5 FC6
        Architectures: i386 x86_64""", raise_errors=False)
        self.assertEquals(ti.releases, ['FC5', 'FC6'])
        self.assertEquals(ti.test_archs, ["i386", "x86_64"])

class RhtsOptionsFieldTests(unittest.TestCase):
    def test_rhtsoptions(self):
        "Ensure RhtsOptions field is parsed correctly"
        ti = parse_string("RhtsOptions: Compatible", raise_errors=False)
        self.assertEquals(ti.options, ["Compatible"])

    def test_multi_options(self):
        "Ensure RhtsOptions field is parsed correctly"
        ti = parse_string("RhtsOptions: Compatible -CompatService -StrongerAVC", raise_errors=False)
        self.assertEquals(ti.options, ["Compatible", "-CompatService", "-StrongerAVC"])

    def test_rhtsoptions_minus(self):
        "Ensure RhtsOptions field parses options preceded with dash correctly"
        ti = parse_string("RhtsOptions: -Compatible", raise_errors=False)
        self.assertEquals(ti.options, ["-Compatible"])

    def test_rhtsoption_bad_value(self):
        "Ensure RhtsOptions field captures bad input"
        self.assertRaises(ParserError, parse_string, "RhtsOptions: Compat", raise_errors=True)

    def test_rhtsoption_duplicate(self):
        "Ensure RhtsOptions field captures duplicate entries"
        self.assertRaises(ParserError, parse_string, "RhtsOptions: Compatible\nRhtsOptions: -Compatible", raise_errors=True)

class EnvironmentFieldTests(unittest.TestCase):
    def test_environment(self):
        "Ensure Environment field is parsed correctly"
        ti = parse_string("Environment: VAR1=VAL1\nEnvironment: VAR2=Value with spaces - 2", raise_errors=False)
        self.assertEquals(ti.environment["VAR1"], "VAL1")
        self.assertEquals(ti.environment["VAR2"], "Value with spaces - 2")

    def test_environment_duplicate_key(self):
        "Ensure Environment field captures duplicate keys"
        self.assertRaises(ParserError, parse_string, "Environment: VAR1=VAL1\nEnvironment: VAR1=Value with spaces - 2", raise_errors=True)

    def test_environment_bad_key(self):
        "Ensure Environment field captures bad keys"
        self.assertRaises(ParserError, parse_string, "Environment: VAR =VAL1", raise_errors=True)

class NotifyFieldTests(unittest.TestCase):
    def test_notify(self):
        "Ensure Notify field is deprecated"
        self.assertRaises(ParserWarning, parse_string, "Notify: everyone in a 5-mile radius", raise_errors=True)

class OwnerFieldTests(unittest.TestCase):
    def test_owner_example(self):
        "Ensure that the example Owner field is parsed correctly"
        ti = parse_string("Owner: John Doe <jdoe@redhat.com>", raise_errors=False)
        self.assertEquals(ti.owner, "John Doe <jdoe@redhat.com>")

    def test_owner_example2(self):
        "Ensure that other Owner fields are parsed correctly"
        ti = parse_string("Owner: Jane Doe <jdoe@fedoraproject.org>", raise_errors=False)
        self.assertEquals(ti.owner, "Jane Doe <jdoe@fedoraproject.org>")

    # https://bugzilla.redhat.com/show_bug.cgi?id=723159
    def test_owner_with_hyphen(self):
        parser = StrictParser(raise_errors=True)
        parser.handle_owner('Owner', 'Endre Balint-Nagy <endre@redhat.com>')
        self.assertEquals(parser.info.owner, 'Endre Balint-Nagy <endre@redhat.com>')

class PriorityFieldTests(unittest.TestCase):
    def test_priority(self):
        "Ensure Priority field is parsed correctly"
        ti = parse_string("Priority: Manual", raise_errors=False)
        self.assertEquals(ti.priority, "Manual")

class BugFieldTests(unittest.TestCase):
    def test_single_bug(self):
        "Ensure a single Bug field works"
        ti = parse_string("Bug: 123456", raise_errors=False)
        self.assertEquals(ti.bugs, [123456])

    def test_single_bugs(self):
        "Ensure a single Bugs field works"
        ti = parse_string("Bugs: 123456", raise_errors=False)
        self.assertEquals(ti.bugs, [123456])

    def test_multiple_bugs(self):
        "Ensure that multiple values for a Bugs field work"
        ti = parse_string("Bugs: 123456 456123", raise_errors=False)
        self.assertEquals(ti.bugs, [123456, 456123])

    def test_multiple_bug_lines(self):
        "Ensure that multiple Bug and Bugs lines work"
        ti = parse_string("""Bugs: 123456 456123
        Bug: 987654 456789""", raise_errors=False)
        self.assertEquals(ti.bugs, [123456, 456123, 987654, 456789])

    def test_blank_bug(self):
        "Ensure a blank Bug field is handled"
        ti = parse_string("Bug: ", raise_errors=False)
        self.assertEquals(ti.bugs, [])

class TestVersionFieldTests(unittest.TestCase):
    def test_testversion(self):
        "Ensure TestVersion field is parsed correctly"
        ti = parse_string("TestVersion: 1.1", raise_errors=False)
        self.assertEquals(ti.testversion, "1.1")

class LicenseFieldTests(unittest.TestCase):
    def test_license(self):
        "Ensure License field is parsed correctly"
        ti = parse_string("License: GPL", raise_errors=False)
        self.assertEquals(ti.license, "GPL")

class TestTimeFieldTests(unittest.TestCase):
    def test_testtime_seconds(self):
        "Ensure TestTime field can handle seconds"
        ti = parse_string("TestTime: 5", raise_errors=False)
        self.assertEquals(ti.avg_test_time, 5)

    def test_testtime_minutes(self):
        "Ensure TestTime field can handle minutes"
        ti = parse_string("TestTime: 10m", raise_errors=False)
        self.assertEquals(ti.avg_test_time, 600)

    def test_testtime_hours(self):
        "Ensure TestTime field can handle hours"
        ti = parse_string("TestTime: 2h", raise_errors=False)
        self.assertEquals(ti.avg_test_time, (2*60*60))

class RequiresFieldTests(unittest.TestCase):
    def test_single_line_requires(self):
        "Ensure Requires field is parsed correctly"
        ti = parse_string("Requires: evolution dogtail", raise_errors=False)
        self.assertEquals(ti.requires, ['evolution', 'dogtail'])

    def test_multiline_requires(self):
        "Ensure we can handle multiple Requires lines"
        ti = parse_string("""Requires: evolution dogtail
        Requires: foo bar""", raise_errors=False)
        self.assertEquals(ti.requires, ['evolution', 'dogtail', 'foo', 'bar'])

    def test_requires_with_case_differences(self):
        "Ensure Requires field is parsed correctly"
        ti = parse_string("Requires: opencryptoki openCryptoki", raise_errors=False)
        self.assertEquals(ti.requires, ['opencryptoki', 'openCryptoki'])

class RunForFieldTests(unittest.TestCase):
    def test_single_line_runfor(self):
        "Ensure RunFor field is parsed correctly"
        ti = parse_string("RunFor: evolution dogtail", raise_errors=False)
        self.assertEquals(ti.runfor, ['evolution', 'dogtail'])

    def test_multiline_runfor(self):
        "Ensure we can handle multiple RunFor lines"
        ti = parse_string("""RunFor: evolution dogtail
        RunFor: foo bar""", raise_errors=False)
        self.assertEquals(ti.runfor, ['evolution', 'dogtail', 'foo', 'bar'])

class TypeFieldTests(unittest.TestCase):
    def test_single_line_type(self):
        "Ensure Type field is parsed correctly"
        ti = parse_string("Type: Crasher Regression", raise_errors=False)
        self.assertEquals(ti.types, ['Crasher', 'Regression'])

    def test_multiline_type(self):
        "Ensure we can handle multiple Type lines"
        ti = parse_string("""Type: Crasher Regression
        Type: Performance Stress""", raise_errors=False)
        self.assertEquals(ti.types, ['Crasher', 'Regression', 'Performance', 'Stress'])

class NeedPropertyFieldTests(unittest.TestCase):
    def test_single_line_needproperty(self):
        "Ensure NeedProperty field is parsed correctly"
        ti = parse_string("NeedProperty: PROCESSORS > 1", raise_errors=False)
        self.assertEquals(ti.need_properties, [("PROCESSORS", ">", "1")])

    def test_multiline_needproperty(self):
        "Ensure we can handle multiple NeedProperty lines"
        ti = parse_string("""
        NeedProperty: CAKE = CHOCOLATE
        NeedProperty: SLICES > 3
        """, raise_errors=False)
        self.assertEquals(ti.need_properties, [("CAKE", "=", "CHOCOLATE"), ("SLICES", ">", "3")])

class DestructiveFieldTests(unittest.TestCase):
    def test_destructive(self):
        ti = parse_string("Destructive: yes", raise_errors=False)
        self.assertEquals(ti.destructive, True)

class SiteConfigDeclarationTests(unittest.TestCase):
    """Unit tests for the SiteConfig declaration"""

    def test_relative_siteconfig_without_name(self):
        "Ensure that a relative SiteConfig declaration without a Name is handled with a sane error"
        self.assertRaises(ParserError, parse_string, "SiteConfig(server): Hostname of server", raise_errors=True)

    def test_flat_relative_siteconfig(self):
        "Ensure that relative SiteConfig declarations without nesting work"
        ti = parse_string("""
        Name: /desktop/evolution/mail/imap/authentication/ssl
        SiteConfig(server): Hostname of server
        SiteConfig(username): Username to use
        SiteConfig(password): Password to use
        """, raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/desktop/evolution/mail/imap/authentication/ssl/server', "Hostname of server"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/username', "Username to use"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/password', "Password to use")
                                          ])

    def test_nested_relative_siteconfig(self):
        "Ensure that a relative SiteConfig declaration containing a path works"
        ti = parse_string("""
        Name: /desktop/evolution/mail/imap/authentication
        SiteConfig(ssl/server): Hostname of server to try SSL auth against
        SiteConfig(ssl/username): Username to use for SSL auth
        SiteConfig(ssl/password): Password to use for SSL auth
        SiteConfig(tls/server): Hostname of server to try TLS auth against
        SiteConfig(tls/username): Username to use for TLS auth
        SiteConfig(tls/password): Password to use for TLS auth
        """, raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/desktop/evolution/mail/imap/authentication/ssl/server', "Hostname of server to try SSL auth against"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/username', "Username to use for SSL auth"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/password', "Password to use for SSL auth"),
                                          ('/desktop/evolution/mail/imap/authentication/tls/server', "Hostname of server to try TLS auth against"),
                                          ('/desktop/evolution/mail/imap/authentication/tls/username', "Username to use for TLS auth"),
                                          ('/desktop/evolution/mail/imap/authentication/tls/password', "Password to use for TLS auth")
                                          ])

    def test_absolute_siteconfig(self):
        "Ensure that an absolute SiteConfig declaration works"
        ti = parse_string("""SiteConfig(/stable-servers/ldap/hostname): Location of stable LDAP server to use""", raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/stable-servers/ldap/hostname', 'Location of stable LDAP server to use')])

    #def test_siteconfig_comment(self):
    #    "Ensure that comments are stripped as expected from descriptions"
    #    ti = parse_string("SiteConfig(/foo/bar): Some value # hello world", raise_errors=False)
    #    self.assertEquals(ti.siteconfig, [('/foo/bar', "Some value")])

    def test_siteconfig_whitespace(self):
        "Ensure that whitespace is stripped as expected from descriptions"
        ti = parse_string("SiteConfig(/foo/bar):        Some value    ", raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/foo/bar', "Some value")])

    def test_output_relative_siteconfig(self):
        "Ensure that the output methods collapse redundant paths in relative SiteConfig declarations"
        ti = TestInfo()
        ti.test_name = '/foo/bar'
        ti.siteconfig = [('/foo/bar/baz/fubar', 'Dummy value')]
        self.assertEquals(ti.generate_siteconfig_lines(), "SiteConfig(baz/fubar): Dummy value\n")


class IntegrationTests(unittest.TestCase):
    def test_example_file(self):
        "Ensure a full example file is parsed correctly"
        ti = parse_string("""\
# Test comment
Owner:        Jane Doe <jdoe@redhat.com>
Name:         /examples/coreutils/example-simple-test
Path:         /mnt/tests/examples/coreutils/example-simple-test
Description:  This test ensures that md5sums are generated and validated correctly
TestTime:     1m
TestVersion:  1.1
License:      GPL
RunFor:       coreutils
Requires:     coreutils python
        """, raise_errors=True)
        self.assertEquals(ti.owner, "Jane Doe <jdoe@redhat.com>")
        self.assertEquals(ti.test_name, "/examples/coreutils/example-simple-test")
        self.assertEquals(ti.test_path, "/mnt/tests/examples/coreutils/example-simple-test")
        self.assertEquals(ti.test_description, "This test ensures that md5sums are generated and validated correctly")
        self.assertEquals(ti.avg_test_time, 60)
        self.assertEquals(ti.testversion, "1.1")
        self.assertEquals(ti.license, "GPL")
        self.assertEquals(ti.runfor, ["coreutils"])
        self.assertEquals(ti.requires, ["coreutils", "python"])

    def test_output_testinfo(self):
        "Output an example file, then ensure it is parsed succesfully"
        ti1 = parse_string("""\
# Test comment
Owner:        Jane Doe <jdoe@redhat.com>
Name:         /examples/coreutils/example-simple-test
Path:         /mnt/tests/examples/coreutils/example-simple-test
Description:  This test ensures that md5sums are generated and validated correctly
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

        p = StrictParser(raise_errors=True)
        p.parse(open(file.name, "r").readlines())
        ti2= p.info
        self.assertEquals(ti2.owner, "Jane Doe <jdoe@redhat.com>")
        self.assertEquals(ti2.test_name, "/examples/coreutils/example-simple-test")
        self.assertEquals(ti2.test_path, "/mnt/tests/examples/coreutils/example-simple-test")
        self.assertEquals(ti2.test_description, "This test ensures that md5sums are generated and validated correctly")
        self.assertEquals(ti2.avg_test_time, 60)
        self.assertEquals(ti2.testversion, "1.1")
        self.assertEquals(ti2.license, "GPL")
        self.assertEquals(ti2.destructive, True)
        self.assertEquals(ti2.runfor, ["coreutils"])
        self.assertEquals(ti2.requires, ["coreutils", "python"])
        self.assertEquals(ti2.need_properties, [('CAKE', '=', 'CHOCOLATE'), ('SLICES', '>', '3')])
        self.assertEquals(ti2.siteconfig, [('/examples/coreutils/example-simple-test/server', 'Hostname of server'),
                                           ('/examples/coreutils/example-simple-test/username', 'Username to use'),
                                           ('/examples/coreutils/example-simple-test/password', 'Password to use'),
                                           ('/examples/coreutils/example-simple-test/ssl/server', 'Hostname of server to try SSL auth against'),
                                           ('/examples/coreutils/example-simple-test/ssl/username', 'Username to use for SSL auth'),
                                           ('/examples/coreutils/example-simple-test/ssl/password', 'Password to use for SSL auth'),
                                           ('/examples/coreutils/example-simple-test/tls/server', 'Hostname of server to try TLS auth against'),
                                           ('/examples/coreutils/example-simple-test/tls/username', 'Username to use for TLS auth'),
                                           ('/examples/coreutils/example-simple-test/tls/password', 'Password to use for TLS auth'),
                                           ('/stable-servers/ldap/hostname', 'Location of stable LDAP server to use')])
