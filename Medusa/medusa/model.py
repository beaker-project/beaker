from datetime import datetime
from turbogears.database import metadata, mapper, session

from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relation, backref, synonym
from sqlalchemy import String, Unicode, Integer, DateTime, UnicodeText, Boolean, Float, VARCHAR, TEXT
from sqlalchemy.exceptions import InvalidRequestError

from turbogears import identity

from datetime import timedelta, date, datetime

import md5

system_table = Table('system', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('name', String(255), nullable=False),
    Column('serial', Unicode(1024)),
    Column('date_added', DateTime, 
           default=datetime.utcnow, nullable=False),
    Column('date_modified', DateTime),
    Column('date_lastcheckin', DateTime),
    Column('location', String(255)),
    Column('notes', UnicodeText),
    Column('vendor', Unicode(255)),
    Column('model', Unicode(255)),
    Column('lender', Unicode(255)),
    Column('owner_id', Integer,
           ForeignKey('tg_user.user_id')),
    Column('user_id', Integer,
           ForeignKey('tg_user.user_id')),
    Column('type_id', Integer,
           ForeignKey('system_type.id'), nullable=False),
    Column('status_id', Integer,
           ForeignKey('system_status.id'), nullable=False),
    Column('shared', Boolean, default=False),
    Column('private', Boolean, default=False),
    Column('deleted', Boolean, default=False),
    Column('memory', Integer),
    Column('checksum', String(32))
)

system_device_table = Table('system_device', metadata,
    Column('id', Integer, autoincrement=True, 
           nullable=False, primary_key=True),
    Column('system_id', Integer,
           ForeignKey('system.id'),
           nullable=False),
    Column('device_id', Integer,
           ForeignKey('device.id'),
           nullable=False),
)

system_type_table = Table('system_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('type', Unicode(100), nullable=False),
)

system_status_table = Table('system_status', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('status', Unicode(100), nullable=False),
)

arch_table = Table('arch', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('arch', String(20))
)

cpu_table = Table('cpu', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('vendor',String(255)),
    Column('model',Integer),
    Column('model_name',String(255)),
    Column('family',Integer),
    Column('stepping',Integer),
    Column('speed',Float),
    Column('processors',Integer),
    Column('cores',Integer),
    Column('sockets',Integer),
    Column('hyper',Boolean),
)

cpu_flag_table = Table('cpu_flag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('cpu_id', Integer, ForeignKey('cpu.id')),
    Column('flag', String(10))
)

numa_table = Table('numa', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('nodes',Integer),
)

device_class_table = Table('device_class', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column("device_class", VARCHAR(24)),
    Column("description", TEXT)
)

device_table = Table('device', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('vendor_id',String(255)),
    Column('device_id',String(255)),
    Column('subsys_device_id',String(255)),
    Column('subsys_vendor_id',String(255)),
    Column('bus',String(255)),
    Column('driver',String(255)),
    Column('description',String(255)),
    Column('device_class_id', Integer,
           ForeignKey('device_class.id'), nullable=False),
    Column('date_added', DateTime, 
           default=datetime.utcnow, nullable=False)
)

