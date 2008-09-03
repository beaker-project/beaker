# Logan - Logan is the scheduling piece of the Beaker project
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
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from logan.widgets import myPaginateDataGrid
from logan.xmlrpccontroller import RPCRoot
from logan.helpers import make_link

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

class Families(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    id = widgets.HiddenField(name='id')
    name = widgets.TextField(name='name', label='Name', validator=validators.NotEmpty())
    alias = widgets.TextField(name='alias', label='Alias', validator=validators.NotEmpty())
    archids = widgets.CheckBoxList(name='archids', label='Arches', options=Arch.get_arches, validator=validators.NotEmpty())
    form = widgets.TableForm(
        'family',
        fields = [id,name,alias,archids],
        action = 'save_data',
        submit_test = _(u'Submit Data')
    )

    @expose(template='logan.templates.form')
    def new(self, *args, **kw):
        try:
            value = Family.by_id(args[0])
            value.archids = [arch.id for arch in value.arches]
            title = kw['title']
        except:
            value = kw
            title = 'New Family'
        return dict(
            title = title,
            form = self.form,
            action = '/families/save',
            options = {},
            value = value,
        )

    @expose()
    def save(self, *args, **kw):
        print kw
        if kw.get('id'):
            family = Family.by_id(kw['id'])
        else:
            family = Family.lazy_create(name=kw['name'],alias=kw['alias'])
        for arch in kw['archids']:
            family.arches.append(Arch.by_id(arch))
            print arch
        flash(_(u"OK"))
        redirect(".")

    @expose(template='logan.templates.grid')
    def index(self, *args, **kw):
        families = session.query(Family)
        family_grid = widgets.DataGrid(fields=[
		     widgets.DataGrid.Column(name='name', getter=lambda x: make_link("./edit/%s" % x.id, x.name), title='Name'),
		     widgets.DataGrid.Column(name='alias', getter=lambda x: x.alias, title='Alias'),
		     widgets.DataGrid.Column(name='arches', getter=lambda x: ', '.join([arch.arch for arch in x.arches]), title='Arches'),
                    ])
        return dict(title="Families", grid=family_grid, list=families, search_bar=None)

    @expose()
    def edit(self, *args):
        return self.new(title="Edit Family", *args)

