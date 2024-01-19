# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# We are talking about job logs here, not logs produced by the daemons.

import errno
import os
import os.path

from bkr.common.helpers import makedirs_ignore


class LogFile(object):
    def __init__(self, path, register_func, create=True):
        self.path = path  #: absolute path where the log will be stored
        self.register_func = register_func  #: called only if the file was created
        self.create = create  #: create the file if it doesn't exist

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path)

    def open_ro(self):
        """
        If you just want to read the log, call this instead of entering the context manager.
        """
        return open(self.path, "r")

    def __enter__(self):
        makedirs_ignore(os.path.dirname(self.path), 0o755)
        created = False
        if self.create:
            try:
                # stdio does not have any mode string which corresponds to this
                # combination of flags, so we have to use raw os.open :-(
                fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644)
                created = True
            except (OSError, IOError) as e:
                if e.errno != errno.EEXIST:
                    raise
                fd = os.open(self.path, os.O_RDWR)
        else:
            fd = os.open(self.path, os.O_RDWR)
        try:
            self.f = os.fdopen(fd, "r+")
        except Exception:
            os.close(fd)
            raise
        try:
            if created:
                # first time we have touched this file, need to register it
                self.register_func()
            return self
        except Exception:
            self.f.close()
            del self.f
            raise

    def __exit__(self, type, value, traceback):
        self.f.close()
        del self.f

    def truncate(self, size):
        self.f.truncate(size)

    def update_chunk(self, data, offset):
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        self.f.seek(offset, os.SEEK_SET)
        # XXX the original uploadFile acquires an exclusive lock while writing,
        # for no reason that I can discern
        self.f.write(data)
        self.f.flush()


class LogStorage(object):

    """
    Handles storage of job logs on the local filesystem.

    The old XML-RPC API doesn't include the recipe ID with the task or result
    upload calls. So for now, everything is stored flat. Eventually it would be
    nice to arrange things hierarchically with everything under recipe instead.
    """

    def __init__(self, base_dir, base_url, hub):
        self.base_dir = base_dir
        if not base_url.endswith("/"):
            base_url += "/"  # really it is always a directory
        self.base_url = base_url
        self.hub = hub

    def recipe(self, recipe_id, path, create=True):
        path = os.path.normpath(path.lstrip("/"))
        if path.startswith("../"):
            raise ValueError("Upload path not allowed: %s" % path)
        recipe_base_dir = os.path.join(
            self.base_dir, "recipes", (recipe_id[:-3] or "0") + "+", recipe_id, ""
        )
        recipe_base_url = "%srecipes/%s+/%s/" % (
            self.base_url,
            recipe_id[:-3] or "0",
            recipe_id,
        )
        return LogFile(
            os.path.join(recipe_base_dir, path),
            lambda: self.hub.recipes.register_file(
                recipe_base_url,
                recipe_id,
                os.path.dirname(path),
                os.path.basename(path),
                recipe_base_dir,
            ),
            create=create,
        )

    def task(self, task_id, path, create=True):
        path = os.path.normpath(path.lstrip("/"))
        if path.startswith("../"):
            raise ValueError("Upload path not allowed: %s" % path)
        task_base_dir = os.path.join(
            self.base_dir, "tasks", (task_id[:-3] or "0") + "+", task_id, ""
        )
        task_base_url = "%stasks/%s+/%s/" % (
            self.base_url,
            task_id[:-3] or "0",
            task_id,
        )
        return LogFile(
            os.path.join(task_base_dir, path),
            lambda: self.hub.recipes.tasks.register_file(
                task_base_url,
                task_id,
                os.path.dirname(path),
                os.path.basename(path),
                task_base_dir,
            ),
            create=create,
        )

    def result(self, result_id, path, create=True):
        path = os.path.normpath(path.lstrip("/"))
        if path.startswith("../"):
            raise ValueError("Upload path not allowed: %s" % path)
        result_base_dir = os.path.join(
            self.base_dir, "results", (result_id[:-3] or "0") + "+", result_id, ""
        )
        result_base_url = "%sresults/%s+/%s/" % (
            self.base_url,
            result_id[:-3] or "0",
            result_id,
        )
        return LogFile(
            os.path.join(result_base_dir, path),
            lambda: self.hub.recipes.tasks.register_result_file(
                result_base_url,
                result_id,
                os.path.dirname(path),
                os.path.basename(path),
                result_base_dir,
            ),
            create=create,
        )
