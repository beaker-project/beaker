# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest

from bkr.labcontroller.config import _conf
from bkr.labcontroller.proxy import PanicDetector, ConsoleLogHelper, InstallFailureDetector


class TestPanicDetector(unittest.TestCase):

    def setUp(self):
        self.conf = _conf
        self.panic_detector = PanicDetector(self.conf["PANIC_REGEX"])

        self.should_panic = [
            b'Internal error: Oops - BUG: 0 [#2] PREEMPT ARM', # oops.kernel.org examples
            b'Oops: 0000 [#1] SMP\\',
            b'Oops[#1]',
            b'Oops - bad mode', # jbastian example bz:1538906
            b'kernel BUG at fs/ext4/super.c:1022!' # xifeng example bz:1778643
        ]

        # From bz:1538906
        self.should_not_panic = [
            b'regression-bz123456789-Oops-when-some-thing-happens-',
            b'I can\'t believe it\'s not a panic',
            b'looking for a kernel BUG at my setup!'
        ]

        self.acceptable_panic_matches = ['Oops:', 'Oops ', 'Oops[',
            'kernel BUG at fs/ext4/super.c:1022!']

    def test_panic_detector_detects_correctly(self):
        for line in self.should_panic:
            self.panic_detector.fired = False
            match = self.panic_detector.feed(line)
            self.assertTrue(self.panic_detector.fired,
                        "Failed to detect: %r" % (line))
            self.assertTrue(match in self.acceptable_panic_matches,
                        "%r is not an acceptable match. Line: %r" % (match, line))

    def test_panic_detector_ignores_false_panic(self):
        for line in self.should_not_panic:
            match = self.panic_detector.feed(line)
            self.assertFalse(self.panic_detector.fired,
                            "Panic detector erroneously detected: %r" % (line))
            self.assertIsNone(match,
                            "feed result ( %r ) wasn't NoneType" % (match))


class TestConsoleLogHelper(unittest.TestCase):

    def test_strip_cntrl_regex(self):
        helper = ConsoleLogHelper(
            watchdog={'recipe_id': 1},
            proxy=None,
            panic=_conf["PANIC_REGEX"],
        )
        self.assertIsNone(helper.strip_cntrl.search(b'\t'))
        self.assertIsNone(helper.strip_cntrl.search(b'\n'))
        self.assertIsNotNone(helper.strip_cntrl.search(b'\x00'))
        self.assertIsNotNone(helper.strip_cntrl.search(b'\x01'))
        self.assertIsNotNone(helper.strip_cntrl.search(b'\x7f'))


class TestInstallFailureDetector(unittest.TestCase):

    def test_loads_patterns(self):
        detector = InstallFailureDetector()
        self.assertTrue(len(detector.patterns) > 0)

    def test_detects_dracut_failure(self):
        detector = InstallFailureDetector()
        match = detector.feed(
            b'dracut-initqueue[123]: Warning: /dev/root does not exist')
        self.assertTrue(detector.fired)
        self.assertIsNotNone(match)

    def test_ignores_normal_output(self):
        detector = InstallFailureDetector()
        match = detector.feed(b'Starting installation process')
        self.assertFalse(detector.fired)
        self.assertIsNone(match)
