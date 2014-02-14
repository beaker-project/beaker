
# vim: set fileencoding=utf-8 :

# Beaker
#
# Copyright (C) 2010 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import unittest
from bkr.server.util import unicode_truncate

class UnicodeTruncateTest(unittest.TestCase):

    def self_test_doesnt_mangle_short_values(self):
        s = u'a\u044f\u044f\u044f\u044f'
        self.assertEqual(unicode_truncate(s, bytes_length=100), s)

    def self_test_truncates_on_character_boundaries(self):
        s = u'a\u044f\u044f\u044f\u044f'
        self.assertEqual(unicode_truncate(s, bytes_length=4), u'a\u044f')
