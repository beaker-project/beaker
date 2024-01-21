# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import signal
import subprocess
import time
import unittest

import gevent
import psutil

from bkr.labcontroller.concurrency import (
    MonitoredSubprocess,
    _kill_process_group,
    _read_from_pipe,
)

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch


class TestReadFromPipe(unittest.TestCase):
    @patch("fcntl.fcntl", MagicMock())
    @patch("gevent.socket.wait_read", MagicMock())
    def test_read_normal(self):
        mock_file = MagicMock()
        mock_file.read.side_effect = [b"foo", b"bar", b""]

        result = _read_from_pipe(mock_file)
        expected_result = "foobar"
        self.assertEqual(result, expected_result)

    @patch("fcntl.fcntl", MagicMock())
    @patch("gevent.socket.wait_read", MagicMock())
    def test_read_discarding(self):
        mock_file = MagicMock()
        mock_file.read.side_effect = (
            [b"a" * 4096] * 1001 + [b"This line shouldn't be in output"] + [b""]  # EOT
        )

        result = _read_from_pipe(mock_file)

        expected_result = "a" * 4096 * 1000 + "+++ DISCARDED"
        self.assertEqual(result, expected_result)


class TestKillProcessGroup(unittest.TestCase):
    @patch("os.killpg")
    @patch("gevent.sleep", MagicMock())
    def test_kill_process_group(self, mock_killpg):
        t_pgid = 12345

        _kill_process_group(t_pgid)

        # Verify that SIGTERM and SIGKILL are both called
        expected_calls = [((t_pgid, signal.SIGTERM),), ((t_pgid, signal.SIGKILL),)]
        self.assertEqual(mock_killpg.call_args_list, expected_calls)


class SubprocessTest(unittest.TestCase):
    def _assert_child_is_process_group_leader(self, p):
        self.assertEqual(os.getpgid(p.pid), p.pid)

    def _assert_process_group_is_removed(self, pgid):
        processes_in_group = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if os.getpgid(proc.pid) == pgid:
                    processes_in_group.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass

        gone, alive = psutil.wait_procs(processes_in_group, timeout=10)

        self.assertEqual([], alive)

    def test_runaway_output_is_discarded(self):
        def _test():
            p = MonitoredSubprocess(
                ["seq", "--format=%0.0f cans of spam on the wall", str(8096 * 8096)],
                stdout=subprocess.PIPE,
                timeout=5,
            )
            p.dead.wait()
            out = p.stdout_reader.get()
            self.assertEqual(p.returncode, -signal.SIGTERM)
            self.assertTrue(len(out) <= 4096013, len(out))
            self.assertTrue(out.endswith("+++ DISCARDED"), out[:-10240])

        greenlet = gevent.spawn(_test)
        gevent.wait()
        greenlet.get(block=False)

    def test_timeout_is_enforced(self):
        def _test():
            p = MonitoredSubprocess(["sleep", "10"], timeout=1)
            p.dead.wait()
            self.assertEqual(p.returncode, -signal.SIGTERM)

        greenlet = gevent.spawn(_test)
        gevent.wait()
        greenlet.get(block=False)

    def test_child_is_process_group_leader(self):
        def _test():
            p = MonitoredSubprocess(["sleep", "1"], timeout=2)
            self._assert_child_is_process_group_leader(p)
            p.dead.wait()

        greenlet = gevent.spawn(_test)
        gevent.wait()
        greenlet.get(block=False)

    def test_process_group_is_killed_on_leader_timeout(self):
        # This test makes the following process tree:
        #
        #           MonitoredSubprocess
        #                  |
        #                  |
        #                 bash
        #                 /  \
        #                /    \
        #               /      \
        #           sleep 10   bash
        #                        |
        #                        |
        #                     sleep 30
        #
        # The process group leader should timeout, and everything in the
        # process group should be terminated/killed.
        def _test():
            p = MonitoredSubprocess(
                ["bash", "-c", "{ sleep 30 ; } & sleep 10"], timeout=1
            )
            # The rest of this test hinges on this assertion
            self._assert_child_is_process_group_leader(p)
            p.dead.wait()
            self.assertIn(p.returncode, [-signal.SIGTERM, -signal.SIGKILL])
            self._assert_process_group_is_removed(p.pid)

        greenlet = gevent.spawn(_test)
        gevent.wait()
        greenlet.get(block=False)

    def test_orphan_child_is_killed_when_parent_exits(self):
        # This test makes the following process tree:
        #
        #           MonitoredSubprocess
        #                  |
        #                  |
        #                 bash
        #                 /  \
        #                /    \
        #               /      \
        #           sleep 1    bash
        #                        |
        #                        |
        #                     sleep 60
        #
        # These should all be in the same process group and should
        # all be killed when the process group leader exits normally.
        def _test():
            p = MonitoredSubprocess(
                ["bash", "-c", "{ sleep 60 ; } & sleep 1"], timeout=10
            )
            # The rest of this test hinges on this assertion
            self._assert_child_is_process_group_leader(p)
            p.dead.wait()
            self.assertEqual(p.returncode, 0)
            self._assert_process_group_is_removed(p.pid)

        greenlet = gevent.spawn(_test)
        gevent.wait()
        greenlet.get(block=False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=832250
    def test_reaper_race(self):
        def _test():
            procs = [MonitoredSubprocess(["true"], timeout=10) for _ in range(600)]
            for p in procs:
                p.dead.wait()

        greenlet = gevent.spawn(_test)
        gevent.wait()
        greenlet.get(block=False)
