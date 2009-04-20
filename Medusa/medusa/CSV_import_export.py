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

class CSV(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    upload     = widgets.FileField(name='csv_file', label='Import CSV')
    download   = widgets.RadioButtonList(name='csv_type', label='CSV Type',
                               options=[('system', 'System'), 
                                        ('labinfo', 'LabInfo'), 
                                        ('exclude', 'Excluded Families'), 
                                        ('install', 'Install Options')], 
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
            log = csv_types[csv_type]._from_csv(system,data)
        else:
            log.append("Invalid csv_type %s" % data['csv_type'])
        return log

    def to_datastruct(self):
        datastruct = dict()
        for csv_key in self.csv_keys:
            datastruct[csv_key] = getattr(self, csv_key, None)
        yield datastruct

class CSV_System(CSV):
    csv_type = 'system'
    csv_keys = ['fqdn', 'arch', 'deleted', 'lab_controller',
                'lender', 'location', 'mac_address', 'memory', 'model',
                'owner', 'secret', 'serial', 'shared', 'status',
                'type', 'vendor']

    @classmethod
    def query(cls):
        for system in System.query():
            yield CSV_System(system)

    @classmethod
    def _from_csv(cls,system,data):
        """
        Import data from CSV file into System Objects
        """
        log = []

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

    @classmethod
    def _from_csv(cls,system,data):
        """
        Import data from CSV file into LabInfo Objects
        """
        log = []

        return log

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
    def _from_csv(cls,system,data):
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
                    log.append("Adding %s.%s exclude to host %s" % (
                                                                data['family'],
                                                                data['update'],
                                                                system.fqdn
                                                                   )
                              )
            else:
                if data['excluded'] == 'False':
                    for old_osversion in system.excluded_osversion_byarch(arch):
                        if old_osversion.osversion == osversion:
                            activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Excluded_families', '%s/%s' % (old_osversion.osversion, arch),'')
                            system.activity.append(activity)
                            session.delete(old_osversion)
                            log.append("Removing %s.%s exclude from host %s" % (
                                                                data['family'],
                                                                data['update'],
                                                                system.fqdn
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
                    log.append("Adding %s exclude to host %s" % (
                                                                data['family'],
                                                                system.fqdn
                                                                   )
                              )
            else:
                if data['excluded'] == 'False':
                    for old_osmajor in system.excluded_osmajor_byarch(arch):
                        if old_osmajor.osmajor == osmajor:
                            activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Excluded_families', '%s/%s' % (old_osmajor.osmajor, arch),'')
                            system.activity.append(activity)
                            session.delete(old_osmajor)
                            log.append("Removing %s exclude from host %s" % (
                                                                data['family'],
                                                                system.fqdn
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
    def _from_csv(cls,system,data):
        """
        Import data from CSV file into System Objects
        """
        log = []

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
        
csv_types = dict( system = CSV_System,
                  labinfo = CSV_LabInfo,
                  exclude = CSV_Exclude,
                  install = CSV_Install)
