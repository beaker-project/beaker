from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot
from medusa.helpers import *
from tempfile import NamedTemporaryFile
from cherrypy.lib.cptools import serve_file

import cherrypy

from model import *
import string
import csv

def smart_bool(s):
    if s is True or s is False:
        return s
    t = str(s).strip().lower()
    if t == 'true':
        return True
    if t == 'false':
        return False
    return s

class CSV(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    upload     = widgets.FileField(name='csv_file', label='Import CSV')
    download   = widgets.RadioButtonList(name='csv_type', label='CSV Type',
                               options=[('system', 'Systems'), 
                                        ('labinfo', 'System LabInfo'), 
                                        ('exclude', 'System Excluded Families'), 
                                        ('install', 'System Install Options'),
                                        ('keyvalue', 'System Key/Values'),
                                        ('system_groups', 'System Groups')], 
                                                           default='system')

    importform = widgets.TableForm(
        'import',
        fields = [upload],
        action = 'import data',
        submit_text = _(u'Import CSV'),
    )

    exportform = widgets.TableForm(
        'export',
        fields = [download],
        action = 'export data',
        submit_text = _(u'Export CSV'),
    )

    @expose(template='medusa.templates.form')
    def index(self, **kw):
        return dict(
            form = self.exportform,
            action = './action_export',
            options = {},
            value = kw,
        )

    @expose(template='medusa.templates.form-post')
    def csv_import(self, **kw):
        return dict(
            form = self.importform,
            action = './action_import',
            options = {},
            value = kw,
        )

    @expose()
    def action_export(self, csv_type, *args, **kw):
        file = NamedTemporaryFile()
        log = self.to_csv(file, csv_type)
        file.seek(0)
        return serve_file(file.name, contentType="text/csv", 
                                     disposition="attachment",
                                     name="%s.csv" % csv_type)
        

    @expose(template='medusa.templates.csv_import')
    def action_import(self, csv_file, *args, **kw):
        """
        TurboGears method to import data from csv
        """
        log = []
        csv_data = csv_file.file
        dialect = csv.Sniffer().sniff(csv_data.read(1024))
        csv_data.seek(0)
        # ... process CSV file contents here ...
        reader = csv.DictReader(csv_data, dialect=dialect)
        for data in reader:
            if 'fqdn' in data and 'csv_type' in data:
                try:
                    system = System.query.filter(System.fqdn == data['fqdn']).one()
                except InvalidRequestError:
                    system = System(fqdn=data['fqdn'],
                                    owner=identity.current.user)
                if system.can_admin(identity.current.user):
                    # Remove fqdn, can't change that via csv.
                    data.pop('fqdn')
                    log.extend(self.from_csv(system, data))
                else:
                    log.append("You are not the owner of %s" % system.fqdn)
            else:
                log.append("Missing fqdn and csv_type from record")

        return dict(log = log)

    @classmethod
    def to_csv(cls, file, csv_type):
        log = []
        if csv_type in csv_types:
            csv_types[csv_type]._to_csv(file)
        else:
            log.append("Invalid csv_type %s" % csv_type)
        return log

    @classmethod
    def _to_csv(cls, file):
        """
        Export objects into a csv file.
        """
        header = csv.writer(file)
        header.writerow(['csv_type'] + cls.csv_keys)
        writer = csv.DictWriter(file, ['csv_type'] + cls.csv_keys)
        for item in cls.query():
            for data in cls.to_datastruct(item):
                data['csv_type'] = cls.csv_type
                writer.writerow(data)

    @classmethod
    def from_csv(cls, system, data):
        """
        Process data file
        """
        log = []
        if data['csv_type'] in csv_types:
            csv_type = data['csv_type']
            # Remove csv_type now that we know what we want to do.
            data.pop('csv_type')
            log = csv_types[csv_type]._from_csv(system,data,csv_type)
        else:
            log.append("Invalid csv_type %s" % data['csv_type'])
        return log

    @classmethod
    def _from_csv(cls,system,data,csv_type=None):
        """
        Import data from CSV file into LabInfo Objects
        """
        log = []
        csv_object = getattr(system, csv_type, None)
        for key in data.keys():
            if key in cls.csv_keys:
                current_data = getattr(csv_object, key, None)
                if data[key]:
                    newdata = smart_bool(data[key])
                else:
                    newdata = None
                if str(newdata) != str(current_data):
                    activity = SystemActivity(identity.current.user, 'CSV', 'Changed', key, '%s' % current_data, '%s' % newdata)
                    system.activity.append(activity)
                    log.append("%s: %s Changed from %s to %s" % (system.fqdn, key, current_data, newdata))
                    setattr(csv_object,key,newdata)

        return log

    def to_datastruct(self):
        datastruct = dict()
        for csv_key in self.csv_keys:
            datastruct[csv_key] = getattr(self, csv_key, None)
        yield datastruct

class CSV_System(CSV):
    csv_type = 'system'
    reg_keys = ['fqdn', 'deleted', 'lender', 'location', 
                'mac_address', 'memory', 'model',
                'serial', 'shared', 'vendor']

    spec_keys = ['arch', 'lab_controller', 'owner', 
                 'secret', 'status','type']

    csv_keys = reg_keys + spec_keys

    @classmethod
    def query(cls):
        for system in System.query():
            yield CSV_System(system)

    @classmethod
    def _from_csv(cls,system,data,csv_type=None):
        """
        Import data from CSV file into LabInfo Objects
        """
        log = []
        for key in data.keys():
            if key in cls.reg_keys:
                if data[key]:
                    newdata = smart_bool(data[key])
                else:
                    newdata = None
                current_data = getattr(system, key, None)
                if str(newdata) != str(current_data):
                    activity = SystemActivity(identity.current.user, 'CSV', 'Changed', key, '%s' % current_data, '%s' % newdata)
                    system.activity.append(activity)
                    log.append("%s: %s Changed from %s to %s" % (system.fqdn, key, current_data, newdata))
                    setattr(system,key,newdata)

        # import arch
        if 'arch' in data:
            arch_objs = []
            if data['arch']:
                arches = data['arch'].split(',')
                for arch in arches:
                    arch_objs.append(Arch.by_name(arch))
            if system.arch != arch_objs:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'arch', '%s' % system.arch, '%s' % arch_objs)
                system.activity.append(activity)
                log.append("%s: %s Changed from %s to %s" % (system.fqdn, 'lab_controller', system.arch, arch_objs))
                system.arch = arch_objs

        # import labController
        if 'lab_controller' in data:
            if data['lab_controller']:
                try:
                    lab_controller = LabController.by_name(data['lab_controller'])
                except InvalidRequestError:
                    log.append("Invalid lab controller %s" % data['lab_controller'])
                    return log
            else:
                lab_controller = None
            if system.lab_controller != lab_controller:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'lab_controller', '%s' % system.lab_controller, '%s' % lab_controller)
                system.activity.append(activity)
                log.append("%s: %s Changed from %s to %s" % (system.fqdn, 'lab_controller', system.lab_controller, lab_controller))
                system.lab_controller = lab_controller
            
        # import owner
        if 'owner' in data:
            if data['owner']:
                owner = User.by_user_name(data['owner'])
                if not owner:
                    log.append("Invalid User %s" % data['owner'])
                    return log
            else:
                owner = None
            if system.owner != owner:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'owner', '%s' % system.owner, '%s' % owner)
                system.activity.append(activity)
                log.append("%s: %s Changed from %s to %s" % (system.fqdn, 'owner', system.owner, owner))
                system.owner = owner
        # import status
        if 'status' in data:
            if not data['status']:
                log.append("Invalid Status None")
                return log
            try:
                systemstatus = SystemStatus.by_name(data['status'])
            except InvalidRequestError:
                log.append("Invalid Status %s" % data['status'])
                return log
            if system.status != systemstatus:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'status', '%s' % system.status, '%s' % systemstatus)
                system.activity.append(activity)
                log.append("%s: %s Changed from %s to %s" % (system.fqdn, 'status', system.status, systemstatus))
                system.status = systemstatus
        # import type
        if 'type' in data:
            if not data['type']:
                log.append("Invalid Type None")
                return log
            try:
                systemtype = SystemType.by_name(data['type'])
            except InvalidRequestError:
                log.append("Invalid Type %s" % data['type'])
                return log
            if system.type != systemtype:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'type', '%s' % system.type, '%s' % systemtype)
                system.activity.append(activity)
                log.append("%s: %s Changed from %s to %s" % (system.fqdn, 'type', system.type, systemtype))
                system.type = systemtype
        # import secret
        if 'secret' in data:
            if not data['secret']:
                log.append("Invalid secret None")
                return log
            newdata = smart_bool(data['secret'])
            if system.private != newdata:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'secret', '%s' % system.private, '%s' % newdata)
                system.activity.append(activity)
                log.append("%s: %s Changed from %s to %s" % (system.fqdn, 'secret', system.private, newdata))
                system.private = newdata

        return log

    def __init__(self, system):
        self.system = system
        self.fqdn = system.fqdn
        self.arch = ','.join([arch.arch for arch in system.arch])
        self.deleted = system.deleted
        self.lab_controller = system.lab_controller
        self.lender = system.lender
        self.location = system.location
        self.mac_address = system.mac_address
        self.memory = system.memory
        self.model = system.model
        self.owner = system.owner
        self.secret = system.private
        self.serial = system.serial
        self.shared = system.shared
        self.status = system.status
        self.type = system.type
        self.vendor = system.vendor

