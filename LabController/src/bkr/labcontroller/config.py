# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import copy
import os
import socket

from bkr.common.pyconfig import PyConfigParser

__all__ = ["load_conf", "get_conf"]


class Config(PyConfigParser):
    def get_url_domain(self):
        # URL_DOMAIN used to be called SERVER
        return self.get("URL_DOMAIN", self.get("SERVER", socket.gethostname()))


_conf = Config()
default_config = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "default.conf")
)
_conf.load_from_file(default_config)
default_system_conf_file = "/etc/beaker/labcontroller.conf"

_conf_loaded = False


def load_conf(conf_file=default_system_conf_file):
    global _conf, _conf_loaded
    # Will throw IOError if file does not exist
    _conf.load_from_file(conf_file)
    _conf_loaded = True


def get_conf():
    global _conf, _conf_loaded
    if not _conf_loaded:
        load_conf()
    return copy.copy(_conf)
