
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import os.path
import re
import shutil
import tempfile
import unittest2 as unittest

from bkr.inttest.client import run_wizard


class BaseWizardTestCase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)

class TestWizard(BaseWizardTestCase):

    def test_shows_help_successfully(self):
        out = run_wizard(['beaker-wizard', '--help'])
        self.assertRegexpMatches(out, re.compile(r'\bBeaker Wizard\b', re.I), out)

    def test_shows_help_with_nonexistend_command(self):
        """Tests that we don't get a traceback if the user invokes the wizard
        with a nonexistend command."""
        out = run_wizard(['beaker-wizard', 'bogus', '--help'], cwd=self.tempdir)
        self.assertRegexpMatches(out, re.compile(r'\bBeaker Wizard\b', re.I), out)

    def test_wizard_guesses_package_from_cwd(self):
        # When run with no args, beaker-wizard guesses the package from the cwd 
        # and uses defaults for everything else.
        package = 'bash'
        test_path = os.path.join(self.tempdir, package)
        os.mkdir(test_path)

        out = run_wizard(['beaker-wizard'], cwd=test_path)
        self.assertIn('Package : %s' % package, out)

    def test_wizard_guesses_values_from_test_name(self):
        # When given a test name, beaker-wizard creates its output in that 
        # subdirectory and also guesses some values based on the directory 
        # structure. Here we cover each of the possibilities described in the 
        # man page.

        # TESTNAME
        out = run_wizard(['beaker-wizard', 'test-it-works'], cwd=self.tempdir)
        self.assertIn('Test name : test-it-works', out)

        # TYPE/TESTNAME
        out = run_wizard(['beaker-wizard', 'Sanity/test-it-works'], cwd=self.tempdir)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Test name : test-it-works', out)

        # TYPE/PATH/TESTNAME
        out = run_wizard(['beaker-wizard', 'Sanity/http/test-it-works'], cwd=self.tempdir)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Relative path : http', out)
        self.assertIn('Test name : test-it-works', out)

        # PACKAGE/TYPE/NAME
        out = run_wizard(['beaker-wizard', 'wget/Sanity/test-it-works'], cwd=self.tempdir)
        self.assertIn('Package : wget', out)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Relative path : None', out)
        self.assertIn('Test name : test-it-works', out)

        # PACKAGE/TYPE/PATH/NAME
        out = run_wizard(['beaker-wizard', 'wget/Sanity/http/test-it-works'], cwd=self.tempdir)
        self.assertIn('Package : wget', out)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Relative path : http', out)
        self.assertIn('Test name : test-it-works', out)

        # NAMESPACE/PACKAGE/TYPE/NAME
        out = run_wizard(['beaker-wizard', 'distribution/wget/Sanity/test-it-works'], cwd=self.tempdir)
        self.assertIn('Namespace : distribution', out)
        self.assertIn('Package : wget', out)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Relative path : None', out)
        self.assertIn('Test name : test-it-works', out)

        # NAMESPACE/PACKAGE/TYPE/PATH/NAME
        out = run_wizard(['beaker-wizard', 'distribution/wget/Sanity/http/test-it-works'], cwd=self.tempdir)
        self.assertIn('Namespace : distribution', out)
        self.assertIn('Package : wget', out)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Relative path : http', out)
        self.assertIn('Test name : test-it-works', out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1184907
    def test_creates_successfully_custom_test_type(self):
        out = run_wizard(['beaker-wizard', 'http/test1'], cwd=self.tempdir)
        self.assertIn('Test type : http', out)
        self.assertIn('Relative path : None', out)
        self.assertIn('Test name : test1', out)
