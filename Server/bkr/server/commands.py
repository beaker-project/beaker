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
import resource
import logging
import cherrypy
import turbogears
from bkr.log import log_to_stream
from bkr.server.util import load_config

cherrypy.lowercase_api = True

class ConfigurationError(Exception):
    pass


def start():
    """Start the CherryPy application server."""
    if len(sys.argv) > 1:
        load_config(sys.argv[1])
    else:
        load_config()
    log_to_stream(sys.stderr, level=logging.DEBUG)

    # To see all SQL statements executed, uncomment the following.
    #logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    # To see access log entries printed by CherryPy, uncomment the following.
    #logging.getLogger('turbogears.access').setLevel(logging.INFO)

    # If rlimit_as is defined in the config file then set the limit here.
    if turbogears.config.get('rlimit_as'):
        resource.setrlimit(resource.RLIMIT_AS, (turbogears.config.get('rlimit_as'),
                                                turbogears.config.get('rlimit_as')))

    from bkr.server.controllers import Root
    turbogears.start_server(Root())
