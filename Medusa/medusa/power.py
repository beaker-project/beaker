from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.widgets import PowerController
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
    exposed = True

    key = widgets.TextField(name='key', label=_(u'Argument'), attrs=dict(size=10))
    description = widgets.TextField(name='description', label=_(u'Description'), attrs=dict(size=30))
    type = widgets.SingleSelectField(name='type', label=_(u'Type'), options=['Controller','Host'])

    id         = widgets.HiddenField(name='id')
    name       = widgets.TextField(name='name', label=_(u'Name'))
    command    = widgets.TextField(name='command', label=_(u'Command'))
    powerreset = widgets.TextField(name='powerreset', label=_('Power Reset'))
    poweroff   = widgets.TextField(name='poweroff', label=_('Power Off'))
    poweron    = widgets.TextField(name='poweron', label=_('Power On'))

    expform = ExpandingForm(
        name='arguments',
        label=_(u'Command Line Arguments'),
        fields=[key, description, type],
    )

    expanding_form = widgets.TableForm(
        'powertypes',
        fields = [id, name, command, powerreset, poweroff, poweron, expform],
        action = 'save_data',
        submit_text = _(u'Submit Data'),
        validator = ExpandingFormSchema()
    )

    @expose(template='medusa.templates.form')
    def new(self, **kw):
        return dict(
            form = self.expanding_form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='medusa.templates.form')
    def edit(self,**kw):
        values = []
        if kw.get('id'):
            powertype = model.PowerType.get(kw['id'])
            values = dict(
                id         = powertype.id,
                name       = powertype.name,
                command    = powertype.command,
                powerreset = powertype.powerreset,
                poweroff   = powertype.poweroff,
                poweron    = powertype.poweron,
                arguments  = powertype.keys
            )
        
        return dict(
            form = self.expanding_form,
            action = './save',
            options = {},
            value = values,
        )
    
    @expose()
    @validate(form=expanding_form)
    @error_handler(edit)
    def save(self, **kw):
        print kw['arguments']
        if kw['id']:
            edit = model.PowerType.get(kw['id'])
            edit.set(name=kw['name'],command=kw['command'],
                     powerreset=kw['powerreset'],poweroff=kw['poweroff'],
                     poweron=kw['poweron'])
            edit.update_powerkeys(kw['arguments'])
        else:
            new = model.PowerType(name=kw['name'],command=kw['command'],
                                      powerreset=kw['powerreset'],
                                      poweroff=kw['poweroff'],
                                      poweron=kw['poweron'])
            new.update_powerkeys(kw['arguments'])
        flash( _(u"OK") )
        redirect(".")

    @expose(template="medusa.templates.grid")
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
        remove = model.PowerType.get(kw['id'])
        remove.destroySelf()
        flash( _(u"%s Deleted") % remove.name )
        raise redirect(".")

    @cherrypy.expose
    def get_powertypes(*args, **kw):
        powertypes = session.query(PowerType)
        return [(powertype.id, powertype.name) for powertype in powertypes]

    @cherrypy.expose
    def add(self, a, b):
        return (a+b,"Success")

class PowerControllers:
    # For XMLRPC methods in this class.
    exposed = True

    powercontroller = PowerController(
        name='powercontroller',
        label=_(u'Power Control'),
        callback=PowerTypes().get_powertypes,
        search_controller='/powercontrollers/get_powercontroller_args'
    )

    form = widgets.TableForm(
        name='form',
        fields = [powercontroller],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )

    @cherrypy.expose
    def get_powercontrollers(*args, **kw):
        powercontrollers = session.query(PowerControl)
        pc = [(0, 'None')]
        pc.extend([(p.id, p.name) for p in powercontrollers])
        return pc

    @expose(format='json')
    def get_powercontroller_args(self, powercontroller_id=None, 
                                 powertype_id=None,
                                 tg_errors=None):
        if powercontroller_id:
            try:
                powercontrol  = model.PowerControl.get(powercontroller_id)
            except:
                powercontroller_id = None
                pass
        powertype = model.PowerType.get(powertype_id)
        keys = []
        values = {}
        if powercontroller_id:
            for value in powercontrol.keys:
                values[value.key.key] = value.value
        for key in powertype.keys:
            if key.type == 'Controller':
                try:
                    value = values[key.key]
                except:
                    value = None
                keys.append({'id'               : key.id,
                             'description'      : key.description,
                             'value'            : value})
        return dict(keys=keys)

    @expose(format='json')
    def get_power_args(self, powercontroller_id=None, system_id=None):
        powercontrol  = model.PowerControl.get(powercontroller_id)
        if system_id:
            system  = model.System.get(system_id)
        keys = []
        values = {}
        if system_id:
            for value in system.powerKeys:
                values[value.key.key] = value.value
        for key in powercontrol.powertype.keys:
            if key.type == 'Host':
                try:
                    value = values[key.key]
                except:
                    value = None
                keys.append({'id'               : key.id,
                             'description'      : key.description,
                             'value'            : value})
        return dict(keys=keys)

    @expose(template='medusa.templates.form')
    def new(self, **kw):
        powertypes = session.query(PowerType)
        try:
            powertype_id = powertypes[0].id
        except:
            flash( _(u"You must define PowerTypes first") )
            redirect(".")
        return dict(
            form=self.form,
            action = './save',
            options = {},
            value = None
        )

    @expose(template='medusa.templates.form')
    def edit(self,**kw):
        values = []
        commandargs = {}
        keys = {}
        if kw.get('id'):
            powercontrol = model.PowerControl.get(kw['id'])
            powercontroller = dict(
                id             = kw.get('id'),
                powertype      = powercontrol.powertype.id,
                name           = powercontrol.name
            )
            values = dict(powercontroller = powercontroller)
                
        powertypes = session.query(PowerType)
        if not powertypes:
            return dict(form=None)
        return dict(
            form=self.form,
            action = '/powercontrollers/save',
            options = {},
            value = values,
        )
    
    @expose()
    @error_handler(edit)
    def save(self, **kw):
        pc = kw['powercontroller']
        print pc
        keys = []
        for carg in pc['key']:
            key = {}
            key['id'] = carg
            key['value'] = pc['key'][carg]
            keys.append(key)
        if pc['id']:
            edit = model.PowerControl.get(pc['id'])
            edit.set(name=pc['name'],powertype=int(pc['powertype']))
            edit.update_keys(keys)
        else:
            new = model.PowerControl(name=pc['name'],powertype=int(pc['powertype']))
            new.update_keys(keys)
        flash( _(u"OK") )
        redirect(".")

    @expose(template="medusa.templates.grid")
    @paginate('list')
    def index(self):
        powercontrollers = session.query(PowerControl)
        powercontrollers_grid = widgets.PaginateDataGrid(fields=[
                                  ('Name', make_edit_link),
                                  ('Power Type', get_power_type),
                                  (' ', make_remove_link),
                              ])
        return dict(title="Power Controllers", 
                    grid = powercontrollers_grid,
                    search_bar = None,
                    list = powercontrollers)

    @expose()
    def remove(self, **kw):
        remove = model.PowerControl.get(kw['id'])
        remove.destroySelf()
        flash( _(u"%s Deleted") % remove.name )
        raise redirect(".")
