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
            'Oops - bad mode' # jbastian example bz:1538906
        ]

        # From bz:1538906
        self.test_case_name_oops = 'regression-bz123456789-Oops-when-some-thing-happens-'
        self.fake_panic = 'I can\'t believe it\'s not a panic'
        self.acceptable_panic_matches = ['Oops:', 'Oops ', 'Oops[']

    def test_panic_detector_detects_correctly(self):
        for line in self.should_panic:
            self.panic_detector.fired = False
            match = self.panic_detector.feed(line)
            self.assertTrue(self.panic_detector.fired,
                        "Failed to detect: %r" % (line))
            self.assertTrue(match in self.acceptable_panic_matches,
                        "%r is not an acceptable match. Line: %r" % (match, line))

    def test_panic_not_detected_for_random_string(self):
        match = self.panic_detector.feed(self.fake_panic)
        self.assertFalse(self.panic_detector.fired,
                         "Panic detector erroneously detected: %r" % (self.fake_panic))
        self.assertIsNone(match,
                          "feed result ( %r ) wasn't NoneType" % (match))

    def test_panic_not_detected_for_test_case_name_containing_oops(self):
        match = self.panic_detector.feed(self.test_case_name_oops)
        self.assertFalse(self.panic_detector.fired,
                         "Panic detector erroneously detected: %r" % (self.test_case_name_oops))
        self.assertIsNone(match,
                          "feed result ( %r ) wasn't NoneType" % (match))
