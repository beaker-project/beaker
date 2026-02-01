# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest

import six

from bkr.common.helpers import SensitiveUnicode
from bkr.labcontroller.provision import build_power_env


class TestBuildPowerEnv(unittest.TestCase):
    def test_build_power_env(self):
        t_command = {
            "power": {
                "address": u"192.168.1.1",
                "id": u"42",
                "user": u"root",
                "passwd": SensitiveUnicode(u"toor"),
            },
            "action": u"reboot",
        }

        expected = {
            "power_address": "192.168.1.1",
            "power_id": "42",
            "power_user": "root",
            "power_pass": "toor",
            "power_mode": "reboot",
        }

        actual = build_power_env(t_command)

        for key, value in six.iteritems(expected):
            self.assertEqual(expected[key], actual[key])

    def test_build_power_env_with_missing_fields(self):
        t_command = {
            "power": {"address": u"192.168.1.1", "passwd": SensitiveUnicode(u"toor")},
            "action": u"reboot",
        }

        expected = {
            "power_address": "192.168.1.1",
            "power_id": "",
            "power_user": "",
            "power_pass": "toor",
            "power_mode": "reboot",
        }

        actual = build_power_env(t_command)

        for key, value in six.iteritems(expected):
            self.assertEqual(expected[key], actual[key])

    def test_build_power_env_with_none_values(self):
        t_command = {
            "power": {
                "address": u"/var/run/docker.sock",
                "id": u"beaker-machine-1",
                "user": None,
                "passwd": None,
            },
            "action": u"interrupt",
        }

        actual = build_power_env(t_command)

        self.assertEqual(actual["power_user"], "")
        self.assertEqual(actual["power_pass"], "")
        self.assertEqual(actual["power_address"], "/var/run/docker.sock")
        self.assertEqual(actual["power_id"], "beaker-machine-1")
        self.assertEqual(actual["power_mode"], "interrupt")
        for key, value in six.iteritems(actual):
            self.assertIsInstance(value, str,
                                 "env[%r] is %r, expected str" % (key, value))