class CSV_LabInfo(CSV):
    csv_type = 'labinfo'
    csv_keys = ['fqdn', 'orig_cost', 'curr_cost', 'dimensions', 'weight', 'wattage', 'cooling']

    @classmethod
    def query(cls):
        for labinfo in LabInfo.query():
            yield CSV_LabInfo(labinfo)

    def __init__(self, labinfo):
        self.labinfo = labinfo
        self.fqdn = labinfo.system.fqdn
        self.orig_cost = labinfo.orig_cost
        self.curr_cost = labinfo.curr_cost
        self.dimensions = labinfo.dimensions
        self.weight = labinfo.weight
        self.wattage = labinfo.wattage
        self.cooling = labinfo.cooling

class CSV_Exclude(CSV):
    csv_type = 'exclude'
    csv_keys = ['fqdn', 'arch', 'family', 'update', 'excluded']

    @classmethod
    def query(cls):
        for exclude in ExcludeOSMajor.query():
            yield CSV_Exclude(exclude)
        for exclude in ExcludeOSVersion.query():
            yield CSV_Exclude(exclude)

    @classmethod
    def _from_csv(cls,system,data,csv_type=None):
        """
        Import data from CSV file into System Objects
        """
        log = []
        
        arch = Arch.by_name(data['arch'])

        if data['update'] and data['family']:
            osversion = OSVersion.by_name(OSMajor.by_name(data['family']),
                                                            data['update'])
            if osversion not in [oldosversion.osversion for oldosversion in system.excluded_osversion_byarch(arch)]:
                if data['excluded'] == 'True':
                    exclude_osversion = ExcludeOSVersion(osversion=osversion,
                                                         arch=arch)
                    system.excluded_osversion.append(exclude_osversion)
                    activity = SystemActivity(identity.current.user, 'CSV', 'Added', 'Excluded_families', '', '%s/%s' % (osversion, arch))
                    system.activity.append(activity)
                    log.append("%s: Added %s.%s exclude%s" % (
                                                                system.fqdn,
                                                                data['family'],
                                                                data['update'],
                                                                   )
                              )
            else:
                if data['excluded'] == 'False':
                    for old_osversion in system.excluded_osversion_byarch(arch):
                        if old_osversion.osversion == osversion:
                            activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Excluded_families', '%s/%s' % (old_osversion.osversion, arch),'')
                            system.activity.append(activity)
                            session.delete(old_osversion)
                            log.append("%s: Removed %s.%s exclude" % (
                                                                system.fqdn,
                                                                data['family'],
                                                                data['update'],
                                                                       )
                                      )

        if not data['update'] and data['family']:
            osmajor = OSMajor.by_name(data['family'])
            if osmajor not in [oldosmajor.osmajor for oldosmajor in system.excluded_osmajor_byarch(arch)]:
                if data['excluded'] == 'True':
                    exclude_osmajor = ExcludeOSMajor(osmajor=osmajor, arch=arch)
                    system.excluded_osmajor.append(exclude_osmajor)
                    activity = SystemActivity(identity.current.user, 'CSV', 'Added', 'Excluded_families', '', '%s/%s' % (osmajor, arch))
                    system.activity.append(activity)
                    log.append("%s: Added %s exclude" % (
                                                                system.fqdn,
                                                                data['family'],
                                                                   )
                              )
            else:
                if data['excluded'] == 'False':
                    for old_osmajor in system.excluded_osmajor_byarch(arch):
                        if old_osmajor.osmajor == osmajor:
                            activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Excluded_families', '%s/%s' % (old_osmajor.osmajor, arch),'')
                            system.activity.append(activity)
                            session.delete(old_osmajor)
                            log.append("%s: Removed %s exclude" % (
                                                                system.fqdn,
                                                                data['family'],
                                                                       )
                                      )

        return log

    def __init__(self, exclude):
        self.fqdn = exclude.system.fqdn
        self.arch = exclude.arch
        self.excluded = True
        if type(exclude) == ExcludeOSMajor:
            self.family = exclude.osmajor
            self.update = None
        if type(exclude) == ExcludeOSVersion:
            self.family = exclude.osversion.osmajor
            self.update = exclude.osversion.osminor

