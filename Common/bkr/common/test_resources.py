# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest

from bkr.common.resources import (
    resource_stream,
    resource_string,
    resource_listdir,
    resource_exists,
    iter_entry_points,
)


class ResourceStreamTest(unittest.TestCase):
    def test_resource_stream_returns_readable_file_object(self):
        f = resource_stream("bkr.common", "schema/beaker-job.rng")
        try:
            data = f.read()
            self.assertIsInstance(data, bytes)
            self.assertGreater(len(data), 0)
            self.assertIn(b"<grammar", data)
        finally:
            f.close()


class ResourceStringTest(unittest.TestCase):
    def test_resource_string_returns_bytes(self):
        data = resource_string("bkr.common", "schema/beaker-job.rng")
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)
        self.assertIn(b"<grammar", data)


class ResourceListdirTest(unittest.TestCase):
    def test_resource_listdir_returns_list(self):
        entries = resource_listdir("bkr.common", "schema")
        self.assertIsInstance(entries, list)
        self.assertIn("beaker-job.rng", entries)
        self.assertIn("beaker-task.rng", entries)


class ResourceExistsTest(unittest.TestCase):
    def test_resource_exists_true_for_file(self):
        self.assertTrue(resource_exists("bkr.common", "schema/beaker-job.rng"))

    def test_resource_exists_true_for_directory(self):
        self.assertTrue(resource_exists("bkr.common", "schema"))

    def test_resource_exists_false(self):
        self.assertFalse(resource_exists("bkr.common", "schema/nonexistent.xyz"))


class IterEntryPointsTest(unittest.TestCase):
    def test_iter_entry_points_returns_iterable(self):
        eps = iter_entry_points("console_scripts")
        result = list(eps)
        self.assertIsInstance(result, list)

    def test_iter_entry_points_empty_group(self):
        eps = iter_entry_points("nonexistent.group.12345")
        result = list(eps)
        self.assertEqual(result, [])
