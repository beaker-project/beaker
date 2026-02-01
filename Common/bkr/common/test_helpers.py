# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
import tempfile
import unittest

import six

from bkr.common.helpers import AtomicFileReplacement, siphon
from bkr.common.helpers_six import parse_content_type


class ParsingContentType(unittest.TestCase):

    def test_ok(self):
        self.assertEqual(parse_content_type('type/subtype; charset=utf-8'), 'type/subtype')
        self.assertEqual(parse_content_type('type/subtype'), 'type/subtype')

    def test_empty(self):
        self.assertEqual(parse_content_type(''), '')


class TestSiphon(unittest.TestCase):

    def test_siphon_text_to_text_file(self):
        src = six.StringIO(u'hello world')
        dest = six.StringIO()
        siphon(src, dest)
        self.assertEqual(dest.getvalue(), u'hello world')

    def test_siphon_binary_to_binary_file(self):
        binary_data = b'\x00\x01\xcd\xfe\xff' * 1000
        src = six.BytesIO(binary_data)
        tmp = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        try:
            siphon(src, tmp)
            tmp.close()
            with open(tmp.name, 'rb') as f:
                self.assertEqual(f.read(), binary_data)
        finally:
            os.unlink(tmp.name)


class TestAtomicFileReplacement(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_text_mode(self):
        dest_path = os.path.join(self.tmpdir, 'textfile')
        with AtomicFileReplacement(dest_path) as f:
            f.write(u'hello')
        with open(dest_path, 'r') as f:
            self.assertEqual(f.read(), 'hello')

    def test_binary_mode(self):
        binary_data = b'\x00\x01\xcd\xfe\xff'
        dest_path = os.path.join(self.tmpdir, 'binfile')
        with AtomicFileReplacement(dest_path, binary=True) as f:
            f.write(binary_data)
        with open(dest_path, 'rb') as f:
            self.assertEqual(f.read(), binary_data)
