# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Async utilities that should probably be in gevent.
"""

import errno
import fcntl
import logging
import os
import signal
import subprocess

import gevent.event
import gevent.hub
import gevent.socket
import six

logger = logging.getLogger(__name__)


# Based on code from gevent-subprocess:
# https://bitbucket.org/eriks5/gevent-subprocess/src/550405f060a5/src/gevsubprocess/pipe.py
def _read_from_pipe(f):
    fcntl.fcntl(f, fcntl.F_SETFL, os.O_NONBLOCK)
    chunks = []
    # Start discarding chunks read if we see too many. This will prevent
    # a runaway child process from using up all our memory.
    discarding = False
    while True:
        try:
            gevent.socket.wait_read(f.fileno())
            chunk = f.read(4096)
            if not chunk:
                break
            if not discarding:
                chunks.append(chunk)
                if len(chunks) >= 1000:
                    logger.error(
                        "Too many chunks read from fd %s, "
                        "child process is running amok?!",
                        f.fileno(),
                    )
                    chunks.append(b"+++ DISCARDED")
                    discarding = True
        except IOError as e:
            if e.errno != errno.EAGAIN:
                raise
    if six.PY3:
        # Keep data in bytes until the end to reduce memory footprint
        return b"".join(chunks).decode("utf-8")
    return "".join(chunks)


def _timeout_kill(p, timeout):
    gevent.sleep(timeout)
    _kill_process_group(p.pid)


def _kill_process_group(pgid):
    # Try SIGTERM first, then SIGKILL just to be safe
    try:
        os.killpg(pgid, signal.SIGTERM)
    except OSError as e:
        if e.errno != errno.ESRCH:
            raise
    else:
        gevent.sleep(1)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise


class MonitoredSubprocess(subprocess.Popen):

    """
    Subclass of subprocess.Popen with some useful additions:
        * 'dead' attribute: a gevent.event.Event which is set when the child
          process has terminated
        * if 'stdout' is subprocess.PIPE, a 'stdout_reader' attribute:
          a greenlet which reads and accumulates the child's stdout (fetch it
          by calling stdout_reader.get())
        * same for stderr
        * if a timeout is given, the child will be sent SIGTERM and then
          SIGKILL if it is still running after the timeout (in seconds) has
          elapsed
    """

    _running = []

    def __init__(self, *args, **kwargs):
        self._running.append(self)
        self.dead = gevent.event.Event()
        timeout = kwargs.pop("timeout", None)
        orig_preexec_fn = kwargs.get("preexec_fn", None)

        def preexec_fn():
            os.setpgid(0, 0)
            if orig_preexec_fn is not None:
                orig_preexec_fn()

        kwargs["preexec_fn"] = preexec_fn
        super(MonitoredSubprocess, self).__init__(*args, **kwargs)
        if kwargs.get("stdout") == subprocess.PIPE:
            self.stdout_reader = gevent.spawn(_read_from_pipe, self.stdout)
        if kwargs.get("stderr") == subprocess.PIPE:
            self.stderr_reader = gevent.spawn(_read_from_pipe, self.stderr)
        if timeout:
            self.timeout_killer = gevent.spawn(_timeout_kill, self, timeout)

    @classmethod
    def _sigchld_handler(cls, signum, frame):
        assert signum == signal.SIGCHLD
        # It's important that we do no real work in this signal handler,
        # because we could be invoked at any time (from any stack frame, in the
        # middle of anything) and we don't want to raise, or interfere with
        # anything else. So we just schedule the real work in a greenlet.
        gevent.spawn(cls._reap_children)

    @classmethod
    def _reap_children(cls):
        for child in list(cls._running):
            if child.poll() is not None:
                # Let's try SIGTERM, and then SIGKILL just to be safe
                cls._running.remove(child)
                _kill_process_group(child.pid)
                child.dead.set()
                if hasattr(child, "timeout_killer"):
                    child.timeout_killer.kill(block=False)


gevent.hub.get_hub()
# XXX dodgy: this signal handler has to be registered *after* the libev
# default loop is created by get_hub(), since libev registers its own
# (unused) SIGCHLD handler
signal.signal(signal.SIGCHLD, MonitoredSubprocess._sigchld_handler)
