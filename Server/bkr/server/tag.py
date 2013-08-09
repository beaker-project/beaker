from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, \
    error_handler, validators, redirect, paginate
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import DistroTags
from bkr.server.helpers import *
from distro import Distros

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class Tags(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @expose(format='json')
    def by_tag(self, tag, *args, **kw):
        tag = tag.lower()
        search = DistroTag.list_by_tag(tag)
        tags = [match.tag for match in search]
        return dict(tags=tags)

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='tag',limit=50)
    def index(self):
        tags = session.query(DistroTag)
        tags_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='tag', getter=lambda x: make_link(url  = '../distros/tagsearch/?tag=%s' % x.tag,
                                  text = x.tag), title='Tag', options=dict(sortable=True)),
                              ])
        return dict(title="Tags", grid = tags_grid,
                                         search_bar = None,
                                         object_count = tags.count(),
                                         list = tags)

    default = index
