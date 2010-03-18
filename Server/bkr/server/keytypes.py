from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *

import cherrypy

# from beaker.server import json
# import logging
# log = logging.getLogger("beaker.server.controllers")
#import model
from model import *
import string

class KeyTypes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    id         = widgets.HiddenField(name='id')
    key_name   = widgets.TextField(name='key_name', label=_(u'Name'))
    numeric    = widgets.CheckBox(name='numeric', label=_(u'Numeric'))

    form = widgets.TableForm(
        'keytypes',
        fields = [id, key_name, numeric],
        action = 'save_data',
        submit_text = _(u'Submit Data'),
    )

    @expose(template='beaker.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='beaker.server.templates.form')
    def edit(self,**kw):
        values = []
        if kw.get('id'):
            key = Key.by_id(kw['id'])
            values = dict(
                id         = key.id,
                key_name   = key.key_name,
                numeric    = key.numeric
            )
        
        return dict(
            form = self.form,
            action = './save',
            options = {},
            value = values,
        )
    
    @expose()
    @error_handler(edit)
    def save(self, **kw):
        if kw['id']:
            key = Key.by_id(kw['id'])
            key.key_name = kw['key_name']
        else:
            key = Key(key_name=kw['key_name'])
        if 'numeric' in kw:
            key.numeric = kw['numeric']
        flash( _(u"OK") )
        redirect(".")

    @expose(template="beaker.server.templates.grid_add")
    @paginate('list')
    def index(self):
        keytypes = session.query(Key)
        keytypes_grid = widgets.PaginateDataGrid(fields=[
                                  ('Key', lambda x: make_edit_link(x.key_name, x.id)),
                                  ('Numeric', lambda x: x.numeric),
                                  (' ', lambda x: make_remove_link(x.id)),
                              ])
        return dict(title="Key Types", grid = keytypes_grid,
                                         search_bar = None,
                                         list = keytypes)

    @expose()
    def remove(self, **kw):
        remove = Key.by_id(kw['id'])
        session.delete(remove)
        flash( _(u"%s Deleted") % remove.key_name )
        raise redirect(".")

