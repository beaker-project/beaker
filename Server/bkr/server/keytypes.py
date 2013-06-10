from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import myPaginateDataGrid, AlphaNavBar
from bkr.server.admin_page import AdminPage

import cherrypy

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

class KeyTypes(AdminPage):
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

    
    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/keytypes/by_name?anywhere=1"),
        kw['search_name'] = 'key'
        super(KeyTypes,self).__init__(*args,**kw)

        self.search_col = Key.key_name
        self.search_mapper = Key
    
    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='bkr.server.templates.form')
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

    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list')
    def index(self,*args,**kw):
        keytypes = session.query(Key) 
        list_by_letters = set([elem.key_name[0].capitalize() for elem in keytypes])
        results = self.process_search(**kw)
        if results:
            keytypes = results
        keytypes_grid = myPaginateDataGrid(fields=[
                                  ('Key', lambda x: make_edit_link(x.key_name, x.id)),
                                  ('Numeric', lambda x: x.numeric),
                                  (' ', lambda x: make_remove_link(x.id)),
                              ]) 
        return dict(title="Key Types", 
                    grid = keytypes_grid, 
                    search_widget = self.search_widget_form,
                    alpha_nav_bar = AlphaNavBar(list_by_letters,self.search_name),
                    addable = self.add,
                    object_count = keytypes.count(),
                    list = keytypes)

    @expose()
    def remove(self, **kw):
        remove = Key.by_id(kw['id'])
        session.delete(remove)
        flash( _(u"%s Deleted") % remove.key_name )
        raise redirect(".")

    @expose(format='json')
    def by_name(self,input,*args,**kw):
        if 'anywhere' in kw:
            search = Key.list_by_name(input,find_anywhere=True)
        else:
            search = Key.list_by_name(input)

        keys = [elem.key_name for elem in search]
        return dict(matches=keys)

