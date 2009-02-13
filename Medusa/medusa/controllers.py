from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from model import *
from turbogears import identity, redirect, config
from medusa.power import PowerTypes
from medusa.group import Groups
from medusa.labcontroller import LabControllers
from medusa.user_system import UserSystems
from medusa.distro import Distros
from medusa.activity import Activities
from medusa.widgets import myPaginateDataGrid
from medusa.widgets import PowerTypeForm
from medusa.widgets import PowerForm
from medusa.widgets import PowerActionForm
from medusa.widgets import SystemDetails
from medusa.widgets import SystemHistory
from medusa.widgets import SystemExclude
from medusa.widgets import SystemKeys
from medusa.widgets import SystemNotes
from medusa.widgets import SystemGroups
from medusa.widgets import SystemInstallOptions
from medusa.widgets import SystemProvision
from medusa.widgets import SearchBar, SystemForm
from medusa.widgets import SystemArches
from medusa.xmlrpccontroller import RPCRoot
from medusa.cobbler_utils import hash_to_string
from cherrypy import request, response
from cherrypy.lib.cptools import serve_file
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from medusa.needpropertyxml import *
from medusa.helpers import *
from medusa.tools.init import dummy

from kid import Element
import cherrypy
import md5
import re
import string

# for debugging
import sys

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
import breadcrumbs
from datetime import datetime

#def search():
#    """Return proper join for search"""
#    tables = dict ( Cpu = 'Cpu.q.system == System.q.id' 
#    tables = dict ( Cpu = (Cpu.q.system == System.q.id))

#    systems = System.select(AND(*your_dict.iter_values()))  ?

class Users:

    @expose(format='json')
    def by_name(self, input):
        input = input.lower()
        return dict(matches=User.list_by_name(input))

class Netboot:
    # For XMLRPC methods in this class.
    exposed = True

    # path for Legacy RHTS
    @cherrypy.expose
    def system_return(self, *args):
        return Root().system_return(*args)

    @cherrypy.expose
    def commandBoot(self, machine_account, commands):
        """
        NetBoot Compat layer for old RHTS Scheduler
        """
        repos = []
        bootargs = None
        kickstart = []
        packages = []
        testrepo = None
        hostname = None
        distro_name = None
        SETENV = re.compile(r'SetEnvironmentVar\s+([^\s]+)\s+"*([^"]+)')
        BOOTARGS = re.compile(r'BootArgs\s+(.*)')
        KICKSTART = re.compile(r'Kickstart\s+(.*)')
        ADDREPO = re.compile(r'AddRepo\s+([^\s]+)')
        TESTREPO = re.compile(r'TestRepo\s+([^\s]+)')
        INSTALLPACKAGE = re.compile(r'InstallPackage\s+([^\s]+)')

        for command in commands.split('\n'):
            if SETENV.match(command):
                if SETENV.match(command).group(1) == "RESULT_SERVER":
                    rhts_server = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "RECIPEID":
                    recipeid = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "HOSTNAME":
                    hostname = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "DISTRO":
                    distro_name = SETENV.match(command).group(2)
            if INSTALLPACKAGE.match(command):
                packages.append(INSTALLPACKAGE.match(command).group(1))
            if BOOTARGS.match(command):
                bootargs = BOOTARGS.match(command).group(1)
            if KICKSTART.match(command):
                kickstart = KICKSTART.match(command).group(1).split("RHTSNEWLINE")
            if ADDREPO.match(command):
                repos.append(ADDREPO.match(command).group(1))
            if TESTREPO.match(command):
                testrepo = TESTREPO.match(command).group(1)
            
        ks_meta = "rhts_server=%s testrepo=%s recipeid=%s packages=%s" % (rhts_server, testrepo, recipeid, string.join(packages,":"))
        if repos:
            ks_meta = "%s customrepos=%s" % (ks_meta, string.join(repos,"|"))
        if distro_name:
            distro = Distro.by_install_name(distro_name)
        else:
            rc = -4
            result = "distro not defined"
        if hostname:
            system = System.query().filter(System.fqdn == hostname).one()
            rc, result = system.action_auto_provision(distro, ks_meta, bootargs)
            activity = SystemActivity(system.user, 'VIA %s' % machine_account, 'Provision', 'Distro', "", "%s: %s" % (result, distro.install_name))
            system.activity.append(activity)
        else:
            rc = -3
            result = "hostname not defined"
        return rc

