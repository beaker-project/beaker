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

class Arches(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    id = widgets.HiddenField(name='id')
    arch = widgets.TextField(name='arch', label='Arch', validator=validators.NotEmpty())
    form = widgets.TableForm(
        'arch',
        fields = [id,arch],
        action = 'save_data',
        submit_test = _(u'Submit Data')
    )

    @expose()
    def get_arches():
        arches = session.query(Arch)
        return [(arch.id, arch.arch) for arch in arches]

    @expose(template='logan.templates.form')
    def new(self, *args, **kw):
        try:
            value = Arch.by_id(args[0])
            title = kw['title']
        except:
            value = kw
            title = 'New Arch'
        return dict(
            title = title,
            form = self.form,
            action = './save',
            options = {},
            value = value,
        )

    @expose()
    def save(self, *args, **kw):
        print kw
        if kw.get('id'):
            arch = Arch.by_id(kw['id'])
            arch.arch = kw['arch']
        else:
            arch = Arch.lazy_create(arch=kw['arch'])
            
        flash(_(u"OK"))
        redirect(".")

    @expose(template='logan.templates.grid')
    def index(self, *args, **kw):
        arches = session.query(Arch)
        arch_grid = widgets.DataGrid(fields=[
		     widgets.DataGrid.Column(name='arch', getter=lambda x: make_link("./edit/%s" % x.id, x.arch), title='Arch'),
                    ])
        return dict(title="Arches", grid=arch_grid, list=arches, search_bar=None)

    @expose()
    def edit(self, *args):
        return self.new(title="Edit Arch", *args)

