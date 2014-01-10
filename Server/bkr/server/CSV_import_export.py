
from turbogears.database import session
from turbogears import expose, widgets
from sqlalchemy.exc import InvalidRequestError
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from tempfile import NamedTemporaryFile
from cherrypy.lib.cptools import serve_file
from bkr.server.model import (System, SystemType, Activity, SystemActivity,
                              User, Group, LabController, LabInfo,
                              OSMajor, OSVersion,
                              ExcludeOSMajor, ExcludeOSVersion,
                              SystemStatus, Power, PowerType, Arch,
                              Provision, ProvisionFamily,
                              ProvisionFamilyUpdate,
                              Key, Key_Value_Int, Key_Value_String)
from bkr.server.widgets import HorizontalForm, RadioButtonList
from kid import XML

import csv
import datetime
import logging
logger = logging.getLogger(__name__)

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

    export_help_text = XML(u'<span>Refer to the <a href="http://beaker-project.org/docs/'
                           'admin-guide/interface.html#export" target="_blank">'
                           'documentation</a> to learn more about the exported data.</span>').expand()
    import_help_text = XML(u'<span>Refer to the <a href="http://beaker-project.org/docs/'
                           'admin-guide/interface.html#import" target="_blank">'
                           'documentation</a> for details about the supported CSV format.</span>').expand()

    upload     = widgets.FileField(name='csv_file', label='Import CSV', \
                                   help_text = import_help_text)
    download   = RadioButtonList(name='csv_type', label='CSV Type',
                               options=[('system', 'Systems'),
                                        ('system_id', 'Systems (for modification)'), 
                                        ('labinfo', 'System LabInfo'), 
                                        ('power', 'System Power'),
                                        ('exclude', 'System Excluded Families'), 
                                        ('install', 'System Install Options'),
                                        ('keyvalue', 'System Key/Values'),
                                        ('system_group', 'System Groups'),
                                        ('user_group', 'User Groups')], 
                                 default='system',
                                 help_text = export_help_text)

    importform = HorizontalForm(
        'import',
        fields = [upload],
        action = 'import data',
        submit_text = _(u'Import CSV'),
    )

    exportform = HorizontalForm(
        'export',
        fields = [download],
        action = 'export data',
        submit_text = _(u'Export CSV'),
    )

    @expose(template='bkr.server.templates.form')
    @identity.require(identity.not_anonymous())
    def index(self, **kw):
        return dict(
            form = self.exportform,
            title=_(u'CSV Export'),
            action = './action_export',
            options = {},
            value = kw,
        )

    @expose(template='bkr.server.templates.form-post')
    @identity.require(identity.in_group('admin'))
    def csv_import(self, **kw):
        return dict(
            form = self.importform,
            title=_(u'CSV Import'),
            action = './action_import',
            options = {},
            value = kw,
        )

    @expose()
    @identity.require(identity.not_anonymous())
    def action_export(self, csv_type, *args, **kw):
        file = NamedTemporaryFile()
        log = self.to_csv(file, csv_type)
        file.seek(0)

        return serve_file(file.name, contentType="text/csv",
                                     disposition="attachment",
                                     name="%s.csv" % csv_type)

    @expose(template='bkr.server.templates.csv_import')
    @identity.require(identity.in_group('admin'))
    def action_import(self, csv_file, *args, **kw):
        """
        TurboGears method to import data from csv
        """
        log = []
        try:
            # ... process CSV file contents here ...
            missing = object()
            reader = csv.DictReader(csv_file.file, restkey=missing, restval=missing)
            for data in reader:
                if missing in data:
                    log.append('Too many fields on line %s (expecting %s)'
                            % (reader.line_num, len(reader.fieldnames)))
                    continue
                if any(value is missing for value in data.itervalues()):
                    missing_fields = [field for field, value in data.iteritems()
                            if value is missing]
                    log.append('Missing fields on line %s: %s' % (reader.line_num,
                            ', '.join(missing_fields)))
                    continue
                if 'csv_type' in data:
                    if data['csv_type'] in system_types and ('fqdn' in data or 'id' in data):
                        if data.get('id', None):
                            try:
                                system = System.query.filter(System.id == data['id']).one()
                            except InvalidRequestError as e:
                                log.append('Error importing system on line %s: Non-existent system id' %
                                           reader.line_num)
                                continue
                        else:
                            try:
                                system = System.query.filter(System.fqdn == data['fqdn']).one()
                            except InvalidRequestError:
                                # Create new system with some defaults
                                # Assume the system is broken until proven otherwise.
                                # Also assumes its a machine.  we have to pick something
                                try:
                                    system = System(fqdn=data['fqdn'],
                                                owner=identity.current.user,
                                                type=SystemType.machine,
                                                status=SystemStatus.broken)
                                except ValueError as e:
                                    log.append('Error importing system on line %s: %s' %
                                               (reader.line_num, str(e)))
                                    continue

                        if system.can_edit(identity.current.user):
                            # we change the FQDN only when a valid system id is supplied
                            if not data.get('id', None):
                                data.pop('fqdn')
                            try:
                                self.from_csv(system, data, log)
                            except ValueError as e:
                                log.append('Error importing system on line %s: %s' %
                                           (reader.line_num, str(e)))
                                if system.id:
                                    # System already existed but some or all of the
                                    #  import data was invalid.
                                    session.expire(system)
                                else:
                                    # System didn't exist before import but some
                                    # or all of the import data was invalid.
                                    session.expunge(system)
                                    del(system)
                            else:
                                session.add(system)
                                session.flush([system])
                        else:
                            log.append("You are not the owner of %s" % system.fqdn)
                    elif data['csv_type'] == 'user_group' and \
                      'user' in data:
                        user = User.by_user_name(data['user'])
                        if user:
                            CSV_GroupUser.from_csv(user, data, log)
                        else:
                            log.append('%s is not a valid user' % data['user'])
                    else:
                        log.append("Invalid csv_type %s or missing required fields" % data['csv_type'])
                else:
                    log.append("Missing csv_type from record")
        except csv.Error, e:
            session.rollback()
            log.append('Error parsing CSV file: %s' % e)

        if log:
            logger.debug('CSV import failed with errors: %r', log)
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
                # XXX remove encoding in Python 3...
                writer.writerow(dict((k, unicode(v).encode('utf8')) for k, v in data.iteritems()))

    @classmethod
    def from_csv(cls, system, data, log):
        """
        Process data file
        """
        if data['csv_type'] in csv_types:
            csv_type = data['csv_type']
            # Remove csv_type now that we know what we want to do.
            data.pop('csv_type')
            csv_types[csv_type]._from_csv(system, data, csv_type, log)
            system.date_modified = datetime.datetime.utcnow()
        else:
            raise ValueError("Invalid csv_type %s" % data['csv_type'])

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into Objects
        """ 
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
                    setattr(csv_object,key,newdata)

    def to_datastruct(self):
        datastruct = dict()
        for csv_key in self.csv_keys:
            val = getattr(self, csv_key, None)
            if val is None:
                val = ''
            datastruct[csv_key] = unicode(val)
        yield datastruct

class CSV_System(CSV):
    csv_type = 'system'
    reg_keys = ['fqdn', 'deleted', 'lender', 'location', 
                'mac_address', 'memory', 'model',
                'serial', 'vendor']

    spec_keys = ['arch', 'lab_controller', 'owner', 
                 'secret', 'status','type','cc']

    csv_keys = reg_keys + spec_keys

    @classmethod
    def query(cls):
        for system in System.permissable_systems(System.query.outerjoin('user')):
            yield CSV_System(system)

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into System Objects
        """
        for key in data.keys():
            if key in cls.reg_keys and key != 'id':
                if data[key]:
                    newdata = smart_bool(data[key])
                else:
                    newdata = None
                current_data = getattr(system, key, None)
                if str(newdata) != str(current_data):
                    setattr(system,key,newdata)
                    activity = SystemActivity(identity.current.user,
                                              'CSV', 'Changed', key, '%s' %
                                              current_data, '%s' % newdata)
                    system.activity.append(activity)
        # import arch
        if 'arch' in data:
            arch_objs = []
            if data['arch']:
                arches = data['arch'].split(',')
                for arch in arches:
                    try:
                        arch_obj = Arch.by_name(arch)
                    except InvalidRequestError:
                        raise ValueError("%s: Invalid arch %s" %
                                         (system.fqdn, arch))
                    arch_objs.append(arch_obj)
            if system.arch != arch_objs:
                activity = SystemActivity(identity.current.user,
                                          'CSV', 'Changed', 'arch', '%s' %
                                          system.arch, '%s' % arch_objs)
                system.activity.append(activity)
                system.arch = arch_objs

        # import cc
        if 'cc' in data:
            cc_objs = []
            if data['cc']:
                cc_objs = data['cc'].split(',')
            if system.cc != cc_objs:
                activity = SystemActivity(identity.current.user,
                                          'CSV', 'Changed', 'cc', '%s' % 
                                          system.cc, '%s' % cc_objs)
                system.activity.append(activity)
                system.cc = cc_objs

        # import labController
        if 'lab_controller' in data:
            if data['lab_controller']:
                try:
                    lab_controller = LabController.by_name(data['lab_controller'])
                except InvalidRequestError:
                    raise ValueError("%s: Invalid lab controller %s" %
                                     (system.fqdn, data['lab_controller']))
            else:
                lab_controller = None
            if system.lab_controller != lab_controller:
                activity = SystemActivity(identity.current.user,
                                          'CSV', 'Changed', 'lab_controller', '%s' %
                                          system.lab_controller, '%s' % lab_controller)
                system.activity.append(activity)
                system.lab_controller = lab_controller

        # import owner
        if 'owner' in data:
            if data['owner']:
                owner = User.by_user_name(data['owner'])
                if not owner:
                    raise ValueError("%s: Invalid User %s" %
                                              (system.fqdn, data['owner']))
            else:
                owner = None
            if system.owner != owner:
                activity = SystemActivity(identity.current.user,
                                          'CSV', 'Changed', 'owner', '%s' %
                                          system.owner, '%s' % owner)
                system.activity.append(activity)
                system.owner = owner
        # import status
        if 'status' in data and data['status']:
            try:
                systemstatus = SystemStatus.from_string(data['status'])
            except ValueError:
                raise ValueError("%s: Invalid Status %s" %
                                 (system.fqdn, data['status']))
            if system.status != systemstatus:
                activity = SystemActivity(identity.current.user, 
                                          'CSV', 'Changed', 'status', '%s' %
                                          system.status, '%s' % systemstatus)
                system.activity.append(activity)
                system.status = systemstatus

        # import type
        if 'type' in data:
            if not data['type']:
                raise ValueError("%s: Invalid Type None" % system.fqdn)
            try:
                systemtype = SystemType.from_string(data['type'])
            except ValueError:
                raise ValueError("%s: Invalid Type %s" %
                                 (system.fqdn, data['type']))
            if system.type != systemtype:
                activity = SystemActivity(identity.current.user,
                                          'CSV', 'Changed', 'type', '%s' %
                                          system.type, '%s' % systemtype)
                system.activity.append(activity)
                system.type = systemtype
        # import secret
        if 'secret' in data:
            if not data['secret']:
                raise ValueError("%s: Invalid secret None" % system.fqdn)
            newdata = smart_bool(data['secret'])
            if system.private != newdata:
                activity = SystemActivity(identity.current.user,
                                          'CSV', 'Changed', 'secret', '%s' %
                                          system.private, '%s' % newdata)
                system.activity.append(activity)
                system.private = newdata

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
        self.status = system.status
        self.type = system.type
        self.vendor = system.vendor
        self.cc = ','.join([cc for cc in system.cc])

