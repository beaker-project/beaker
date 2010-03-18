# Medusa - Medusa is the Inventory piece of the Beaker project
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# -*- coding: utf-8 -*-
"""This module contains functions called from console script entry points."""

import sys
from os import getcwd
from os.path import dirname, exists, join

import pkg_resources
pkg_resources.require("TurboGears>=1.0.4.4")
pkg_resources.require("SQLAlchemy>=0.3.10")

import cherrypy
import turbogears

from beaker.server.util import load_config

cherrypy.lowercase_api = True

class ConfigurationError(Exception):
    pass


def start():
    """Start the CherryPy application server."""
    if len(sys.argv) > 1:
        load_config(sys.argv[1])
    else:
        load_config()

    from beaker.server.controllers import Root
    turbogears.start_server(Root())