class Arches:
    @expose(format='json')
    def by_name(self,name):
        name = name.lower()
        search = Arch.list_by_name(name)
        arches = [match.arch for match in search]
        return dict(arches=arches)

class Devices:

    @expose(template='medusa.templates.grid')
    @paginate('list')
    def view(self, id):
        device = session.query(Device).get(id)
        systems = System.all(identity.current.user).join('devices').filter_by(id=id)
        device_grid = myPaginateDataGrid(fields=[
                        ('System', lambda x: make_link("/view/%s" % x.fqdn, x.fqdn)),
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
    devices = Devices()
    groups = Groups()
    labcontrollers = LabControllers()
    usersystems = UserSystems()
    distros = Distros()
    activity = Activities()
    users = Users()
    arches = Arches()
    netboot = Netboot()

    id         = widgets.HiddenField(name='id')
    submit     = widgets.SubmitButton(name='submit')

    autoUsers  = widgets.AutoCompleteField(name='user',
                                           search_controller=url("/users/by_name"),
                                           search_param="input",
                                           result_name="matches")
    

    owner_form    = widgets.TableForm(
        'Owner',
        fields = [id, autoUsers,],
        action = 'save_data',
        submit_text = _(u'Change'),
    )

    search_bar = SearchBar(name='systemsearch',
                           label=_(u'System Search'),
                           table_callback=System.get_tables,
                           search_controller=url("/get_fields")
                 )
    system_form = SystemForm()
    power_form = PowerForm(name='power')
    power_action_form = PowerActionForm(name='power_action')
    system_details = SystemDetails()
    system_activity = SystemHistory()
    system_exclude = SystemExclude(name='excluded_families')
    system_keys = SystemKeys(name='keys')
    system_notes = SystemNotes(name='notes')
    system_groups = SystemGroups(name='groups')
    system_installoptions = SystemInstallOptions(name='installoptions')
    system_provision = SystemProvision(name='provision')
    arches_form = SystemArches(name='arches')

    @expose(format='json')
    def get_fields(self, table_name):
        return dict( fields = System.get_fields(table_name))

    @expose(format='json')
    def get_installoptions(self, system_id=None, distro_id=None):
        try:
            system = System.by_id(system_id,identity.current.user)
        except InvalidRequestError:
            return dict(ks_meta=None)
        try:
            distro = Distro.by_id(distro_id)
        except InvalidRequestError:
            return dict(ks_meta=None)
        install_options = system.install_options(distro)
        ks_meta = hash_to_string(install_options['ks_meta'])
        kernel_options = hash_to_string(install_options['kernel_options'])
        kernel_options_post = hash_to_string(install_options['kernel_options_post'])
        return dict(ks_meta = ks_meta, kernel_options = kernel_options,
                    kernel_options_post = kernel_options_post)

    @expose(template='medusa.templates.grid_add')
    @paginate('list',default_order='fqdn',limit=20,allow_limit_override=True)
    def index(self, *args, **kw):
        return self.systems(systems = System.all(identity.current.user), *args, **kw)

    @expose(template='medusa.templates.grid')
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn',limit=20,allow_limit_override=True)
    def available(self, *args, **kw):
        return self.systems(systems = System.available(identity.current.user), *args, **kw)

    @expose(template='medusa.templates.grid')
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn',limit=20,allow_limit_override=True)
    def free(self, *args, **kw):
        return self.systems(systems = System.free(identity.current.user), *args, **kw)

    @expose(template='medusa.templates.grid')
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn',limit=20,allow_limit_override=True)
    def mine(self, *args, **kw):
        return self.systems(systems = System.mine(identity.current.user), *args, **kw)

    # @identity.require(identity.in_group("admin"))
    def systems(self, systems, *args, **kw):
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
                        widgets.PaginateDataGrid.Column(name='fqdn', getter=lambda x: make_link("/view/%s" % x.fqdn, x.fqdn), title='System', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x: x.status, title='Status', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='vendor', getter=lambda x: x.vendor, title='Vendor', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='model', getter=lambda x: x.model, title='Model', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='location', getter=lambda x: x.location, title='Location', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='type.type', getter=lambda x: x.type, title='Type', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='user.display_name', getter=lambda x: x.user, title='User', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='date_lastcheckin', getter=lambda x: x.date_lastcheckin, title='Last Checkin', options=dict(sortable=True)),
                       ])
        return dict(title="Systems", grid = systems_grid,
                                     list = systems, searchvalue = searchvalue,
                                     action = '.',
                                     options = {},
                                     search_bar = self.search_bar)

    @expose(format='json')
    def by_fqdn(self, input):
        input = input.lower()
        search = System.list_by_fqdn(input,identity.current.user).all()
        matches =  [match.fqdn for match in search]
        return dict(matches = matches)

    @expose()
    @identity.require(identity.not_anonymous())
    def key_remove(self, system_id=None, key_value_id=None):
        removed = None
        if system_id and key_value_id:
            try:
                system = System.by_id(system_id,identity.current.user)
            except:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id and group_id must be provided"))
            redirect("/")
        
        if system.can_admin(identity.current.user):
            for key_value in system.key_values:
                if key_value.id == int(key_value_id):
                    system.key_values.remove(key_value)
                    removed = key_value
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Key/Value', "%s/%s" % (removed.key_name, removed.key_value), "")
                    system.activity.append(activity)
        
        if removed:
            flash(_(u"removed %s/%s" % (removed.key_name,removed.key_value)))
        else:
            flash(_(u"Key_Value_Id not Found"))
        redirect("./view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def arch_remove(self, system_id=None, arch_id=None):
        removed = None
        if system_id and arch_id:
            try:
                system = System.by_id(system_id,identity.current.user)
            except:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id and arch_id must be provided"))
            redirect("/")
        if system.can_admin(identity.current.user):
           for arch in system.arch:
               if arch.id == int(arch_id):
                   system.arch.remove(arch)
                   removed = arch
                   activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Arch', arch.arch, "")
                   system.activity.append(activity)
        if removed:
            flash(_(u"%s Removed" % removed.arch))
        else:
            flash(_(u"Arch ID not found"))
        redirect("./view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def group_remove(self, system_id=None, group_id=None):
        removed = None
        if system_id and group_id:
            try:
                system = System.by_id(system_id,identity.current.user)
            except:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id and group_id must be provided"))
            redirect("/")
        if system.can_admin(identity.current.user):
           for group in system.groups:
               if group.group_id == int(group_id):
                   system.groups.remove(group)
                   removed = group
                   activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Group', group.display_name, "")
                   gactivity = GroupActivity(identity.current.user, 'WEBUI', 'Removed', 'System', "", system.fqdn)
                   group.activity.append(gactivity)
                   system.activity.append(activity)
        if removed:
            flash(_(u"%s Removed" % removed.display_name))
        else:
            flash(_(u"Group ID not found"))
        redirect("./view/%s" % system.fqdn)

    @expose(template="medusa.templates.system")
    @identity.require(identity.not_anonymous())
    def new(self):
        options = {}
        options['readonly'] = False
        return dict(
            title    = 'New System',
            form     = self.system_form,
            widgets  = {},
            action   = '/save',
            value    = None,
            options  = options)

    @expose(template="medusa.templates.form")
    def test(self, fqdn=None, **kw):
        try:
            system = System.by_fqdn(fqdn,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find %s" % fqdn) )
            redirect("/")

        return dict(
            title   = "test",
            system  = system,
            form    = self.system_provision,
            action  = '/save',
            value   = system,
            options = dict(readonly = False,
                     lab_controller = system.lab_controller,
                     prov_install = [(distro.id, distro.install_name) for distro in system.distros()]))

    @expose(template="medusa.templates.system")
    def view(self, fqdn=None, **kw):
        if fqdn:
            try:
                system = System.by_fqdn(fqdn,identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to find %s" % fqdn) )
                redirect("/")
        elif kw.get('id'):
            try:
                system = System.by_id(kw['id'],identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to find system with id of %s" % kw['id']) )
                redirect("/")
        else:
            system = None
        options = {}
        readonly = False
        is_user = False
        if system:
            title = system.fqdn
            if system.can_admin(identity.current.user):
                options['owner_change_text'] = ' (Change)'
            else:
                readonly = True
            if system.can_share(identity.current.user):
                options['user_change_text'] = ' (Take)'
            if system.current_user(identity.current.user):
                options['user_change_text'] = ' (Return)'
                is_user = True
        else:
            title = 'New'

        if readonly:
            attrs = dict(readonly = 'True')
        else:
            attrs = dict()
        options['readonly'] = readonly

        #Excluded Family options
        options['excluded_families'] = []
        for arch in system.arch:
            options['excluded_families'].append((arch.arch, [(osmajor.id, osmajor.osmajor, [(osversion.id, '%s' % osversion, attrs) for osversion in osmajor.osversion],attrs) for osmajor in OSMajor.query()]))

        return dict(
            title    = title,
            readonly = readonly,
            is_user  = is_user,
            form     = self.system_form,
            action   = '/save',
            value    = system,
            options  = options,
            widgets         = dict( power     = self.power_form,
                                    details   = self.system_details,
                                    history   = self.system_activity,
                                    exclude   = self.system_exclude,
                                    keys      = self.system_keys,
                                    notes     = self.system_notes,
                                    groups    = self.system_groups,
                                    install   = self.system_installoptions,
                                    provision = self.system_provision,
                                    power_action = self.power_action_form, 
                                    arches    = self.arches_form),
            widgets_action  = dict( power     = '/save_power',
                                    exclude   = '/save_exclude',
                                    keys      = '/save_keys',
                                    notes     = '/save_note',
                                    groups    = '/save_group',
                                    install   = '/save_install',
                                    provision = '/action_provision',
                                    power_action = '/action_power',
                                    arches    = '/save_arch'),
            widgets_options = dict(power     = options,
                                   exclude   = options,
                                   keys      = dict(readonly = readonly,
                                                key_values = system.key_values),
                                   notes     = dict(readonly = readonly,
                                                notes = system.notes),
                                   groups    = dict(readonly = readonly,
                                                groups = system.groups),
                                   install   = dict(readonly = readonly,
                                                provisions = system.provisions,
                                                prov_arch = [(arch.id, arch.arch) for arch in system.arch]),
                                   provision = dict(is_user = is_user,
                                                    lab_controller = system.lab_controller,
                                                    prov_install = [(distro.id, distro.install_name) for distro in system.distros().order_by(distro_table.c.install_name)]),
                                   power_action   = options,
                                   arches    = dict(readonly = readonly,
                                                    arches = system.arch)),
        )
         
    @expose(template='medusa.templates.form')
    @identity.require(identity.not_anonymous())
    def owner_change(self, id):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if not system.can_admin(identity.current.user):
            flash( _(u"Insufficient permissions to change owner"))
            redirect("/")

        return dict(
            title   = "Change Owner for %s" % system.fqdn,
            form = self.owner_form,
            action = '/save_owner',
            options = None,
            value = {'id': system.id},
        )
            
    @expose()
    @identity.require(identity.not_anonymous())
    def save_owner(self, id, *args, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if not system.can_admin(identity.current.user):
            flash( _(u"Insufficient permissions to change owner"))
            redirect("/")
        user = User.by_user_name(kw['user']['text'])
        activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'Owner', '%s' % system.owner, '%s' % user)
        system.activity.append(activity)
        system.owner = user
        flash( _(u"OK") )
        redirect("/")

    @expose()
    @identity.require(identity.not_anonymous())
    def user_change(self, id):
        status = None
        activity = None
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if system.user:
            if system.user == identity.current.user or \
              identity.current.user.is_admin():
                status = "Returned"
                activity = SystemActivity(identity.current.user, 'WEBUI', status, 'User', '%s' % system.user, '')
                system.action_return()
        else:
            if system.can_share(identity.current.user):
                status = "Reserved"
                system.user = identity.current.user
                activity = SystemActivity(identity.current.user, 'WEBUI', status, 'User', '', '%s' % system.user )
        system.activity.append(activity)
        session.save_or_update(system)
        flash( _(u"%s %s" % (status,system.fqdn)) )
        redirect("/view/%s" % system.fqdn)

    @error_handler(view)
    @expose()
    @identity.require(identity.not_anonymous())
    def save_power(self, id, power_address, power_type_id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Power for %s" % id) )
            redirect("/")

        if system.power:
            if power_address != system.power.power_address:
                #Power Address Changed
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_address', system.power.power_address, power_address )
                system.power.power_address = power_address
                system.activity.append(activity)
            if kw.get('power_user'):
                if kw['power_user'] != system.power.power_user:
                    #Power User Changed
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_user', '********', '********' )
                    system.power.power_user = kw['power_user']
                    system.activity.append(activity)
            else:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'power_user', '********', '********' )
                system.activity.append(activity)
                system.power.power_user = None
            if kw.get('power_passwd'):
                if kw['power_passwd'] != system.power.power_passwd:
                    #Power Passwd Changed
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_passwd', '********', '********' )
                    system.power.power_passwd = kw['power_passwd']
                    system.activity.append(activity)
            else:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'power_passwd', '********', '********' )
                system.activity.append(activity)
                system.power.power_passwd = None
            if kw.get('power_id'):
                if kw['power_id'] != system.power.power_id:
                    #Power ID Changed
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_id', system.power.power_id, kw['power_id'] )
                    system.power.power_id = kw['power_id']
                    system.activity.append(activity)
            else:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'power_id', system.power.power_id, '' )
                system.activity.append(activity)
                system.power.power_id = None
            if power_type_id != system.power.power_type_id:
                #Power Type Changed
                if int(power_type_id) == 0:
                    system.power = None
                else:
                    try:
                        power_type = PowerType.by_id(power_type_id)
                    except InvalidRequestError:
                        flash( _(u"Invalid power type %s" % power_type_id) )
                        redirect("/view/%s" % system.fqdn)
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_type', system.power.power_type.name, power_type.name )
                    system.power.power_type = power_type
                    system.activity.append(activity)
            flash( _(u"Updated Power") )
        else:
            try:
                power_type = PowerType.by_id(power_type_id)
            except InvalidRequestError:
                flash( _(u"Invalid power type %s" % power_type_id) )
                redirect("/view/%s" % system.fqdn)
            power = Power(power_type=power_type, power_address=power_address)
            if kw.get('power_user'):
                power.power_user = kw['power_user']
            if kw.get('power_passwd'):
                power.power_passwd = kw['power_passwd']
            if kw.get('power_id'):
                power.power_id = kw['power_id']
            system.power = power
            flash( _(u"Saved Power") )
        redirect("/view/%s" % system.fqdn)

    @expose()
    @validate(form=system_form)
    @identity.require(identity.not_anonymous())
    @error_handler(new)
    def save(self, **kw):
        if kw.get('id'):
            try:
                system = System.by_id(kw['id'],identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to save %s" % kw['id']) )
                redirect("/")
            system.fqdn = kw['fqdn']
        else:
            if System.query().filter(System.fqdn == kw['fqdn']).count() != 0:   
                flash( _(u"%s already exists!" % kw['fqdn']) )
                redirect("/")
            system = System(fqdn=kw['fqdn'],owner=identity.current.user)
# TODO what happens if you log changes here but there is an issue and the actual change to the system fails?
#      would be good to have the save wait until the system is updated
# TODO log  group +/-
        # Fields missing from kw have been set to NULL
        log_fields = [ 'fqdn', 'vendor', 'lender', 'model', 'serial', 'location', 'type_id', 'checksum', 'status_id', 'lab_controller_id' , 'mac_address']
        for field in log_fields:
            try:
                current_val = str(system.__dict__[field])
            except KeyError:
                current_val = ""
            # catch nullable fields return None.
            if current_val == 'None':
                current_val = ""
            if kw.get(field):
                if current_val != str(kw[field]):
#                    sys.stderr.write("\nfield: " + field + ", Old: " +  current_val + ", New: " +  str(kw[field]) + " " +  "\n")
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, current_val, kw[field] )
                    system.activity.append(activity)
            else:
                 if current_val != "":
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, current_val, "" )
                    system.activity.append(activity)
        log_bool_fields = [ 'shared', 'private' ]
        for field in log_bool_fields:
            try:
                current_val = str(system.__dict__[field])
            except KeyError:
                current_val = ""
            if kw.get(field):
                if current_val != True:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, current_val, "True" )
                    system.activity.append(activity)
            else:
                if current_val != False:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, current_val, "False" )
                    system.activity.append(activity)
        system.status_id=kw['status_id']
        system.location=kw['location']
        system.model=kw['model']
        system.type_id=kw['type_id']
        system.serial=kw['serial']
        system.vendor=kw['vendor']
        system.lender=kw['lender']
        system.date_modified = datetime.utcnow()
        if kw.get('shared'):
            system.shared=kw['shared']
        else:
            system.shared=False
        if kw.get('private'):
            system.private=kw['private']
        else:
            system.private=False

        # Change Lab Controller
        if kw['lab_controller_id'] == 0:
            system.lab_controller_id = None
        else:
            system.lab_controller_id = kw['lab_controller_id']
        system.mac_address=kw['mac_address']
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_keys(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add Key for %s" % id) )
            redirect("/")
        # Add a Key/Value Pair
        if kw.get('key_name') and kw.get('key_value'):
            key_value = Key_Value(kw['key_name'],kw['key_value'])
            system.key_values.append(key_value)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Key/Value', "", "%s/%s" % (kw['key_name'],kw['key_value']) )
            system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_arch(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add arch for %s" % id) )
            redirect("/")
        # Add an Arch
        if kw.get('arch').get('text'):
            arch = Arch.by_name(kw['arch']['text'])
            system.arch.append(arch)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Arch', "", kw['arch']['text'])
            system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_group(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add Group for %s" % id) )
            redirect("/")
        # Add a Group
        if kw.get('group').get('text'):
            try:
                group = Group.by_name(kw['group']['text'])
            except InvalidRequestError:
                flash(_(u"%s is an Invalid Group" % kw['group']['text']))
                redirect("/view/%s" % system.fqdn)
            system.groups.append(group)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Group', "", kw['group']['text'])
            gactivity = GroupActivity(identity.current.user, 'WEBUI', 'Added', 'System', "", system.fqdn)
            group.activity.append(gactivity)
            system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    def action_power(self, id, action, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to look up system id:%s via your login" % id) )
            redirect("/")
        if system.user != identity.current.user:
            flash( _(u"You are not the current User for %s" % system) )
            redirect("/")
        (rc, result) =  system.action_power(action)
        activity = SystemActivity(identity.current.user, 'WEBUI', action, 'Power', "", result)
        system.activity.append(activity)
        if rc == 0:
            flash(_(u"Successfully %s %s" % (action, system.fqdn)))
        else:
            flash(_(u"Failed to %s %s, error: %s:%s" % (action, system.fqdn, rc, result)))
        redirect("/view/%s" % system.fqdn)

    @expose()
    def action_provision(self, id, prov_install=None, ks_meta=None, 
                             koptions=None, koptions_post=None, reboot=None):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Provision for %s" % id) )
            redirect("/")
        try:
            distro = Distro.by_id(prov_install)
        except InvalidRequestError:
            flash( _(u"Unable to lookup distro for %s" % id) )
            redirect("/")
        (rc, result) = system.action_provision(distro = distro,
                                               ks_meta = ks_meta,
                                       kernel_options = koptions,
                                  kernel_options_post = koptions_post)
        activity = SystemActivity(identity.current.user, 'WEBUI', 'Provision', 'Distro', "", "%s: %s" % (result, distro.install_name))
        system.activity.append(activity)
        result = "Provision: %s,%s" % (rc, result)
        if rc == 0:
            if reboot:
                (rc, result2) =  system.action_power(action="reboot")
                result = "%s Reboot: %s" % (result, result2)
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Reboot', 'Power', "", result2)
                system.activity.append(activity)
        flash(_(u"%s" % result))
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_note(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Note for %s" % id) )
            redirect("/")
        # Add a Note
        if kw.get('note'):
            note = Note(user=identity.current.user,text=kw['note'])
            system.notes.append(note)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Note', "", kw['note'])
            system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_exclude(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Exclude flags for %s" % id) )
            redirect("/")
        for arch in system.arch:
        # Update Excluded Families
            if kw.get('excluded_families') and \
             kw['excluded_families'].has_key(arch.arch):
                if isinstance(kw['excluded_families'][arch.arch], list):
                    excluded_osmajor = [int(i) for i in kw['excluded_families'][arch.arch]]
                else:
                    excluded_osmajor = [int(kw['excluded_families'][arch.arch])]
                for new_families in excluded_osmajor:
                    if new_families not in [osmajor.osmajor.id for osmajor in system.excluded_osmajor_byarch(arch)]:
                        new_excluded_osmajor = ExcludeOSMajor(osmajor=OSMajor.by_id(new_families),arch=arch)
                        activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Excluded_families', "", "%s/%s" % (new_excluded_osmajor.osmajor, arch))
                        system.excluded_osmajor.append(new_excluded_osmajor)
                        system.activity.append(activity)
            else:
                excluded_osmajor = []
            for old_families in system.excluded_osmajor_byarch(arch):
                if old_families.osmajor.id not in excluded_osmajor:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Excluded_families', "%s/%s" % (old_families.osmajor, arch), "")
                    session.delete(old_families)
                    system.activity.append(activity)
                    
            if kw.get('excluded_families_subsection') and \
             kw['excluded_families_subsection'].has_key(arch.arch):
                if isinstance(kw['excluded_families_subsection'][arch.arch], list):
                    excluded_osversion = [int(i) for i in kw['excluded_families_subsection'][arch.arch]]
                else:
                    excluded_osversion = [int(kw['excluded_families_subsection'][arch.arch])]
                for new_osversion in excluded_osversion:
                    if new_osversion not in [osversion.osversion.id for osversion in system.excluded_osversion_byarch(arch)]:
                        new_excluded_osversion = ExcludeOSVersion(osversion=OSVersion.by_id(new_osversion),arch=arch)
                        activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Excluded_families', "", "%s/%s" % (new_excluded_osversion.osversion, arch))
                        system.excluded_osversion.append(new_excluded_osversion)
                        system.activity.append(activity)
            else:
                excluded_osversion = []
            for old_osversion in system.excluded_osversion_byarch(arch):
                if old_osversion.osversion.id not in excluded_osversion:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Excluded_families', "%s/%s" % (old_osversion.osversion, arch), "")
                    session.delete(old_osversion)
                    system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    def remove_install(self, system_id, arch_id, **kw):
        try:
            system = System.by_id(system_id, identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to remove Install Option for %s" % system_id) )
            redirect("/")
        try:
            arch = Arch.by_id(arch_id)
        except InvalidRequestError:
            flash( _(u"Unable to lookup arch for %s" % arch_id) )
            redirect("/")
        
        if kw.get('osversion_id'):
            # remove osversion option
            osversion = OSVersion.by_id(int(kw['osversion_id']))
            system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion] = None
        elif kw.get('osmajor_id'):
            # remove osmajor option
            osmajor = OSMajor.by_id(int(kw['osmajor_id']))
            system.provisions[arch].provision_families[osmajor] = None
        else:
            # remove arch option
            system.provisions[arch] = None
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_install(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Install Options for %s" % id) )
            redirect("/")
        # Add an install option
        if kw.get('prov_ksmeta') or kw.get('prov_koptions') or \
           kw.get('prov_koptionspost'):
            arch = Arch.by_id(int(kw['prov_arch']))
            if int(kw['prov_osversion']) != 0:
                osversion = OSVersion.by_id(int(kw['prov_osversion']))
                if system.provisions.has_key(arch):
                    if system.provisions[arch].provision_families.has_key(osversion.osmajor):
                        if system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates.has_key(osversion):
                            provision = system.provisions[arch].provision_families[osmajor].provision_family_updates[osversion]
                            action = "Changed"
                        else:
                            provision = ProvisionFamilyUpdate()
                            action = "Added"
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s/%s' % (arch, osversion), provision.ks_meta, kw['prov_ksmeta']))
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s/%s' % (arch, osversion), provision.kernel_options, kw['prov_koptions']))
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s/%s' % (arch, osversion), provision.kernel_options_post, kw['prov_koptionspost']))
                        provision.ks_meta=kw['prov_ksmeta']
                        provision.kernel_options=kw['prov_koptions']
                        provision.kernel_options_post=kw['prov_koptionspost']
                        provision.osversion = osversion
                        system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion] = provision
                
            elif int(kw['prov_osmajor']) != 0:
                osmajor = OSMajor.by_id(int(kw['prov_osmajor']))
                if system.provisions.has_key(arch):
                    if system.provisions[arch].provision_families.has_key(osmajor):
                        provision = system.provisions[arch].provision_families[osmajor]
                        action = "Changed"
                    else:
                        provision = ProvisionFamily()
                        action = "Added"
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s/%s' % (arch, osmajor), provision.ks_meta, kw['prov_ksmeta']))
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s/%s' % (arch, osmajor), provision.kernel_options, kw['prov_koptions']))
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s/%s' % (arch, osmajor), provision.kernel_options_post, kw['prov_koptionspost']))
                    provision.ks_meta=kw['prov_ksmeta']
                    provision.kernel_options=kw['prov_koptions']
                    provision.kernel_options_post=kw['prov_koptionspost']
                    provision.osmajor=osmajor
                    system.provisions[arch].provision_families[osmajor] = provision
            else:
                if system.provisions.has_key(arch):
                    provision = system.provisions[arch]
                    action = "Changed"
                else:
                    provision = Provision()
                    action = "Added"
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s' % arch, provision.ks_meta, kw['prov_ksmeta']))
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s' % arch, provision.kernel_options, kw['prov_koptions']))
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s' % arch, provision.kernel_options_post, kw['prov_koptionspost']))
                provision.ks_meta=kw['prov_ksmeta']
                provision.kernel_options=kw['prov_koptions']
                provision.kernel_options_post=kw['prov_koptionspost']
                provision.arch=arch
                system.provisions[arch] = provision
        redirect("/view/%s" % system.fqdn)

    @cherrypy.expose
    def lab_controllers(self, machine_account):
        return [lc.fqdn for lc in LabController.query()]
    
    def pick_common(self, distro=None, user=None, xml=None):
        distro = Distro.by_install_name(distro)
        systems = distro.systems(user)
        #FIXME Should validate XML before processing.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(xml)):
            if callable(getattr(child, 'filter')):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        if joins:
            systems = systems.filter(and_(*joins))
        if queries:
            systems = systems.filter(and_(*queries))
        return systems
        
    @cherrypy.expose
    def system_pick(self, machine_account, distro=None, user=None, xml=None):
        if not distro:
            return (0,"You must supply a distro")
        if not user:
            return (0,"You must supply a user name")
        if not xml:
            return (0,"No xml query provided")

        user = User.by_user_name(user)
        systems = self.pick_common(distro, user, xml)

        hit = False
        for system in systems:
            # If the system doesn't have a current user then take it
            if session.connection(System).execute(system_table.update(
                     and_(system_table.c.id==system.id,
                          system_table.c.user_id==None)), 
                           user_id=user.user_id).rowcount == 1:
                hit = True
                break

        if hit:
            # We have a match and its available!
            return (dict(fqdn    = system.fqdn,
                         mac_address = '%s' % system.mac_address), 1)
        elif systems.count():
            # We have matches but none are available right now
            system = systems.first()
            return (dict(fqdn    = system.fqdn,
                         mac_address = '%s' % system.mac_address), 0)
        else:
            # Nothing matches what the user requested.
            return (None, -1)

    @cherrypy.expose
    def system_validate(self, machine_account, distro=None, user=None, xml=None):
        if not distro:
            return (0,"You must supply a distro")
        if not user:
            return (0,"You must supply a user name")
        if not xml:
            return (0,"No xml query provided")

        user = User.by_user_name(user)
        systems = self.pick_common(distro, user, xml)

        if systems.count():
            # We have matches 
            system = systems.first()
            return (dict(fqdn    = system.fqdn,
                         mac_address = '%s' % system.mac_address), 0)
        else:
            # Nothing matches what the user requested.
            return (None, -1)
            
    @cherrypy.expose
    def system_return(self, machine_account, fqdn=None, full_name=None):
        if not fqdn:
            return (0,"You must supply a system")
        if not full_name:
            return (0,"You must supply a user name")

        user = User.by_user_name(full_name)
        try:
            system = System.by_fqdn(fqdn,identity.current.user)
        except InvalidRequestError:
            return (0, "Invalid system")
        if system.user == user:
            activity = SystemActivity(system.user, 'VIA %s' % machine_account, "Returned", 'User', '%s' % system.user, '')
            system.activity.append(activity)
            system.action_return()
        return
        

    @cherrypy.expose
    def legacypush(self, machine_account, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN")
        if not inventory:
            return (0,"No inventory data provided")

        try:
            system = System.query.filter(System.fqdn == fqdn).one()
        except InvalidRequestError:
            system = System(fqdn=fqdn)
        return system.update_legacy(inventory)

    @cherrypy.expose
    def push(self, machine_account, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN")
        if not inventory:
            return (0,"No inventory data provided")

        try:
            system = System.query.filter(System.fqdn == fqdn).one()
        except InvalidRequestError:
            # New system, add it.
            system = System(fqdn=fqdn)
        return system.update(inventory)

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

    @expose()
    def robots_txt(self):
        return "User-agent: *\nDisallow: /\n"

    @expose()
    def favicon_ico(self):
        static_dir = config.get('static_filter.dir', path="/static")
        filename = join(os.path.normpath(static_dir), 'images', 'favicon.ico')
        return serve_file(filename)

#    @expose(template='medusa.templates.activity')
#    def activity(self, *args, **kw):
# TODO This is mainly for testing
# if it hangs around it should check for admin access
#        return dict(title="Activity", search_bar=None, activity = Activity.all())
#
