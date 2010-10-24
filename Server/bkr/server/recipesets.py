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

from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, config, url
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.widgets import RecipeWidget
from bkr.server.widgets import RecipeTasksWidget
from bkr.server.widgets import SearchBar
from bkr.server import search_utility
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.recipetasks import RecipeTasks
from socket import gethostname
from bkr.upload import Uploader
import exceptions
import time

import cherrypy

from model import *
import string

import logging
log = logging.getLogger(__name__)

class RecipeSets(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def stop(self, recipeset_id, stop_type, msg=None):
        """
        Set recipeset status to Completed
        """
        try:
            recipeset = RecipeSet.by_id(recipeset_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipeset ID: %s' % recipeset_id))
        if stop_type not in recipeset.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, recipeset.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(recipeset,stop_type)(**kwargs)