class CSV_System_id(CSV_System):

    reg_keys = ['id'] + CSV_System.reg_keys
    csv_keys = reg_keys + CSV_System.spec_keys

    def __init__(self, system):
        self.id = system.id
        super(CSV_System_id, self).__init__(system)

    @classmethod
    def query(cls):
        for system in System.permissable_systems \
            (System.query.outerjoin('user')):
            yield CSV_System_id(system)


class CSV_Power(CSV):
    csv_type = 'power'
    reg_keys = ['fqdn', 'power_address', 'power_user', 'power_passwd', 
                'power_id']
    spec_keys = ['power_type']
    csv_keys = reg_keys + spec_keys

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into Power Objects
        """
        csv_object = getattr(system, csv_type, None)
        if not csv_object:
            csv_object = Power()
            system.power = csv_object
        for key in data.keys():
            if key in cls.reg_keys:
                if data[key]:
                    newdata = smart_bool(data[key])
                else:
                    newdata = None
                current_data = getattr(csv_object, key, None)
                if str(newdata) != str(current_data):
                    activity = SystemActivity(identity.current.user, 'CSV', 'Changed', key, '***', '***')
                    system.activity.append(activity)
                    setattr(csv_object,key,newdata)

        # import power_type
        if 'power_type' in data:
            if not data['power_type']:
                log.append("%s: Invalid power_type None" % system.fqdn)
                return False
            try:
                power_type = PowerType.by_name(data['power_type'])
            except InvalidRequestError:
                log.append("%s: Invalid Power Type %s" % (system.fqdn,
                                                         data['power_type']))
                return False
            if csv_object.power_type != power_type:
                activity = SystemActivity(identity.current.user, 'CSV', 'Changed', 'power_type', '%s' % csv_object.power_type, '%s' % power_type)
                system.activity.append(activity)
                csv_object.power_type = power_type

        return True

    @classmethod
    def query(cls):
        for power in System.permissable_systems(Power.query.outerjoin('system','user')):
            if power.system:
                yield CSV_Power(power)

    def __init__(self, power):
        self.power = power
        self.fqdn = power.system.fqdn
        self.power_address = power.power_address
        self.power_user = power.power_user
        self.power_passwd = power.power_passwd
        self.power_type = power.power_type.name
        self.power_id = power.power_id

class CSV_LabInfo(CSV):
    csv_type = 'labinfo'
    csv_keys = ['fqdn', 'orig_cost', 'curr_cost', 'dimensions', 'weight', 'wattage', 'cooling']

    @classmethod
    def query(cls):
        for labinfo in System.permissable_systems(LabInfo.query.outerjoin('system','user')):
            if labinfo.system:
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

    @classmethod 
    def _from_csv(cls,system,data,csv_type,log):
        new_data = dict()
        for c_type in cls.csv_keys:
            if c_type in data:
                new_data[c_type] = data[c_type]
       
        system.labinfo = LabInfo(**new_data)
        session.add(system)
        session.flush([system])
        

class CSV_Exclude(CSV):
    csv_type = 'exclude'
    csv_keys = ['fqdn', 'arch', 'family', 'update', 'excluded']

    @classmethod
    def query(cls):
        for exclude in System.permissable_systems(ExcludeOSMajor.query.outerjoin('system','user')):
            if exclude.system:
                yield CSV_Exclude(exclude)
        for exclude in System.permissable_systems(ExcludeOSVersion.query.outerjoin('system','user')):
            if exclude.system:
                yield CSV_Exclude(exclude)

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into System Objects
        """
        try:
            arch = Arch.by_name(data['arch'])
        except InvalidRequestError:
            log.append("%s: Invalid Arch %s" % (system.fqdn, data['arch']))
            return False

        if data['update'] and data['family']:
            try:
                osversion = OSVersion.by_name(OSMajor.by_name(str(data['family'])),
                                                            str(data['update']))
            except InvalidRequestError:
                log.append("%s: Invalid Family %s Update %s" % (system.fqdn,
                                                        data['family'],
                                                        data['update']))
                return False
            if osversion not in [oldosversion.osversion for oldosversion in system.excluded_osversion_byarch(arch)]:
                if data['excluded'] == 'True':
                    exclude_osversion = ExcludeOSVersion(osversion=osversion,
                                                         arch=arch)
                    system.excluded_osversion.append(exclude_osversion)
                    activity = SystemActivity(identity.current.user, 'CSV', 'Added', 'Excluded_families', '', '%s/%s' % (osversion, arch))
                    system.activity.append(activity)
            else:
                if data['excluded'] == 'False':
                    for old_osversion in system.excluded_osversion_byarch(arch):
                        if old_osversion.osversion == osversion:
                            activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Excluded_families', '%s/%s' % (old_osversion.osversion, arch),'')
                            system.activity.append(activity)
                            session.delete(old_osversion)
        if not data['update'] and data['family']:
            try:
                osmajor = OSMajor.by_name(data['family'])
            except InvalidRequestError:
                log.append("%s: Invalid family %s " % (system.fqdn,
                                                       data['family']))
                return False
            if osmajor not in [oldosmajor.osmajor for oldosmajor in system.excluded_osmajor_byarch(arch)]:
                if data['excluded'].lower() == 'true':
                    exclude_osmajor = ExcludeOSMajor(osmajor=osmajor, arch=arch)
                    system.excluded_osmajor.append(exclude_osmajor)
                    activity = SystemActivity(identity.current.user, 'CSV', 'Added', 'Excluded_families', '', '%s/%s' % (osmajor, arch))
                    system.activity.append(activity)
            else:
                if data['excluded'].lower() == 'false':
                    for old_osmajor in system.excluded_osmajor_byarch(arch):
                        if old_osmajor.osmajor == osmajor:
                            activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Excluded_families', '%s/%s' % (old_osmajor.osmajor, arch),'')
                            system.activity.append(activity)
                            session.delete(old_osmajor)
        return True

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
        for install in System.permissable_systems(Provision.query.outerjoin('system','user')):
            if install.system:
                yield CSV_Install(install)

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into System Objects
        """
        family = None
        update = None

        # Arch is required
        if 'arch' in data:
            try:
                arch = Arch.by_name(data['arch'])
            except InvalidRequestError:
                log.append("%s: Invalid arch %s" % (system.fqdn, data['arch']))
                return False
        else:
            log.append("%s: Error! Missing arch" % system.fqdn)
            return False

        # pull in update and family if present
        if 'family' in data:
            family = data['family']
            if family:
                try:
                    family = OSMajor.by_name(family)
                except InvalidRequestError:
                    log.append("%s: Error! Invalid family %s" % (system.fqdn,
                                                              data['family']))
                    return False
        if 'update' in data:
            update = data['update']
            if update:
                if not family:
                    log.append("%s: Error! You must specify Family along with Update" % system.fqdn)
                    return False
                try:
                    update = OSVersion.by_name(family, str(update))
                except InvalidRequestError:
                    log.append("%s: Error! Invalid update %s" % (system.fqdn,
                                                             data['update']))
                    return False

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
            installlog = '%s/%s' % (arch,update)
                       
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
            installlog = '%s/%s' % (arch,family)
                       
        #Import Arch specific
        if not family and not update:
            if system.provisions.has_key(arch):
                prov = system.provisions[arch]
            else:
                prov = Provision(arch=arch)
                system.provisions[arch] = prov
            installlog = '%s' % arch

        if 'ks_meta' in data and prov.ks_meta != data['ks_meta']:
            system.activity.append(SystemActivity(identity.current.user,'CSV','Changed', 'InstallOption:ks_meta:%s' % installlog, prov.ks_meta, data['ks_meta']))
            prov.ks_meta = data['ks_meta']
        if 'kernel_options' in data and prov.kernel_options != data['kernel_options']:
            system.activity.append(SystemActivity(identity.current.user,'CSV','Changed', 'InstallOption:kernel_options:%s' % installlog, prov.kernel_options, data['kernel_options']))
            prov.kernel_options = data['kernel_options']
        if 'kernel_options_post' in data and prov.kernel_options_post != data['kernel_options_post']:
            system.activity.append(SystemActivity(identity.current.user,'CSV','Changed', 'InstallOption:kernel_options_post:%s' % installlog, prov.kernel_options_post, data['kernel_options_post']))
            prov.kernel_options_post = data['kernel_options_post']

        return True

    def __init__(self, install):
        self.install = install
        self.fqdn = install.system.fqdn
        self.arch = install.arch

    def to_datastruct(self):
        datastruct = dict(fqdn = self.fqdn,
                          arch = self.arch,
                          family = '',
                          update = '',
                          ks_meta = self.install.ks_meta or '',
                          kernel_options = self.install.kernel_options or '',
                          kernel_options_post = self.install.kernel_options_post or '')
        yield datastruct
        if self.install.provision_families:
            for family in self.install.provision_families.keys():
                prov_family = self.install.provision_families[family]
                datastruct['family'] = family
                datastruct['ks_meta'] = prov_family.ks_meta or ''
                datastruct['kernel_options'] = prov_family.kernel_options or ''
                datastruct['kernel_options_post'] = prov_family.kernel_options_post or ''
                yield datastruct
                if prov_family.provision_family_updates:
                    for update in prov_family.provision_family_updates.keys():
                        prov_update = prov_family.provision_family_updates[update]
                        datastruct['update'] = update.osminor
                        datastruct['ks_meta'] = prov_update.ks_meta or ''
                        datastruct['kernel_options'] = prov_update.kernel_options or ''
                        datastruct['kernel_options_post'] = prov_update.kernel_options_post or ''
                        yield datastruct
                    datastruct['update'] = ''
        
class CSV_KeyValue(CSV):
    csv_type = 'keyvalue'
    csv_keys = ['fqdn', 'key', 'key_value', 'deleted' ]

    @classmethod
    def query(cls):        
        for key_int in System.permissable_systems(Key_Value_Int.query.outerjoin('system','user')):
            if key_int.system:
                yield CSV_KeyValue(key_int)
        for key_string in System.permissable_systems(Key_Value_String.query.outerjoin('system','user')):
            if key_string.system:
                yield CSV_KeyValue(key_string)

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into System Objects
        """
        if 'key' in data and data['key']:
            try:
                key = Key.by_name(data['key'])
            except InvalidRequestError:
                log.append('%s: Invalid Key %s ' % (system.fqdn, data['key']))
                return False
        else:
            log.append('%s: Key must not be blank!' % system.fqdn)
            return False
        if 'key_value' in data and data['key_value']:
            if key.numeric:
                system_key_values = system.key_values_int
                try:
                    key_value = Key_Value_Int.by_key_value(system,
                                                           key,
                                                           data['key_value'])
                except InvalidRequestError:
                    key_value = Key_Value_Int(key=key,
                                              key_value=data['key_value'])
            else:
                system_key_values = system.key_values_string
                try:
                    key_value = Key_Value_String.by_key_value(system,
                                                           key,
                                                           data['key_value'])
                except InvalidRequestError:
                    key_value = Key_Value_String(key=key,
                                                 key_value=data['key_value'])
        else:
            log.append('%s: Key Value must not be blank!' % system.fqdn)
            return False
        deleted = False
        if 'deleted' in data:
            deleted = smart_bool(data['deleted'])
        if deleted:
            if key_value in system_key_values:
                activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'Key/Value', '%s/%s' % (data['key'],data['key_value']), '')
                system.activity.append(activity)
                system_key_values.remove(key_value)
                if not key_value.id:
                    session.expunge(key_value)
        else:
            if key_value not in system_key_values:
                activity = SystemActivity(identity.current.user, 'CSV', 'Added', 'Key/Value', '', '%s/%s' % (data['key'],data['key_value']))
                system.activity.append(activity)
                system_key_values.append(key_value)
        session.add(key_value)
        session.flush([key_value])
        return True

    def __init__(self, key):
        self.fqdn = key.system.fqdn
        self.key = key.key
        self.key_value = key.key_value
        self.deleted = False

