
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import division

from threading import Thread, Event
from logging import getLogger
import tempfile
import os
import fcntl
import errno
from six.moves import queue

log = getLogger(__name__)


class _QueueAccess:

    def __init__(self, in_q, out_q):
        self.in_queue = in_q
        self.out_queue = out_q


class BkrThreadPool:

    _qpool = {}
    _tpool = {}

    def __init__(self):
        pass

    @classmethod
    def create_and_run(cls, name, target_f, target_args, num=30, *args, **kw):
        if name in cls._qpool:
            raise Exception('%s has already been initialised in the BkrThreadPool' % name)

        out_q = queue.Queue()
        in_q = queue.Queue()
        cls._qpool[name] = _QueueAccess(in_q, out_q)
        cls._tpool[name] = []
        for i in range(num):
            t = Thread(target=target_f, args=target_args)
            cls._tpool[name].append(t)
            t.setDaemon(False)
            t.start()

    @classmethod
    def get(self, name):
        return self._qpool[name]

    @classmethod
    def join(cls, name, timeout):
        tpool = cls._tpool[name]
        for t in tpool:
            t.join(timeout)
            if t.isAlive():
                log.warn('Thread %s did not shutdown cleanly' % t.ident)


class RepeatTimer(Thread):

    def __init__(self, interval, function, stop_on_exception=True, args=None, kwargs=None):
        Thread.__init__(self)

        if kwargs is None:
            kwargs = {}
        if args is None:
            args = []

        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.stop_on_exception = stop_on_exception
        self.finished = Event()

    def stop(self):
        self.done = True
        self.finished.set()

    def run(self):
        self.done = False
        while True:
            self.finished.wait(self.interval)
            if self.done:
                self.finished.clear()
                break
            if not self.finished.is_set():
                try:
                    self.function(*self.args, **self.kwargs)
                except Exception as e:
                    if self.stop_on_exception:
                        self.finished.clear()
                        raise
                    # TODO: Not strictly for auth'ing, think of something better
                    log.exception('Login Fail')
            self.finished.clear()


class SensitiveUnicode(unicode):
    def __repr__(self):
        return '<repr blocked>'

    def encode(self, *args, **kwargs):
        return SensitiveStr(super(SensitiveUnicode, self).encode(*args, **kwargs))


class SensitiveStr(str):
    def __repr__(self):
        return '<repr blocked>'

    def decode(self, *args, **kwargs):
        return SensitiveUnicode(super(SensitiveStr, self).decode(*args, **kwargs))


# Would be nice if Python did this for us: http://bugs.python.org/issue8604
class AtomicFileReplacement(object):
    """
    Replace a file atomically

    Easiest usage is as a context manager, but create_temp, destroy_temp
    and replace_dest can also be called directly if needed
    """

    def __init__(self, dest_path, mode=0o644):
        self.dest_path = dest_path
        self.mode = mode
        self._temp_info = None

    @property
    def temp_file(self):
        if not self._temp_info:
            msg = "Replacement for %r not yet created" % self.dest_path
            raise RuntimeError(msg)
        return self._temp_info[0]

    def create_temp(self):
        """Create the temporary file that may later be renamed"""
        dirname, basename = os.path.split(self.dest_path)
        fd, temp_path = tempfile.mkstemp(prefix='.' + basename, dir=dirname)
        try:
            f = os.fdopen(fd, 'w')
        except:
            os.unlink(temp_path)
            raise
        self._temp_info = f, fd, temp_path
        return f

    def destroy_temp(self):
        """Ensure the temporary file (if any) is destroyed"""
        temp_info = self._temp_info
        if temp_info is None:
            return
        f, fd, temp_path = temp_info
        try:
            os.unlink(temp_path)
        except:
            pass
        self._temp_info = None

    def replace_dest(self):
        """Move the temporary file to its final destination"""
        temp_info = self._temp_info
        if temp_info is None:
            msg = "Replacement for %r not yet created" % self.dest_path
            raise RuntimeError(msg)
        f, fd, temp_path = temp_info
        f.flush()
        os.fchmod(fd, self.mode)
        os.rename(temp_path, self.dest_path)
        self._temp_info = None

    def __enter__(self):
        return self.create_temp()

    def __exit__(self, exc_type, exc, exc_tb):
        if exc_type is None:
            self.replace_dest()
        else:
            self.destroy_temp()

# Backwards compatibility alias
atomically_replaced_file = AtomicFileReplacement


def atomic_link(source, dest):
    temp_path = tempfile.mktemp(prefix=os.path.basename(dest),
            dir=os.path.dirname(dest))
    os.link(source, temp_path)
    try:
        os.rename(temp_path, dest)
    except:
        # Clean up the temp file, but suppress any exception if the cleaning fails
        try:
            os.unlink(temp_path)
        finally:
            pass
        # Now re-raise the original exception
        raise


def atomic_symlink(source, dest):
    temp_path = tempfile.mktemp(prefix=os.path.basename(dest),
            dir=os.path.dirname(dest))
    os.symlink(source, temp_path)
    try:
        os.rename(temp_path, dest)
    except:
        # Clean up the temp file, but suppress any exception if the cleaning fails
        try:
            os.unlink(temp_path)
        finally:
            pass
        # Now re-raise the original exception
        raise


def makedirs_ignore(path, mode):
    """
    Creates the given directory (and any parents), but succeeds if it already
    exists.
    """
    try:
        os.makedirs(path, mode)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def siphon(src, dest):
    while True:
        chunk = src.read(4096)
        if not chunk:
            break
        dest.write(chunk)


def unlink_ignore(path):
    """
    Unlinks the given path, but succeeds if it doesn't exist.
    """
    try:
        os.unlink(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


class Flock(object):
    """
    Context manager which locks the given path using flock(2).
    """

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDONLY)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX)
        except:
            os.close(self.fd)
            raise

    def __exit__(self, type, value, traceback):
        os.close(self.fd)
        del self.fd


# This is a method on timedelta in Python 2.7+
def total_seconds(td):
    """
    Returns the total number of seconds (float)
    represented by the given timedelta.
    """
    return (float(td.microseconds) + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

