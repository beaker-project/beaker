# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from datetime import date
from six.moves import StringIO

from bkr.client import wizard

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

EXPECTED_GPL_HEADER = ("Copyright (c) %s %s.\n" %
                       (date.today().year, wizard.LICENSE_ORGANISATION))

EXPECTED_OTHER_HEADER = ("Copyright (c) %s %s. All rights reserved.\n" %
                         (date.today().year, wizard.LICENSE_ORGANISATION))


class ShellEscapingTest(unittest.TestCase):

    def test_it(self):
        self.assertEqual(wizard.shellEscaped(r'a " ` $ ! \ z'), r'a \" \` \$ \! \\ z')


class LicenseTests(unittest.TestCase):

    def setUp(self):
        self.options = options = wizard.Options([], load_user_prefs=False)
        self.license = wizard.License(options)

    def test_default_is_gplv2_or_later(self):
        self.assertEqual(self.license.data, "GPLv2+")

    def check_license_text(self, includes, excludes):
        text = self.license.get()
        for fragment in includes:
            self.assertIn(fragment, text)
        for fragment in excludes:
            self.assertNotIn(fragment, text)

    def test_gplv2_or_later_text(self):
        self.license.data = "GPLv2+"
        includes = (EXPECTED_GPL_HEADER, "version 2", "any later version")
        excludes = ("version 3",)
        self.check_license_text(includes, excludes)

    def test_gplv2_only_text(self):
        self.license.data = "GPLv2"
        includes = (EXPECTED_GPL_HEADER, "version 2")
        excludes = ("version 3", "any later version")
        self.check_license_text(includes, excludes)

    def test_gplv3_or_later_implicit_text(self):
        self.license.data = "GPLv3"
        includes = (EXPECTED_GPL_HEADER, "version 3", "any later version")
        excludes = ("version 2",)
        self.check_license_text(includes, excludes)

    def test_gplv3_or_later_explicit_text(self):
        self.license.data = "GPLv3+"
        includes = (EXPECTED_GPL_HEADER, "version 3", "any later version")
        excludes = ("version 2",)
        self.check_license_text(includes, excludes)

    def test_explicit_other_text(self):
        self.license.data = "other"
        includes = (EXPECTED_OTHER_HEADER, "PROVIDE YOUR LICENSE TEXT")
        self.check_license_text(includes, ())

    def test_unknown_other_text(self):
        self.license.data = "this is not a valid license selector"
        includes = (EXPECTED_OTHER_HEADER, "PROVIDE YOUR LICENSE TEXT")
        self.check_license_text(includes, ())

    def test_custom_other_text(self):
        # use one of the dummy licenses in the template
        self.license.data = "GPLvX"
        includes = (EXPECTED_OTHER_HEADER, "This is GPLvX license text.")
        self.check_license_text(includes, ())


class ArchitecturesTest(unittest.TestCase):

    def setUp(self):
        self.options = wizard.Options([], load_user_prefs=False)
        self.archs = wizard.Architectures(self.options)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1095079
    def test_contain_aarch64(self):
        self.assertIn('aarch64', self.archs.list)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1120487
    def test_contain_ppc64le(self):
        self.assertIn('ppc64le', self.archs.list)


class BugsTest(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=902299
    def test_security_info_removed_from_summary(self):
        bzbug = Mock(
            summary='CVE-2012-5660 EMBARGOED abrt: Race condition in '
                    'abrt-action-install-debuginfo',
            bug_id=887866,
        )
        options = wizard.Options(['beaker-wizard', 'CVE-2012-5660'],
                                 load_user_prefs=False)
        bugs = wizard.Bugs(options)
        bugs.bug = bzbug
        self.assertEqual(
            'abrt: Race condition in abrt-action-install-debuginfo',
            bugs.getSummary())


class DescTest(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1165754
    def test_shell_metachars_escaped_in_makefile(self):
        options = wizard.Options(['beaker-wizard', '--yes'], load_user_prefs=False)
        desc = wizard.Desc(options, suggest="Test for BZ#1234567 "
                                            "(I ran `rm -rf ~` and everything's gone suddenly)")
        self.assertEqual(
            """\n            \t@echo "Description:     Test for BZ#1234567 (I ran \`rm -rf ~\` and everything's gone suddenly)" >> $(METADATA)""",
            desc.formatMakefileLine())


class ReleasesTest(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1131429
    def test_default_excludes_rhel4_rhel5(self):
        self.options = options = wizard.Options([], load_user_prefs=False)
        self.releases = wizard.Releases(options)
        self.assertEqual(self.releases.data,
                         ['-RHEL4', '-RHELClient5', '-RHELServer5'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1704804
    def test_long_spelled_out_RHEL_Name(self):
        self.options = options = wizard.Options(['beaker-wizard', '-r', 'RedHatEnterpriseLinux8'],
                                                load_user_prefs=False)
        self.releases = wizard.Releases(options)
        self.assertEqual(self.releases.data,
                ['RedHatEnterpriseLinux8'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1704804
    def test_dashes_and_underscore(self):
        self.options = options = wizard.Options(['beaker-wizard', '-r', 'Fedora-Cloud21-Alpha'],
                                                load_user_prefs=False)
        self.releases = wizard.Releases(options)
        self.assertEqual(self.releases.data,
                ['Fedora-Cloud21-Alpha'])


class TypeTest(unittest.TestCase):

    @patch('sys.stdout', new_callable=StringIO)
    def test_prints_full_heading(self, cpt_stdout):
        type = wizard.Type()
        type.heading()
        cpt_stdout.seek(0)
        printout = cpt_stdout.read()
        self.assertRegexpMatches(printout, r'\bWhat is the type of test?\b')
        self.assertRegexpMatches(printout, r'\bRecommended values\b')
        self.assertRegexpMatches(printout, r'\bPossible values\b')
