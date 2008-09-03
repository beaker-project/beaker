from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from model import *
from turbogears import identity, redirect
from medusa.power import PowerTypes, PowerControllers
from medusa.widgets import myPaginateDataGrid
from medusa.widgets import Power
from medusa.widgets import SearchBar
from medusa.xmlrpccontroller import RPCRoot
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm

from kid import Element
import cherrypy
import md5

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
import breadcrumbs
from datetime import datetime

def make_link(url, text):
    # make an <a> element
    a = Element('a', {'class': 'list'}, href=url)
    a.text = text
    return a

def so_to_dict(sqlobj):
    """Convert SQLObject to a dictionary based on columns."""
    d = {}
    if sqlobj == None:
        # stops recursion
        return d
    for name in sqlobj.sqlmeta.columns.keys():
        d[name] = getattr(sqlobj, name)
    "id must be added explicitly"
    d["id"] = sqlobj.id
    if sqlobj._inheritable:
        d.update(so_to_dict(sqlobj._parent))
        d.pop('childName')
    return d

#def search():
#    """Return proper join for search"""
#    tables = dict ( Cpu = 'Cpu.q.system == System.q.id' 
#    tables = dict ( Cpu = (Cpu.q.system == System.q.id))

#    systems = System.select(AND(*your_dict.iter_values()))  ?

