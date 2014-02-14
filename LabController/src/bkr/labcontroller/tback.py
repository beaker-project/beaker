# -*- coding: utf-8 -*-

# Copyright (c) 2009 Red Hat, Inc.
#
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# This is a copy and paste of kobo.tback version 0.4.2-1
import os
import sys
import traceback
import re

def get_traceback():
    """Return a traceback string."""
    exc_info = sys.exc_info()
    if exc_info[0] is None:
        return ""
    return "".join(traceback.format_exception(*exc_info)).replace(r"\n", "\n")


def get_exception():
    """Return an exception string."""
    result = sys.exc_info()[1]
    if result is None:
        return ""
    return str(result)


class Traceback(object):
    """Enhanced traceback with detailed output."""

    def __init__(self, exc_info=None, show_traceback=True, show_code=True, show_locals=True, show_environ=False, show_modules=False):
        self.exc_info = exc_info or sys.exc_info()
        self.show_traceback = show_traceback
        self.show_code = show_code
        self.show_locals = show_locals
        self.show_environ = show_environ
        self.show_modules = show_modules

    def _to_str(self, value, format=None):
        """Convert value to string.

        We must absolutely avoid propagating exceptions, and str(value)
        COULD cause any exception, so we MUST catch any...
        """

        format = format or "%s"
        try:
            result = format % value
        except:
            result = "<ERROR WHILE CONVERTING VALUE TO STRING>"
        return result

    def get_traceback(self):
        """Return a traceback string."""
        if self.exc_info[0] is None:
            return ""
        result = []

        if self.show_traceback:
            c_pattern = re.compile('\n')
            for i in traceback.format_exception(*self.exc_info):
                for line in c_pattern.split(i):
                    line and result.append(line)

        if self.show_environ:
            result.append("<ENVIRON>")
            for key, value in sorted(os.environ.iteritems()):
                result.append("%s = %s" % (self._to_str(key, "%20s"), self._to_str(value)))
            result.append("</ENVIRON>")

        if self.show_environ:
            result.append("<GLOBALS>")
            for key, value in sorted(os.environ.iteritems()):
                result.append("%s = %s" % (self._to_str(key, "%20s"), self._to_str(value)))
            result.append("</GLOBALS>")

        if self.show_modules:
            result.append("<MODULES>")
            for key, value in sorted(sys.modules.iteritems()):
                result.append("%s = %s" % (self._to_str(key, "%20"), self._to_str(value)))
            result.append("</MODULES>")

        if self.show_code or self.show_locals:
            for frame in reversed(self.get_frames()):
                if frame["filename"] == "?" or frame["lineno"] == "?":
                    continue

                result.append("Frame %s in %s at line %s" % (
                    self._to_str(frame["function"]),
                    self._to_str(frame["filename"]),
                    self._to_str(frame["lineno"]))
                )

                if self.show_code:
                    result.append("<CODE>")
                    lineno = frame["pre_context_lineno"]
                    for line in frame["pre_context"]:
                        result.append("    %s %s" % (self._to_str(lineno, "%4d"), self._to_str(line)))
                        lineno += 1

                    result.append("--> %s %s" % (self._to_str(lineno, "%4d"), self._to_str(frame["context_line"])))
                    lineno += 1

                    for line in frame["post_context"]:
                        result.append("    %s %s" % (self._to_str(lineno, "%4d"), self._to_str(line)))
                        lineno += 1
                    result.append("</CODE>")

                if self.show_locals:
                    result.append("<LOCALS>")
                    for key, value in sorted(frame["vars"]):
                        result.append("%20s = %s" % (self._to_str(key), self._to_str(value, "%.200r")))
                        if key == "self":
                            try:
                                variables = sorted(dir(value))
                            except Exception, ex:
                                # this exception may be thrown on xmlrpc proxy object
                                # e.g. <ServerProxy>.__dir__ will be handled as xmlrpc call,
                                # expected behaviour is that the call returns list of strings for the scope
                                variables = []
                            for obj_key in variables:
                                try:
                                    obj_value = getattr(value, obj_key)
                                except:
                                    result.append("%20s - uninitialized variable" % ("self." + self._to_str(obj_key)))
                                    continue
                                if obj_key.startswith("__"):
                                    continue
                                if callable(obj_value):
                                    continue
                                obj_value_str = self._to_str(obj_value, "%.200r")
                                result.append("%20s = %s" % ("self." + self._to_str(obj_key), obj_value_str))
                    result.append("</LOCALS>")
        s = u''

        for i in result:
            line = i.replace(r'\\n', '\n').replace(r'\n', '\n')

            if type(i) == unicode:
                s += i
            else:
                s += unicode(str(i), errors='replace')
            s += '\n'

        return s.encode('ascii', 'replace')

    def print_traceback(self):
        """Print a traceback string to stderr."""
        print >>sys.stderr, self.get_traceback()

    def _get_lines_from_file(self, filename, lineno, context_lines):
        # this function was taken from Django and adapted for CLI
        """
        Return context_lines before and after lineno from file.
        Return (pre_context_lineno, pre_context, context_line, post_context).
        """
        source = None
        try:
            f = open(filename)
            try:
                source = f.readlines()
            finally:
                f.close()
        except (OSError, IOError):
            pass

        if source is None:
            return None, [], None, []

        encoding = "ascii"
        for line in source[:2]:
            # File coding may be specified. Match pattern from PEP-263
            # (http://www.python.org/dev/peps/pep-0263/)
            match = re.search(r"coding[:=]\s*([-\w.]+)", line)
            if match:
                encoding = match.group(1)
                break
        source = [ unicode(sline, encoding, "replace") for sline in source ]

        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        pre_context = [ line.strip("\n") for line in source[lower_bound:lineno] ]
        context_line = source[lineno].strip("\n")
        post_context = [ line.strip("\n") for line in source[lineno+1:upper_bound] ]

        return lower_bound, pre_context, context_line, post_context


    def get_frames(self):
        # this function was taken from Django and adapted for CLI
        """Return a list with frame information."""
        tb = self.exc_info[2]

        frames = []
        while tb is not None:
            # support for __traceback_hide__ which is used by a few libraries to hide internal frames.
            if tb.tb_frame.f_locals.get("__traceback_hide__"):
                tb = tb.tb_next
                continue

            filename = tb.tb_frame.f_code.co_filename
            function = tb.tb_frame.f_code.co_name
            lineno = tb.tb_lineno - 1
            pre_context_lineno, pre_context, context_line, post_context = self._get_lines_from_file(filename, lineno, 7)
            if pre_context_lineno is not None:
                frames.append({
                    "tb": tb,
                    "filename": filename,
                    "function": function,
                    "lineno": lineno + 1,
                    "vars": tb.tb_frame.f_locals.items(),
                    "id": id(tb),
                    "pre_context": pre_context,
                    "context_line": context_line,
                    "post_context": post_context,
                    "pre_context_lineno": pre_context_lineno + 1,
                })
            tb = tb.tb_next

        if not frames:
            frames = [{
                "filename": "?",
                "function": "?",
                "lineno": "?",
            }]
        return frames


def set_except_hook(logger=None):
    """Replace standard excepthook method by an improved one."""
    def _hook(exctype, value, tb):
        tback = Traceback((exctype, value, tb))
        tback.show_locals = True
        logger and logger.error(tback.get_traceback())
        tback.print_traceback()
        print

    _hook.__doc__ = sys.excepthook.__doc__
    _hook.__name__ = sys.excepthook.__name__
    sys.excepthook = _hook
