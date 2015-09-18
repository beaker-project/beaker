
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

    def test_wizard_matches_correct_namespace(self):
        namespace = 'CoreOS'
        namespace_path = os.path.join(self.tempdir, namespace)
        os.mkdir(namespace_path)

        out = run_wizard(['beaker-wizard'], cwd=namespace_path)
        self.assertRegexpMatches(out, re.compile(r'\bNamespace\b.*%s' % namespace, re.I), out)


class TestTypesTest(BaseWizardTestCase):

    def create_basedir(self, dirs=None):
        if dirs is None:
            dirs = ['CoreOS', 'wget']
        basedir = os.path.join(self.tempdir, *dirs)
        os.makedirs(basedir)
        return basedir

    def assertRegexpInMakefile(self, regexp, basedir):
        makefile_path = os.path.join(basedir, 'Makefile')
        with open(makefile_path, 'r') as f:
            contents = f.read()
            self.assertRegexpMatches(contents, regexp, contents)

    def test_creates_successfully_custom_test_type(self):
        basedir = self.create_basedir()

        expected = ['mytesttype', 'test1']
        out = run_wizard(['beaker-wizard', os.path.join(*expected)], cwd=basedir)
        self.assertRegexpMatches(out, re.compile(r'\bwritten\b'))
        self.assertTrue(
            os.path.exists(os.path.join(basedir, *expected)), out
        )
        self.assertRegexpInMakefile(re.compile(r'Type:\s+%s' % expected[0]),
                                    os.path.join(basedir, *expected))

    def test_creates_default_test_type(self):
        basedir = self.create_basedir()

        expected = ['Library', 'test1']
        out = run_wizard(['beaker-wizard', os.path.join(*expected)], cwd=basedir)
        self.assertRegexpMatches(out, re.compile(r'\bwritten\b'))
        self.assertTrue(
            os.path.exists(os.path.join(basedir, *expected)), out
        )