locked_table = Table('locked', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

power_type_table = Table('power_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('name', Unicode(255), nullable=False),
    Column('command', String(255)),
    Column('p_reset',String(255)),
    Column('p_off',String(255)),
    Column('p_on',String(255)),
    Column('p_status',String(255)),
)

power_type_key_table = Table('power_type_key', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('powertype_id', Integer, ForeignKey('power_type.id'),
           nullable=False),
    Column('key', Unicode(50), nullable=False),
    Column('description', Unicode(1024), nullable=False),
    Column('type', Unicode(25), nullable=False)
)

power_control_table = Table('power_control', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('power_type_id', Integer, ForeignKey('power_type.id'),
           nullable=False),
    Column('name', Unicode(255), nullable=False)
)

controller_value_table = Table('controller_value', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('power_control_id', Integer, 
           ForeignKey('power_control.id'),
           nullable=False),
    Column('key_id', Integer,
           ForeignKey('power_type_key.id'),
           nullable=False),
    Column('value', Unicode(255), nullable=False)
)

power_host_table = Table('power_host', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('power_control_id', Integer, 
           ForeignKey('power_control.id'),
           nullable=False),
)

host_value_table = Table('host_value', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('power_host_id', Integer, 
           ForeignKey('power_host.id'),
           nullable=False),
    Column('key_id', Integer,
           ForeignKey('power_type_key.id'),
           nullable=False),
    Column('value', Unicode(255), nullable=False)
)

serial_table = Table('serial', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

serial_type_table = Table('serial_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

install_table = Table('install', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

distro_table = Table('distro', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('name',Unicode(255)),
    Column('family',Unicode(255)),
    Column('update',Unicode(255)),
    Column('arch',Unicode(25)),
    Column('variant',Unicode(25)),
    Column('date',DateTime),
    Column('discinfo_date',Unicode(25)),
)

distro_method_table = Table('distro_method', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('distro_id', Integer, 
           ForeignKey('distro.id'),
           nullable=False),
    Column('name', String(25)),
    Column('path',Unicode(255)),
)

distro_repo_table = Table('distro_repo', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('distro_id', Integer, 
           ForeignKey('distro.id'),
           nullable=False),
    Column('name', Unicode(255)),
    Column('path',Unicode(255)),
)

distro_tag_table = Table('distro_tag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('distro_id', Integer, 
           ForeignKey('distro.id'),
           nullable=False),
    Column('tag', Unicode(255)),
)

distro_key_value_table = Table('distro_key_value', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('distro_id', Integer, 
           ForeignKey('distro.id'),
           nullable=False),
    Column('key', Unicode(255)),
    Column('value', Unicode(255)),
)

# the identity schema

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('expiry', DateTime)
)

visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True)
)

groups_table = Table('tg_group', metadata,
    Column('group_id', Integer, primary_key=True),
    Column('group_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now)
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(16), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(40)),
    Column('created', DateTime, default=datetime.now)
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255))
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

