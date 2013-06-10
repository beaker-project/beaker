from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import AlphaNavBar, myPaginateDataGrid
from bkr.server.model import PowerType
from bkr.server.admin_page import AdminPage

import cherrypy

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class FormSchema(validators.Schema):
    key = validators.UnicodeString(not_empty=True, max=256, strip=True)
    description = validators.UnicodeString(not_empty=True, max=256, strip=True)
    type = validators.UnicodeString(not_empty=True, max=256, strip=True)

class ExpandingFormSchema(validators.Schema):
    name = validators.UnicodeString(not_empty=True, max=256, strip=True)
    command = validators.UnicodeString(not_empty=True, max=256, strip=True)
    powerreset = validators.UnicodeString(not_empty=False, max=256, strip=True)
    poweroff = validators.UnicodeString(not_empty=True, max=256, strip=True)
    poweron = validators.UnicodeString(not_empty=True, max=256, strip=True)
    arguments = validators.ForEach(
        FormSchema(),
    )


def make_link(url, text):
    # make a <a> element
    a = Element('a', href='./' + url)
    a.text = text
    return a
 	
def make_edit_link(power):
    # make a edit link
    return make_link(url  = 'edit?id=%s' % power.id,
                     text = power.name)

def make_remove_link(power):
    # make a remove link
    return make_link(url  = 'remove?id=%s' % power.id,
                     text = 'Remove (-)')
def get_power_type(power):
    # return powertype name
    return make_link(url  = '../powertypes/edit?id=%s' % power.powertype.id,
                     text = power.powertype.name)

class PowerTypes(AdminPage):
    # For XMLRPC methods in this class.
    exposed = False

    id         = widgets.HiddenField(name='id')
    name       = widgets.TextField(name='name', label=_(u'Name'))

    form = widgets.TableForm(
        'powertypes',
        fields = [id, name],
        action = 'save_data',
        submit_text = _(u'Submit Data'),
    )


    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/powertypes/by_name?anywhere=1"),
        kw['search_name'] = 'power'
        super(PowerTypes,self).__init__(*args,**kw)

        self.search_col = PowerType.name
        self.search_mapper = PowerType
      

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
            powertype = PowerType.by_id(kw['id'])
            values = dict(
                id         = powertype.id,
                name       = powertype.name,
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
            edit = PowerType.by_id(kw['id'])
            edit.name = kw['name']
        elif kw.get('name'):
            new = PowerType(name=kw['name'])
        else:
            flash(_(u"Invalid Power Type entry"))
            redirect(".")
        flash( _(u"OK") )
        redirect(".")

    @expose(format='json')
    def by_name(self,input,*args,**kw): 
        if 'anywhere' in kw:
            search = PowerType.list_by_name(input,find_anywhere=True)
        else:
            search = PowerType.list_by_name(input)

        powers = [elem.name for elem in search]
        return dict(matches=powers)

    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list', default_order='name', limit=20)
    def index(self,*args,**kw):
        powertypes = session.query(PowerType)
        list_by_letters = set([elem.name[0].capitalize() for elem in powertypes if elem.name])
        results = self.process_search(**kw)
        if results:
            powertypes = results

        powertypes_grid = myPaginateDataGrid(fields=[
                                  ('Power Type', make_edit_link),
                                  (' ', make_remove_link),
                              ])
        

        return dict(title="Power Types", 
                    grid = powertypes_grid,
                    addable = self.add,
                    search_widget = self.search_widget_form,
                    alpha_nav_bar = AlphaNavBar(list_by_letters,'power'),
                    object_count = powertypes.count(),
                    list = powertypes)

    @expose()
    def remove(self, **kw):
        remove = PowerType.by_id(kw['id'])
        session.delete(remove)
        flash( _(u"%s Deleted") % remove.name )
        raise redirect(".")