class CSV_Install(CSV):
    csv_type = 'install'
    csv_keys = ['fqdn', 'arch', 'family', 'update', 'ks_meta', 'kernel_options', 'kernel_options_post' ]

    @classmethod
    def query(cls):
        for install in Provision.query():
            yield CSV_Install(install)

    @classmethod
    def _from_csv(cls,system,data,csv_type=None):
        """
        Import data from CSV file into System Objects
        """
        log = []
        family = None
        update = None

        # Arch is required
        if 'arch' in data:
            arch = Arch.by_name(data['arch'])
        else:
            log.append("Error! Missing arch")
            return log

        # pull in update and family if present
        if 'family' in data:
            family = data['family']
            if family:
                try:
                    family = OSMajor.by_name(family)
                except InvalidRequestError:
                    log.append("Error! Invalid family %s" % data['family'])
                    return log
        if 'update' in data:
            update = data['update']
            if update:
                if not family:
                    log.append("Error! You must specify Family along with Update")
                    return log
                try:
                    update = OSVersion.by_name(family, update)
                except InvalidRequestError:
                    log.append("Error! Invalid update %s" % data['update'])
                    return log

        #Import Update specific
        if update and family:
            if system.provisions.has_key(arch):
                system_arch = system.provisions[arch]
            else:
                system_arch = Provision(arch=arch)
                system.provisions[arch] = system_arch

            if system_arch.provision_families.has_key(family):
                system_provfam = system_arch.provision_families[family]
            else:
                system_provfam = ProvisionFamily(osmajor=family)
                system_arch.provision_families[family] = system_provfam

            if system_provfam.provision_family_updates.has_key(update):
                prov = system_provfam.provision_family_updates[update]
            else:
                prov = ProvisionFamilyUpdate(osversion=update)
                system_provfam.provision_family_updates[update] = prov
                       
        #Import Family specific
        if family and not update:
            if system.provisions.has_key(arch):
                system_arch = system.provisions[arch]
            else:
                system_arch = Provision(arch=arch)
                system.provisions[arch] = system_arch

            if system_arch.provision_families.has_key(family):
                prov = system_arch.provision_families[family]
            else:
                prov = ProvisionFamily(osmajor=family)
                system_arch.provision_families[family] = prov
                       
        #Import Arch specific
        if not family and not update:
            if system.provisions.has_key(arch):
                prov = system.provisions[arch]
            else:
                prov = Provision(arch=arch)
                system.provisions[arch] = prov

        if 'ks_meta' in data and prov.ks_meta != data['ks_meta']:
            log.append("%s: ks_meta changed from %s to %s" % (system.fqdn,
                                                              prov.ks_meta,
                                                              data['ks_meta']))
            prov.ks_meta = data['ks_meta']
        if 'kernel_options' in data and prov.kernel_options != data['kernel_options']:
            log.append("%s: kernel_options changed from %s to %s" % (system.fqdn,
                                                              prov.kernel_options,
                                                              data['kernel_options']))
            prov.kernel_options = data['kernel_options']
        if 'kernel_options_post' in data and prov.kernel_options_post != data['kernel_options_post']:
            log.append("%s: kernel_options_post changed from %s to %s" % (system.fqdn,
                                                              prov.kernel_options_post,
                                                              data['kernel_options_post']))
            prov.kernel_options_post = data['kernel_options_post']

        return log

    def __init__(self, install):
        self.install = install
        if install.system:
            self.fqdn = install.system.fqdn
        else:
            self.fqdn = None
        self.arch = install.arch

    def to_datastruct(self):
        datastruct = dict(fqdn = self.fqdn,
                          arch = self.arch,
                          family = None,
                          update = None,
                          ks_meta = self.install.ks_meta,
                          kernel_options = self.install.kernel_options,
                          kernel_options_post = self.install.kernel_options_post)
        yield datastruct
        if self.install.provision_families:
            for family in self.install.provision_families.keys():
                prov_family = self.install.provision_families[family]
                datastruct['family'] = family
                datastruct['ks_meta'] = prov_family.ks_meta
                datastruct['kernel_options'] = prov_family.kernel_options
                datastruct['kernel_options_post'] = prov_family.kernel_options_post
                yield datastruct
                if prov_family.provision_family_updates:
                    for update in prov_family.provision_family_updates.keys():
                        prov_update = prov_family.provision_family_updates[update]
                        datastruct['update'] = update.osminor
                        datastruct['ks_meta'] = prov_update.ks_meta
                        datastruct['kernel_options'] = prov_update.kernel_options
                        datastruct['kernel_options_post'] = prov_update.kernel_options_post
                        yield datastruct
                    datastruct['update'] = None
        
class CSV_KeyValue(CSV):
    pass

class CSV_SystemGroups(CSV):
    pass

csv_types = dict( system = CSV_System,
                  labinfo = CSV_LabInfo,
                  exclude = CSV_Exclude,
                  install = CSV_Install,
                  keyvalue = CSV_KeyValue,
                  system_groups = CSV_SystemGroups)
