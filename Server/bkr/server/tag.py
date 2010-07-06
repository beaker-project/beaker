from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
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
    def install_tag(self, distro, arch, *args, **kw):
        tagged_stable = []
        tagged_installs = Distros()._tag(distro, arch, 'INSTALLS')
        if arch == 'ppc':
            tagged_installs.extend(Distros()._tag(distro, 'ppc64', 'INSTALLS'))

        # Tag Stable if we have all expected arches and they are all tagged INSTALLS
        distro_obj = Distro.query().filter(distro_table.c.name.like(distro)).first()
        if distro_obj:
            for arch in distro_obj.osversion.arches:
                if not Distro.query().filter(distro_table.c.name.like(distro)).join('arch').filter(arch_table.c.arch==arch.arch).count():
                    break
            else:
                distros  = set(Distros().list(distro, None, None, None, None))
                installs = set(Distros().list(distro, None, None, ['INSTALLS'], None))
                if distros == installs:
                    tagged_stable = Distros()._tag(distro, None, 'STABLE')
        return dict(installs=tagged_installs, stable=tagged_stable)
        
    @expose(format='json')
    def by_tag(self, tag, *args, **kw):
        tag = tag.lower()
        search = DistroTag.list_by_tag(tag)
        tags = [match.tag for match in search]
        return dict(tags=tags)

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='tag',limit=50,max_limit=None)
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