system_group_table = Table('system_group', metadata,
    Column('system_id', Integer, ForeignKey('system.id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

# the identity model


class Visit(object):
    """
    A visit to your site
    """
    def lookup_visit(cls, visit_key):
        return cls.query.get(visit_key)
    lookup_visit = classmethod(lookup_visit)


class VisitIdentity(object):
    """
    A Visit that is link to a User object
    """
    pass


class Group(object):
    """
    An ultra-simple group definition.
    """
    pass


class User(object):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """
    def permissions(self):
        perms = set()
        for g in self.groups:
            perms |= set(g.permissions)
        return perms
    permissions = property(permissions)

    def by_email_address(cls, email):
        """
        A class method that can be used to search users
        based on their email addresses since it is unique.
        """
        return cls.query.filter_by(email_address=email).first()

    by_email_address = classmethod(by_email_address)

    def by_user_name(cls, username):
        """
        A class method that permits to search users
        based on their user_name attribute.
        """
        return cls.query.filter_by(user_name=username).first()

    by_user_name = classmethod(by_user_name)

    def _set_password(self, password):
        """
        encrypts password on the fly using the encryption
        algo defined in the configuration
        """
        self._password = identity.encrypt_password(password)

    def _get_password(self):
        """
        returns password
        """
        return self._password

    password = property(_get_password, _set_password)


class Permission(object):
    """
    A relationship that determines what each Group can do
    """
    pass

class SystemObject(object):
    def get_tables(cls):
        tables = cls.get_dict().keys()
        tables.sort()
        return tables
    get_tables = classmethod(get_tables)

    def get_dict(cls):
        tables = dict( system = dict(joins=[], cls=cls))
        for property in cls.mapper.iterate_properties:
            mapper = getattr(property, 'mapper', None)
            if mapper:
                remoteTables = {}
                try:
                    remoteTables = property.mapper.class_._get_dict()
                except: pass
                for key in remoteTables.keys():
                    joins = [property.key]
                    joins.extend(remoteTables[key]['joins'])
                    tables['system/%s/%s' % (property.key, key)] = dict(joins=joins, cls=remoteTables[key]['cls'])
                tables['system/%s' % property.key] = dict(joins=[property.key], cls=property.mapper.class_)
        return tables
    get_dict = classmethod(get_dict)

    def _get_dict(cls):
        tables = {}
        for property in cls.mapper.iterate_properties:
            mapper = getattr(property, 'mapper', None)
            if mapper:
                remoteTables = {}
                try:
                    remoteTables = property.mapper.class_._get_dict()
                except: pass
                for key in remoteTables.keys():
                    joins = [property.key]
                    joins.extend(remoteTables[key]['joins'])
                    tables['%s/%s' % (property.key, key)] = dict(joins=joins, cls=remoteTables[key]['cls'])
                tables[property.key] = dict(joins=[property.key], cls=property.mapper.class_)
        return tables
    _get_dict = classmethod(_get_dict)

    def get_fields(cls, lookup=None):
        if lookup:
            dict_lookup = cls.get_dict()
            return dict_lookup[lookup]['cls'].get_fields()
        return cls.mapper.c.keys()
    get_fields = classmethod(get_fields)

class System(SystemObject):

    def __init__(self, name=None):
        self.name = name

    def by_name(cls, name):
        """
        A class method that can be used to search syatems
        based on the name since it is unique.
        """
        print cls
        print name
        return cls.query.filter_by(name=name).one()

    by_name = classmethod(by_name)

    def get_allowed_attr(self):
        attributes = ['vendor','model','memory']
        return attributes

    def get_update_method(self,obj_str):
        methods = dict ( Cpu = self.updateCpu, Arch = self.updateArch, 
                         Devices = self.updateDevices )
        return methods[obj_str]

    def update_powerKeys(self, powerKeys):
        """
        Create any new power keys, and remove any missing ones.
        """
        for powerKey in self.powerKeys:
            if powerKey.id not in powerKeys:
                powerKey.destroySelf()
        for powerKey in powerKeys:
            if powerKey['id'] not in self.powerKeys:
                new_powerKey = PowerKey(system=self.id,
                                           key=int(powerKey['id']),
                                         value=powerKey['value'])
                self.powerKeys.append(new_powerKey)

    def remove_powerKeys(self):
        """ Remove all power keys """
        for powerKey in self.powerKeys:
            powerKey.destroySelf()

    def update(self, inventory):
        """ Update Inventory """

        # Update last checkin even if we don't change anything.
        self.date_lastcheckin = datetime.utcnow()

        md5sum = md5.new("%s" % inventory).hexdigest()
        if self.checksum == md5sum:
            print "No Change"
            return 0
        self.type_id = 1
        self.status_id = 1
        for key in inventory:
            if key in self.get_allowed_attr():
                setattr(self, key, inventory[key])
            else:
                try:
                    method = self.get_update_method(key)
                    method(inventory[key])
                except:
                   raise
        self.date_modified = datetime.utcnow()

    def updateArch(self, archinfo):
        if self.arch:
            for old_arch in self.arch:
                session.delete(old_arch)

        for arch in archinfo:
            new_arch = Arch(arch=arch)
        self.arch.append(new_arch)

    def updateDevices(self, deviceinfo):
        for device in deviceinfo:
            try:
                device = session.query(Device).filter_by(vendor_id = device['vendorID'],
                                   device_id = device['deviceID'],
                                   subsys_vendor_id = device['subsysVendorID'],
                                   subsys_device_id = device['subsysDeviceID'],
                                   bus = device['bus'],
                                   driver = device['driver'],
                                   description = device['description']).one()
                self.devices.append(device)
            except InvalidRequestError:
                new_device = Device(vendor_id       = device['vendorID'],
                                     device_id       = device['deviceID'],
                                     subsys_vendor_id = device['subsysVendorID'],
                                     subsys_device_id = device['subsysDeviceID'],
                                     bus            = device['bus'],
                                     driver         = device['driver'],
                                     device_class   = device['type'],
                                     description    = device['description'])
                session.save(new_device)
                session.flush([new_device])
                self.devices.append(new_device)

    def updateCpu(self, cpuinfo):
        # Remove all old CPU data
        if self.cpu:
            for flag in self.cpu.flags:
                session.delete(flag)
            session.delete(self.cpu)

        # Create new Cpu
        cpu = Cpu(vendor     = cpuinfo['vendor'],
                  model      = cpuinfo['model'],
                  model_name = cpuinfo['modelName'],
                  family     = cpuinfo['family'],
                  stepping   = cpuinfo['stepping'],
                  speed      = cpuinfo['speed'],
                  processors = cpuinfo['processors'],
                  cores      = cpuinfo['cores'],
                  sockets    = cpuinfo['sockets'],
                  flags      = cpuinfo['CpuFlags'])

        self.cpu = cpu

# for property in System.mapper.iterate_properties:
#     print property.mapper.class_.__name__
#     print property.key
#
# systems = session.query(System).join('status').join('type').join(['cpu','flags']).filter(CpuFlag.c.flag=='lm')


class SystemType(SystemObject):
    def __init__(self, type=None):
        self.type = type

    def __repr__(self):
        return self.type

class SystemStatus(SystemObject):
    def __init__(self, status=None):
        self.status = status

    def __repr__(self):
        return self.status

class Arch(SystemObject):
    def __init__(self, arch=None):
        self.arch = arch

    def __repr__(self):
        return self.arch

class Cpu(SystemObject):
    def __init__(self, vendor=None, model=None, model_name=None, family=None, stepping=None,speed=None,processors=None,cores=None,sockets=None,flags=None):
        self.vendor = vendor
        self.model = model
        self.model_name = model_name
        self.family = family
        self.stepping = stepping
        self.speed = speed
        self.processors = processors
        self.cores = cores
        self.sockets = sockets
        if self.processors > self.cores:
            self.hyper = True
        else:
            self.hyper = False
        self.updateFlags(flags)

    def updateFlags(self,flags):
        for cpuflag in flags:
            new_flag = CpuFlag(flag=cpuflag)
            self.flags.append(new_flag)

# systems = session.query(System).join('status').join('type').join(['cpu','flags']).filter(CpuFlag.c.flag=='lm')

class CpuFlag(SystemObject):
    def __init__(self, flag=None):
        self.flag = flag

    def __repr__(self):
        return self.flag

    def by_flag(cls, flag):
        return cls.query.filter_by(flag=flag)

    by_flag = classmethod(by_flag)

class Numa(SystemObject):
    def __init__(self, nodes=None):
        self.nodes = nodes

    def __repr__(self):
        return self.nodes

class DeviceClass(SystemObject):
    def __init__(self, device_class=None, description=None):
        if not device_class:
            device_class = "NONE"
        self.device_class = device_class
        self.description = description

    def __repr__(self):
        return self.device_class

class Device(SystemObject):
    def __init__(self, vendor_id=None, device_id=None, subsys_device_id=None, subsys_vendor_id=None, bus=None, driver=None, device_class=None, description=None):
        if not device_class:
            device_class = "NONE"
        try:
            dc = DeviceClass.query.filter_by(device_class = device_class).one()
        except InvalidRequestError:
            dc = DeviceClass(device_class = device_class)
            session.save(dc)
            session.flush([dc])
        self.vendor_id = vendor_id
        self.device_id = device_id
        self.subsys_vendor_id = subsys_vendor_id
        self.subsys_device_id = subsys_device_id
        self.bus = bus
        self.driver = driver
        self.description = description
        self.device_class = dc

class Locked(object):
    def __init__(self, name=None):
        self.name = name

class PowerType(object):

    def __init__(self, name=None, command=None, p_reset=None, p_off=None, p_on=None, p_status=None):
        self.name = name
        self.command = command
        self.p_reset = p_reset
        self.p_off = p_off
        self.p_on = p_on
        self.p_status = p_ststus

    def update_keys(self, keys):
        """
        Create any new keys, and remove any missing ones.
        """
        for key in self.keys:
            if key.key not in keys:
                key.destroySelf()
        for key in keys:
            if key['key'] not in self.keys:
                new_key = PowerTypeKey(power_type=self.id,
                                           type=key['type'], 
                                           description=key['description'],
                                           key=key['key'])
                self.keys.append(new_key)

class PowerTypeKey(object):
    def __init__(self, key=None, description=None, type=None):
        self.key = key
        self.description = description
        self.type = type

    def ___repr__(self):
        return "%s %s %s" % (self.key, self.description, self.type)

class PowerControl(object):
    def __init__(self, name=None):
        self.name = name

    def update_values(self, values):
        """ Update values for this controllers keys"""
        for value in values:
            if value['id'] not in self.values:
                new_value = ControllerValue(power_control=self.id,
                                          key=int(value['id']),
                                          value=value['value'])
                self.values.append(new_value)

class ControllerValue(object):
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value

class PowerHost(SystemObject):
    def update_values(self, values):
        """ Update values for this hosts keys"""
        for value in values:
            if value['id'] not in self.values:
                new_value = HostValue(power_control_id=self.id,
                                          key_id=int(value['id']),
                                          value=value['value'])
                self.values.append(new_value)

    def get_status(self):
        """ returns the current power status """
        cmd = "%s %s" % (self.power_control_id.power_type_id.command, self.power_control_id.power_type_id.p_status)
        return cmd

class HostValue(object):
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value

class Serial(object):
    def __init__(self, name=None):
        self.name = name

class SerialType(object):
    def __init__(self, name=None):
        self.name = name

class Install(object):
    def __init__(self, name=None):
        self.name = name

class Distro(object):
    def __init__(self, name=None):
        self.name = name

class DistroMethod(object):
    def __init__(self, name=None):
        self.name = name

class DistroRepo(object):
    def __init__(self, name=None):
        self.name = name

class DistroTag(object):
    def __init__(self, name=None):
        self.name = name

class DistroKeyValue(object):
    def __init__(self, name=None):
        self.name = name

# set up mappers between identity tables and classes

SystemType.mapper = mapper(SystemType, system_type_table)
SystemStatus.mapper = mapper(SystemStatus, system_status_table)
System.mapper = mapper(System, system_table,
       properties = {'devices':relation(Device, 
                                        secondary=system_device_table),
                     'type':relation(SystemType, uselist=False),
                     'status':relation(SystemStatus, uselist=False),
                     'arch':relation(Arch),
                     'cpu':relation(Cpu, uselist=False),
                     'numa':relation(Numa, uselist=False),
                     'power':relation(PowerHost, uselist=False),
                     'user':relation(User, uselist=False, viewonly=True,
                          primaryjoin=system_table.c.user_id==users_table.c.user_id,foreign_keys=system_table.c.user_id),
                     'owner':relation(User, uselist=False, viewonly=True,
                          primaryjoin=system_table.c.owner_id==users_table.c.user_id,foreign_keys=system_table.c.owner_id)})
Arch.mapper = mapper(Arch, arch_table)
Cpu.mapper = mapper(Cpu, cpu_table,
       properties = {'flags':relation(CpuFlag)})
CpuFlag.mapper = mapper(CpuFlag, cpu_flag_table)
Numa.mapper = mapper(Numa, numa_table)
Device.mapper = mapper(Device, device_table,
       properties = {'device_class': relation(DeviceClass)})
mapper(DeviceClass, device_class_table)
mapper(Locked, locked_table)
mapper(PowerType, power_type_table, 
        properties = {'keys':relation(PowerTypeKey, 
                                      backref='power_type',
                                      cascade="all, delete, delete-orphan")
    })
mapper(PowerTypeKey, power_type_key_table)
mapper(PowerControl, power_control_table, 
        properties = {'controller_values':relation(ControllerValue,
                                           backref='power_control',
                                           cascade="all, delete, delete-orphan")
    })
mapper(ControllerValue, controller_value_table)
PowerHost.mapper = mapper(PowerHost, power_host_table,
        properties = {'host_values':relation(HostValue,
                                           backref='power_host',
                                           cascade="all, delete, delete-orphan")
    })
mapper(HostValue, host_value_table)
mapper(Serial, serial_table)
mapper(SerialType, serial_type_table)
mapper(Install, install_table)
mapper(Distro, distro_table)
mapper(DistroMethod, distro_method_table)
mapper(DistroRepo, distro_repo_table)
mapper(DistroTag, distro_tag_table)
mapper(DistroKeyValue, distro_key_value_table)

mapper(Visit, visits_table)

mapper(VisitIdentity, visit_identity_table,
        properties=dict(users=relation(User, backref='visit_identity')))

mapper(User, users_table,
        properties=dict(_password=users_table.c.password))

mapper(Group, groups_table,
        properties=dict(users=relation(User,
                secondary=user_group_table, backref='groups')))

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))


#                     Column("comments"), MultipleJoin('Comment')

#    methods       = MultipleJoin("distroMethod")
#    repos         = MultipleJoin("distroRepo")
#    tags          = MultipleJoin("distroTag")
#    keyvalues     = MultipleJoin("distroKeyValue")

## Static list of device_classes -- used by master.kid
global _device_classes
_device_classes = None
def device_classes():
    global _device_classes
    if not _device_classes:
        _device_classes = DeviceClass.query.all()
    for device_class in _device_classes:
        yield device_class