class CSV_GroupUser(CSV):
    csv_type = 'user_group'
    csv_keys = ['user', 'group', 'deleted']

    @classmethod
    def query(cls):
        for user in User.query:
            for group in user.groups:
                yield CSV_GroupUser(user, group)

    @classmethod
    def from_csv(cls,user,data,log):
        """
        Import data from CSV file into user.groups
        """
        if 'group' in data and data['group']:
            try:
                group = Group.by_name(data['group'])
            except InvalidRequestError:
                group = Group(group_name=data['group'],
                              display_name=data['group'])
                session.add(group)
                session.flush([group])
            deleted = False
            if 'deleted' in data:
                deleted = smart_bool(data['deleted'])
            if deleted:
                if group in user.groups:
                    activity = Activity(identity.current.user, 'CSV', 'Removed', 'group', '%s' % group, '')
                    user.groups.remove(group)
            else:
                if group not in user.groups:
                    user.groups.append(group)
                    activity = Activity(identity.current.user, 'CSV', 'Added', 'group', '', '%s' % group)
        else:
            log.append("%s: group can't be empty!" % user)
            return False
        return True

    def __init__(self, user, group):
        self.group = group.group_name
        self.user = user.user_name
        self.deleted = False

class CSV_GroupSystem(CSV):
    csv_type = 'system_group'
    csv_keys = ['fqdn', 'group', 'deleted']

    @classmethod
    def query(cls):
        for system in System.permissable_systems(System.query.outerjoin('user')):
            for group in system.groups:
                yield CSV_GroupSystem(system, group)

    @classmethod
    def _from_csv(cls,system,data,csv_type,log):
        """
        Import data from CSV file into system.groups
        """
        if 'group' in data and data['group']:
            try:
                group = Group.by_name(data['group'])
            except InvalidRequestError:
                group = Group(group_name=data['group'],
                              display_name=data['group'])
                session.add(group)
                session.flush([group])
            deleted = False
            if 'deleted' in data:
                deleted = smart_bool(data['deleted'])
            if deleted:
                if group in system.groups:
                    activity = SystemActivity(identity.current.user, 'CSV', 'Removed', 'group', '%s' % group, '')
                    system.activity.append(activity)
                    system.groups.remove(group)
            else:
                if group not in system.groups:
                    system.groups.append(group)
                    activity = SystemActivity(identity.current.user, 'CSV', 'Added', 'group', '', '%s' % group)
                    system.activity.append(activity)
        else:
            log.append("%s: group can't be empty!" % system.fqdn)
            return False
        return True

    def __init__(self, system, group):
        self.group = group.group_name
        self.fqdn = system.fqdn
        self.deleted = False

system_types = ['system', 'labinfo', 'exclude','install','keyvalue',
                'system_group', 'power']
user_types   = ['user_group']
csv_types = dict( system = CSV_System,
                  system_id = CSV_System_id,
                  labinfo = CSV_LabInfo,
                  exclude = CSV_Exclude,
                  install = CSV_Install,
                  keyvalue = CSV_KeyValue,
                  system_group = CSV_GroupSystem,
                  user_group = CSV_GroupUser,
                  power      = CSV_Power)
