
# encoding: utf8

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import os.path
import re
import shutil
import tempfile
import textwrap
import unittest

from bkr.inttest.client import run_wizard


class BaseWizardTestCase(unittest.TestCase):

    def setUp(self):
        base_tempdir = tempfile.mkdtemp()
        # Create a sub directory to avoid sending the wizard in an infinite
        # loop. The subdirectory will be treated as a package directory by the
        # wizard. Any invalid characters in the name will cause the wizard to
        # ask for a new name until provided by the user.
        self.tempdir = os.path.join(base_tempdir, 'dummy')
        os.mkdir(self.tempdir)
        self.addCleanup(shutil.rmtree, base_tempdir)

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=857090
    def test_rhtsrequired_option(self):
        out = run_wizard(['beaker-wizard', '-Q', 'library(perl/lib1)',
            'http/test-rhtsrequired'],
            cwd=self.tempdir)
        self.assertIn('Required RHTS tests/libraries : library(perl/lib1)', out)
        # assert if it's set properly in the Makefile
        makefile_contents = open(os.path.join(self.tempdir,
                'http', 'test-rhtsrequired', 'Makefile'), 'r').readlines()
        self.assertIn('\t@echo "RhtsRequires:    library(perl/lib1)" >> $(METADATA)\n',
                 makefile_contents)

    # https://bugzilla.redhat.com/show_bug.cgi?id=857090
    def test_rhtsrequires_in_skeleton_xml_tag(self):
        out = run_wizard(['beaker-wizard', '-s', 'skel1',
            'http/test-rhtsrequired'], cwd=self.tempdir)
        self.assertIn('Required RHTS tests/libraries : '
            'library(perl/lib1), library(scl/lib2)', out)
        # assert if it's set properly in the Makefile
        makefile_contents = open(os.path.join(self.tempdir,
                'http', 'test-rhtsrequired', 'Makefile'), 'r').readlines()
        self.assertIn('\t@echo "RhtsRequires:    '
                 'library(perl/lib1) library(scl/lib2)" >> $(METADATA)\n',
                 makefile_contents)

    # https://bugzilla.redhat.com/show_bug.cgi?id=923637
    def test_creates_parametrized_runtest(self):
        out = run_wizard(['beaker-wizard',
                          '-s', 'parametrized',
                          '-o', 'wget,curl',
                          '-q', 'httpd,nginx',
                          'wget/Sanity/test-it-works'], cwd=self.tempdir)

        runtest_contents = open(
            os.path.join(self.tempdir, 'Sanity', 'test-it-works', 'runtest.sh'), 'r').readlines()
        self.assertIn('PACKAGES=${PACKAGES:-curl wget}\n', runtest_contents)
        self.assertIn('REQUIRES=${REQUIRES:-httpd nginx wget}\n', runtest_contents)

    def test_wizard_creates_test_in_current_directory(self):
        out = run_wizard(['beaker-wizard',
                          '--current-directory',
                          'wget/Sanity/http/test-it-works'], cwd=self.tempdir)

        self.assertIn('File ./runtest.sh written', out)
        self.assertIn('File ./Makefile written', out)
        self.assertIn('File ./PURPOSE written', out)
        self.assertIn('Package : wget', out)
        self.assertIn('Test type : Sanity', out)
        self.assertIn('Relative path : http', out)
        self.assertIn('Test name : test-it-works', out)

        runtest_contents = open(
            os.path.join(self.tempdir, 'runtest.sh'), 'r').readlines()
        self.assertIn('PACKAGE="wget"\n', runtest_contents)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1491658
    def test_accepts_non_ascii_names(self):
        out = run_wizard(['beaker-wizard',
                          '--current-directory',
                          '-n', u'Gęśla Jaźń'.encode('utf8'),
                          '-m', 'gj@example.com'], cwd=self.tempdir)
        self.assertNotIn('is not a valid author', out)
        self.assertIn(u'Author : Gęśla Jaźń', out.decode('utf8'))
        makefile_contents = open(os.path.join(self.tempdir, 'Makefile')).readlines()
        self.assertIn(
                '\t@echo "Owner:           Gęśla Jaźń <gj@example.com>" > $(METADATA)\n',
                makefile_contents)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1607515
    def test_accepts_non_ascii_gecos(self):
        uid = os.geteuid()
        passwd_file = tempfile.NamedTemporaryFile(prefix='beaker-inttest-passwd-', delete=True)
        passwd_file.write(textwrap.dedent(u"""\
            svejk:x:{0}:{0}:Josef Švejk:/home/svejk:/sbin/nologin
            """.format(uid).encode('UTF-8')))
        passwd_file.flush()
        group_file = tempfile.NamedTemporaryFile(prefix='beaker-inttest-group-', delete=True)
        group_file.write(textwrap.dedent(u"""\
            svejk:x:{0}
            """.format(uid).encode('UTF-8')))
        group_file.flush()

        # The bug only occurs on "first run", where beaker-wizard prompts you if
        # the default author name (which it pulls from the GECOS field of
        # passwd) is acceptable.
        out = run_wizard(['beaker-wizard', 'wget/Sanity/test-it-works'],
                         cwd=self.tempdir,
                         extra_env={'BEAKER_WIZARD_CONF': 'some-nonexistent-filename',
                                    'LD_PRELOAD': 'libnss_wrapper.so',
                                    'NSS_WRAPPER_PASSWD': passwd_file.name,
                                    'NSS_WRAPPER_GROUP': group_file.name})
        self.assertIn(u'Author : Josef Švejk', out.decode('utf8'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1624909
    def test_cve_number_syntax_change(self):
        out = run_wizard(['beaker-wizard',
                          '--current-directory',
                          'wget/Sanity/http/test-it-works',
                          'CVE-2018-123456789'])
        self.assertIn('Bug or CVE numbers : CVE-2018-123456789', out)
        self.assertNotIn('2018-123456789 is not a valid bug or cve number', out)