class Devices:

    @expose(template='medusa.templates.grid')
    @paginate('list')
    def view(self, id):
        device = session.query(Device).get(id)
        systems = session.query(System).join('devices').filter_by(id=id)
        device_grid = myPaginateDataGrid(fields=[
                        ('System', lambda x: make_link("/view/%s" % x.name, x.name)),
                        ('Description', lambda x: device.description),
                       ])
        return dict(title="", grid = device_grid, search_bar=None,
                                              list = systems)

    @expose(template='medusa.templates.grid')
    @paginate('list',default_order='description',limit=50,allow_limit_override=True)
    def default(self, *args, **kw):
        args = list(args)
        if len(args) == 1:
            devices = session.query(Device).join('device_class').filter_by(device_class=args[0])
                
        if len(args) != 1:
            devices = session.query(Device).join('device_class')
        devices_grid = myPaginateDataGrid(fields=[
                        widgets.PaginateDataGrid.Column(name='description', getter=lambda x: make_link("/devices/view/%s" % x.id, x.description), title='Description', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='device_class.device_class', getter=lambda x: x.device_class, title='Type', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='bus', getter=lambda x: x.bus, title='Bus', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='driver', getter=lambda x: x.driver, title='Driver', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='vendor_id', getter=lambda x: x.vendor_id, title='Vendor ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='device_id', getter=lambda x: x.device_id, title='Device ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='subsys_vendor_id', getter=lambda x: x.subsys_vendor_id, title='Subsys Vendor ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='subsys_device_id', getter=lambda x: x.subsys_device_id, title='Subsys Device ID', options=dict(sortable=True)),
                       ])
        return dict(title="Devices", grid = devices_grid, search_bar=None,
                                     list = devices)


class Root(RPCRoot):
    powertypes = PowerTypes()
    powercontrollers = PowerControllers()
    devices = Devices()

    id           = widgets.HiddenField(name='id')
    name         = widgets.TextField(name='name', label=_(u'Name'), validator=validators.NotEmpty())
    status       = widgets.SingleSelectField(name='status', label=_(u'Status'), options=['Available','InUse','Offline'])
    vendor = widgets.TextField(name='vendor', label=_(u'Vendor'))
    model        = widgets.TextField(name='model', label=_(u'Model'))
    serial = widgets.TextField(name='serial', label=_(u'Serial Number'))
    type = widgets.SingleSelectField(name='type', label=_(u'Type'), options=['Desktop','Server','Virtual'])
    location = widgets.TextField(name='location', label=_(u'Location'))
    contact = widgets.TextField(name='contact', label=_(u'Contact'))
    search_bar = SearchBar(name='systemsearch',
                           label=_(u'System Search'),
                           table_callback=System.get_tables,
                           search_controller='/get_fields'
                 )
    power = Power(name='powercontrol',
                 label=_(u'Power Control'),
                 callback=powercontrollers.get_powercontrollers,
                 search_controller='/powercontrollers/get_power_args',
                 system_id='system_id' # This is Ugly. :(
                 # Should be able to get rid of this 
            )

    system_form = widgets.TableForm(
        'system',
        fields = [id, name, status, vendor, model, type, serial,
                  location, contact, power],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )

    @expose(format='json')
    def get_fields(self, table_name):
        return dict( fields = System.get_fields(table_name))

    @expose(template='medusa.templates.grid')
    @paginate('list',default_order='name')
    # @identity.require(identity.in_group("admin"))
    def index(self, table=None, column=None, operation=None, value=None, *args, **kw):
        systems = session.query(System).join('status').join('type')
        if kw.get("systemsearch"):
            searchvalue = kw['systemsearch']
            for search in kw['systemsearch']:
                clsinfo = System.get_dict()[search['table']]
                cls = clsinfo['cls']
                col = getattr(cls,search['column'], None)
                systems = systems.join(clsinfo['joins'])
                if search['operation'] == 'greater than':
                    systems = systems.filter(col>search['value'])
                if search['operation'] == 'less than':
                    systems = systems.filter(col<search['value'])
                if search['operation'] == 'not equal':
                    systems = systems.filter(col!=search['value'])
                if search['operation'] == 'equal':
                    systems = systems.filter(col==search['value'])
                if search['operation'] == 'like':
                    value = '%%%s%%' % search['value']
                    systems = systems.filter(col.like(value))
        else:
            searchvalue = None
        systems_grid = myPaginateDataGrid(fields=[
                        widgets.PaginateDataGrid.Column(name='name', getter=lambda x: make_link("/view/%s" % x.name, x.name), title='Name', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x: x.status, title='Status', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='vendor', getter=lambda x: x.vendor, title='Vendor', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='model', getter=lambda x: x.model, title='Model', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='serial', getter=lambda x: x.serial, title='Serial', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='location', getter=lambda x: x.location, title='Location', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='type.type', getter=lambda x: x.type, title='Type', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='owner', getter=lambda x: x.owner, title='Owner', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='date_lastcheckin', getter=lambda x: x.date_lastcheckin, title='Last Checkin', options=dict(sortable=True)),
                       ])
        return dict(title="Systems", grid = systems_grid,
                                     list = systems, searchvalue = searchvalue,
                                     action = '.',
                                     options = {},
                                     search_bar = self.search_bar)

    @expose(template="medusa.templates.form")
    def new(self, **kw):
        return dict(
            form = self.system_form,
            action = './save',
            options = {},
            value = kw,
        )


    @expose(template="medusa.templates.system")
    def view(self, fqdn=None, **kw):
        widget = widgets.Tabber()
        if fqdn:
            try:
                system = System.by_name(fqdn)
            except NameError:
                flash( _(u"Unable to find %s" % fqdn) )
                redirect("/")
        elif kw['id']:
            try:
                system = session.query(System).filter_by(id=kw['id']).one()
            except NameError:
                flash( _(u"Unable to find system with id of %s" % kw['id']) )
                redirect("/")
        return dict(
            system = system,
            widget = widget
        )
            
    @expose(template="medusa.templates.form")
    def edit(self, fqdn=None, **kw):
        values = {}
        if fqdn:
            system = System.by_name(fqdn)
        if kw.get('id'):
            system = model.System.get(kw['id'])
        values = so_to_dict(system)
        values['powercontrol'] = dict(powercontroller = system.powerControlID)
        print values

        return dict(
            title = values['name'],
            form = self.system_form,
            action = '/save',
            options = {},
            value = values,
        )

#    @error_handler(view)
    @expose()
    def save(self, **kw):
        pc = kw['powercontrol']
        keys = []
        if 'key' in pc:
            for carg in pc['key']:
                key = {}
                key['id'] = carg
                key['value'] = pc['key'][carg]
                keys.append(key)
        if kw['id']:
            edit = model.System.get(kw['id'])
            edit.set(name=kw['name'], status=kw['status'],
                               contact=kw['contact'], location=kw['location'],
                               model=kw['model'], type=kw['type'],
                               serial=kw['serial'], 
                               date_modified=datetime.utcnow(),
                               vendor=kw['vendor'])
            if int(pc['powercontroller']) == 0:
                edit.set(powerControl='Null')
            else:
		edit.set(powerControl=int(pc['powercontroller']))
            if keys:
                edit.update_powerKeys(keys)
            else:
                edit.remove_powerKeys()
        else:
            new = model.System(name=kw['name'], status=kw['status'],
                               contact=kw['contact'], location=kw['location'],
                               model=kw['model'], type=kw['type'],
                               serial=kw['serial'],date_modified=datetime.utcnow(),
                               vendor=kw['vendor'])
            if pc['powercontroller']:
		new.set(powerControl=int(pc['powercontroller']))
            if keys:
                new.update_keys(keys)
        flash( _(u"OK") )
        redirect(".")

    @cherrypy.expose
    def push(self, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN");
        if not inventory:
            return (0,"No inventory data provided");

        md5sum = md5.new("%s" % inventory).hexdigest()

        try:
            system = System.by_name(fqdn)
        except:
            # New system, add it.
            print fqdn
            system = System(name=fqdn)
                                 # , model=inventory['model'],
                                 # date_modified=datetime.utcnow(),
                                 # vendor=inventory['vendor'])
            pass
        system.update(inventory)
        return 0

    @expose(template="medusa.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):

        if not identity.current.anonymous \
            and identity.was_login_attempted() \
            and not identity.get_identity_errors():
            raise redirect(forward_url)

        forward_url=None
        previous_url= request.path

        if identity.was_login_attempted():
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg=_("Please log in.")
            forward_url= request.headers.get("Referer", "/")
            
        response.status=403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
                    original_parameters=request.params,
                    forward_url=forward_url)

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect("/")
