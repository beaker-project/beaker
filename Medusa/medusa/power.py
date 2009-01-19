from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
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

class PowerTypes(RPCRoot):
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

    @expose(template='medusa.templates.form')
    def new(self, **kw):
        return dict(
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='medusa.templates.form')
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
        else:
            new = PowerType(name=kw['name'])
        flash( _(u"OK") )
        redirect(".")

    @expose(template="medusa.templates.grid_add")
    @paginate('list')
    def index(self):
        powertypes = session.query(PowerType)
        powertypes_grid = widgets.PaginateDataGrid(fields=[
                                  ('Power Type', make_edit_link),
                                  (' ', make_remove_link),
                              ])
        return dict(title="Power Types", grid = powertypes_grid,
                                         search_bar = None,
                                         list = powertypes)

    @expose()
    def remove(self, **kw):
        remove = PowerType.by_id(kw['id'])
        session.delete(remove)
        flash( _(u"%s Deleted") % remove.name )
        raise redirect(".")

