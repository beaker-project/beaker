# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Copy and pasted from kobo.conf, from kobo 0.4.2-1

"""
Python-like syntax config parser.

USAGE:
    settings = PyConfigParser()
    settings.load_from_{conf, dict, file, string}(...)
    print settings[var]

CONFIG FILE SYNTAX:
PyConfigParser accepts following python-like syntax:
 - variable = <str, int, float, dict, list, tuple>
 - variable = <other_variable>
 - formatting strings can be used:
   - variable = "%s %s" % (var1, var2)
   - variable = "%(key1)s %(key2)s" % <dict>
 - imports are supported:
   - from <file_without_suffix> import *
   - from <file_without_suffix> import var1, var2
"""

from __future__ import print_function

import os
import fnmatch
import itertools
import keyword
import token
import tokenize
import six
from six.moves import StringIO

class ImproperlyConfigured(Exception):
    """
    Program is improperly configured.
    """
    pass

def get_dict_value(dictionary, key):
    """
    Return a value from a dictionary, if not found,
    use 'glob' keys (*, ? metachars), then use default value with '*' key.
    """
    if dictionary is None:
        return None

    if type(dictionary) is not dict:
        raise TypeError("Dictionary expected, got %s." % type(dictionary))

    try:
        return dictionary[key]
    except KeyError:
        if isinstance(key, str):
            matches = []
            for pattern in six.iterkeys(dictionary):
                if pattern == '*' or not isinstance(pattern, str):
                    # exclude '*', because it would match every time
                    continue
                if fnmatch.fnmatchcase(key, pattern):
                    matches.append(pattern)
            if len(matches) == 1:
                return dictionary[matches[0]]
            elif len(matches) > 1:
                raise KeyError("Key matches multiple values: %s" % key)
        if '*' in dictionary:
            return dictionary['*']
        raise


