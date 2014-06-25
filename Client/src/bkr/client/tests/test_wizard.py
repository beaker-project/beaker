
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import date
import unittest2 as unittest
from bkr.client import wizard

EXPECTED_GPL_HEADER = ("Copyright (c) %s %s.\n" %
                           (date.today().year, wizard.LICENSE_ORGANISATION))

EXPECTED_OTHER_HEADER = ("Copyright (c) %s %s. All rights reserved.\n" %
                           (date.today().year, wizard.LICENSE_ORGANISATION))

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
