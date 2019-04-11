
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import socket
import unittest

import six

if six.PY2:
    from bkr.common import xmlrpc2 as xmlrpc_interface
if six.PY3:
    from bkr.common import xmlrpc3 as xmlrpc_interface


class DummyTransport:
    """
    Helper to test retry_request_decorator
    """
    def __init__(self):
        self.request_count = 0
        self.close_count = 0

    def request(self, hostname, failures=0):
        self.request_count += 1
        if self.request_count <= failures:
            raise socket.error
        return self.request_count

    def close(self):
        self.close_count += 1


class DummyLogger:
    """
    Helper to test retry_request_decorator
    """
    def __init__(self):
        self.messages = []

    def warning(self, message, *args, **kwds):
        self.messages.append((message, args, kwds))


class RetryTransportMixin:
    DEFAULT_RETRY_COUNT = 5

    def make_transport(self):
        return xmlrpc_interface.retry_request_decorator(DummyTransport)(
                retry_timeout=0.001)


class RetryTransportTestCase(RetryTransportMixin, unittest.TestCase):
    # Check with the standard library logger in place
    def test_default_retry_settings(self):
        transport = xmlrpc_interface.retry_request_decorator(DummyTransport)()
        self.assertEqual(transport.retry_count, self.DEFAULT_RETRY_COUNT)
        self.assertEqual(transport.retry_timeout, 30)

    def test_immediate_success(self):
        transport = self.make_transport()
        self.assertEqual(transport.retry_count, self.DEFAULT_RETRY_COUNT)
        self.assertEqual(transport.retry_timeout, 0.001)
        self.assertEqual(transport.request("dummy"), 1)

    def test_complete_failure(self):
        transport = self.make_transport()
        failure_count = self.DEFAULT_RETRY_COUNT + 1
        self.assertRaises(socket.error, transport.request, "dummy",
                          failures = failure_count)
        # BZ#1059079: Ensure the connection has been forcibly closed
        self.assertEqual(transport.close_count, failure_count)


class RetryTransportLoggingTestCase(RetryTransportMixin, unittest.TestCase):
    # Check we're logging the right things
    def setUp(self):
        self.orig_logger = xmlrpc_interface.logger
        self.logger = xmlrpc_interface.logger = DummyLogger()

    def tearDown(self):
        xmlrpc_interface.logger = self.orig_logger

    def test_immediate_success(self):
        transport = self.make_transport()
        self.assertEqual(transport.request("dummy"), 1)
        self.assertEqual(self.logger.messages, [])

    def get_retry_counts(self):
        return [args[2] for msg, args, kwds in self.logger.messages]

    def test_eventual_success(self):
        transport = self.make_transport()
        self.assertEqual(transport.request("dummy", failures=2), 3)
        max_retries = self.DEFAULT_RETRY_COUNT
        expected = list(range(max_retries, max_retries-2, -1))
        self.assertEqual(self.get_retry_counts(), expected)
        self.assertTrue(self.logger.messages[0][2]["exc_info"])

    def test_complete_failure(self):
        transport = self.make_transport()
        self.assertRaises(socket.error, transport.request, "dummy",
                          failures = self.DEFAULT_RETRY_COUNT + 1)
        expected = list(range(self.DEFAULT_RETRY_COUNT, 0, -1))
        self.assertEqual(self.get_retry_counts(), expected)
