# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest

from bkr.labcontroller.config import _conf
from bkr.labcontroller.proxy import PanicDetector


class TestPanicDetector(unittest.TestCase):

    def setUp(self):
        self.conf = _conf
        self.panic_detector = PanicDetector(self.conf["PANIC_REGEX"])

        self.should_panic = [
            'Internal error: Oops - BUG: 0 [#2] PREEMPT ARM', # oops.kernel.org examples
            'Oops: 0000 [#1] SMP\\',
            'Oops[#1]',
            'Oops - bad mode', # jbastian example bz:1538906
            'kernel BUG at fs/ext4/super.c:1022!' # xifeng example bz:1778643
        ]

        # From bz:1538906
        self.should_not_panic = [
            'regression-bz123456789-Oops-when-some-thing-happens-',
            'I can\'t believe it\'s not a panic',
            'looking for a kernel BUG at my setup!'
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