class PyConfigParser(dict):
    """
    Python-like syntax config parser.
    """

    get_dict_value = staticmethod(get_dict_value)

    def __init__(self, config_file_suffix="conf", debug=False):
        self._tok_number = None
        self._tok_value = None
        self._tok_begin = None
        self._tok_end = None
        self._tok_line = None
        self._tok_name = None
        self._config_file_suffix = config_file_suffix
        self._debug = debug
        self._open_file = None
        self._tokens = None

    def __getitem__(self, name):
        if name.startswith("_"):
            raise KeyError(name)
        return dict.__getitem__(self, name)

    def __setitem__(self, name, value):
        if name.startswith("_"):
            raise KeyError(name)
        return dict.__setitem__(self, name, value)

    def load_from_file(self, file_name):
        """
        Load data data from a file.
        """
        fo = open(file_name, "r")
        data = fo.read()
        fo.close()
        self._open_file = file_name
        self.load_from_string(data)

    def load_from_string(self, input_string):
        """
        Load data from a string.
        """
        if input_string:
            self._tokens = tokenize.generate_tokens(StringIO(input_string).readline)
            for key, value in self._parse():
                self[key] = value

    def load_from_dict(self, input_dict):
        """
        Load data from a dictionary.
        """
        if input_dict is not None:
            self.update(input_dict)

    def load_from_conf(self, conf):
        """
        Load data from another config.
        """
        self.load_from_dict(conf)

    def _parse(self):
        """
        Parse config file and store results to this object.
        """
        while True:
            self._get_token()

            if self._tok_value == "from":
                self._get_from_import()
                continue

            if keyword.iskeyword(self._tok_value):
                raise SyntaxError("Cannot assign to a python keyword: %s" % self._tok_value)

            if self._tok_name == "ENDMARKER":
                break

            self._assert_token(("NAME", ))
            key = self._tok_value

            self._get_token()
            self._assert_token(("OP", "="))

            value = self._get_value()
            yield key, value

    def _assert_token(self, *args):
        """
        Check if token has proper name and value.

        *args are tuples (name, value), (name, )
        """
        for i in args:
            if len(i) == 1 and i == (self._tok_name, ):
                return
            if len(i) == 2 and i == (self._tok_name, self._tok_value):
                return
        raise SyntaxError("Invalid syntax: file: %s, begin: %s, end: %s, text: %s" % (self._open_file, self._tok_begin, self._tok_end, self._tok_line))

    def _get_token(self, skip_newline=True):
        """
        Get a new token from token generator.
        """
        self._tok_number, self._tok_value, self._tok_begin, self._tok_end, self._tok_line = next(self._tokens)
        self._tok_name = token.tok_name.get(self._tok_number, None)

        if self._debug:
            print("%2s %16s %s" % (self._tok_number, self._tok_name, self._tok_value.strip()))

        # skip some tokens
        if self._tok_name in ["COMMENT", "INDENT", "DEDENT"]:
            self._get_token()

        if skip_newline and self._tok_name in ["NL", "NEWLINE"]:
            self._get_token()

    def _get_NAME(self):
        """
        Return a NAME token value.
        """
        if self._tok_value == "False":
            return False

        if self._tok_value == "True":
            return True

        if self._tok_value == "None":
            return None

        # return already defined variable
        return self[self._tok_value]

    def _get_STRING(self):
        """
        Return a STRING token value.
        """

        # remove apostrophes or quotation marks
        result = self._tok_value[1:-1]

        # look at next token if "%s" follows the string
        self._tokens, tmp = itertools.tee(self._tokens)
        if next(tmp)[1:2] != ("%", ):
            # just a regular string
            return result

        # string formatting is used
        self._get_token()
        self._assert_token(("OP", "%"))
        values = self._get_value()
        return result % values

    def _get_NUMBER(self, negative=False):
        """
        Return a NUMBER token value.
        """
        if self._tok_value.find(".") != -1:
            result = float(self._tok_value)
        else:
            result = int(self._tok_value)

        if negative:
            return -result
        return result

    def _get_value(self, get_next=True, basic_types_only=False):
        """
        Get a value (number, string, other variable value, ...).
        """
        if get_next:
            self._get_token()

        self._assert_token(("NAME", ), ("NUMBER", ), ("STRING", ), ("OP", "{"), ("OP", "["), ("OP", "("), ("OP", "-"))

        if (self._tok_name, self._tok_value) == ("OP", "-"):
            self._get_token()
            self._assert_token(("NUMBER", ))
            return self._get_NUMBER(negative=True)

        if self._tok_name in ["NAME", "NUMBER", "STRING"]:
            return getattr(self, "_get_%s" % self._tok_name)()

        if not basic_types_only:
            if (self._tok_name, self._tok_value) == ("OP", "{"):
                return self._get_dict()

            if (self._tok_name, self._tok_value) == ("OP", "["):
                return self._get_list()

            if (self._tok_name, self._tok_value) == ("OP", "("):
                return self._get_tuple()

        self._assert_token(("FOO", ))

    def _get_from_import(self):
        """
        Parse 'from <config> import <variables/*>'
        and import <config> data to this object.
        """

        file_name = ""
        while True:
            self._get_token()
            if (self._tok_name, self._tok_value) == ("NAME", "import"):
                break
            file_name += str(self._tok_value)
        file_name += "." + self._config_file_suffix

        file_name = os.path.join(os.path.dirname(self._open_file), file_name)
        self._assert_token(("NAME", "import"))

        imports = []
        self._get_token()
        while self._tok_name not in ("NL", "NEWLINE"):
            self._assert_token(("NAME", ), ("OP", "*"))
            imports.append(self._tok_value)
            self._get_token(skip_newline=False)
            self._skip_commas(skip_newline=False)

        imported_config = self.__class__(config_file_suffix=self._config_file_suffix, debug=self._debug)
        imported_config.load_from_file(file_name)

        if "*" in imports:
            self.load_from_dict(imported_config)
        else:
            for key in imports:
                try:
                    self[key] = imported_config[key]
                except KeyError:
                    raise KeyError("Can't import %s from %s." % (key, file_name))

    def _skip_commas(self, skip_newline=True):
        """
        Skip OP tokens which contain commas.
        """
        while (self._tok_name, self._tok_value) == ("OP", ","):
            self._get_token(skip_newline)

    def _get_dict(self):
        """
        Get a dictionary content.
        """
        result = {}
        while True:
            self._get_token()
            self._skip_commas()

            if (self._tok_name, self._tok_value) == ("OP", "}"):
                break

            key = self._get_value(get_next=False, basic_types_only=True)

            self._get_token()
            self._assert_token(("OP", ":"))

            value = self._get_value()
            result[key] = value

        return result

    def _get_list(self):
        """
        Get a list content.
        """
        result = []
        while True:
            self._get_token()
            self._skip_commas()

            if (self._tok_name, self._tok_value) == ("OP", "]"):
                break

            value = self._get_value(get_next=False)
            result.append(value)

        return result

    def _get_tuple(self):
        """
        Get a tuple content.
        """
        result = []
        while True:
            self._get_token()
            self._skip_commas()

            if (self._tok_name, self._tok_value) == ("OP", ")"):
                break

            value = self._get_value(get_next=False)
            result.append(value)

        return tuple(result)


# settings is created only if PROJECT_CONFIG_FILE is set
if "PROJECT_CONFIG_FILE" in os.environ:
    try:
        settings = PyConfigParser()
        settings.load_from_file(os.environ.get("PROJECT_CONFIG_FILE"))
    except Exception as ex:
        raise ImproperlyConfigured("Could not load config file: %s" % ex)
