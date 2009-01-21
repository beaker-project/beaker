from datetime import datetime
from turbogears.database import metadata, mapper, session
from turbogears.config import get
import ldap
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relation, backref, synonym
from sqlalchemy import String, Unicode, Integer, DateTime, UnicodeText, Boolean, Float, VARCHAR, TEXT
from sqlalchemy import or_, and_, not_, select
from sqlalchemy.exceptions import InvalidRequestError
from identity import LdapSqlAlchemyIdentityProvider
from cobbler_utils import consolidate, string_to_hash
from sqlalchemy.orm.collections import attribute_mapped_collection

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

from turbogears import identity

from datetime import timedelta, date, datetime

import md5

system_table = Table('system', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn', String(255), nullable=False),
    Column('serial', Unicode(1024)),
    Column('date_added', DateTime, 
           default=datetime.utcnow, nullable=False),
    Column('date_modified', DateTime),
    Column('date_lastcheckin', DateTime),
    Column('location', String(255)),
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
    Column('checksum', String(32)),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id'))
)

system_device_map = Table('system_device_map', metadata,
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
    Column('arch', String(20), unique=True)
)

system_arch_map = Table('system_arch_map', metadata,
    Column('system_id', Integer,
           ForeignKey('system.id'),
           nullable=False),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           nullable=False),
)

provision_table = Table('provision', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
    Column('arch_id', Integer, ForeignKey('arch.id')),
)

provision_family_table = Table('provision_family', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('provision_id', Integer, ForeignKey('provision.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
)

provision_family_update_table = Table('provision_update_family', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('provision_family_id', Integer, ForeignKey('provision_family.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
)

exclude_osmajor_table = Table('exclude_osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
)

exclude_osversion_table = Table('exclude_osversion', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
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
    Column('name', String(255), nullable=False),
)

power_table = Table('power', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('power_type_id', Integer, ForeignKey('power_type.id'),
           nullable=False),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('power_address', String(255), nullable=False),
    Column('power_user', String(255)),
    Column('power_passwd', String(255)),
    Column('power_id', String(255)),
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

#RHEL4-U8-re20081015.nightly_http-AS-x86_64   	redhat 	x86_64
#RHEL4-U8-re20081015.nightly_http-AS-x86_64   	redhat 	x86_64
#RHEL4-U8-re20081015.nightly_nfs-AS-xen-x86_64 	redhat 	x86_64
#RHEL4-U8-re20081015.nightly_nfs-AS-xen-x86_64 	redhat 	x86_64
#RHEL5.3-Client-20081013.nightly_http-i386 	redhat 	i386
#RHEL5.3-Client-20081013.nightly_http-x86_64 	redhat 	x86_64
#RHEL5.3-Client-20081013.nightly_nfs-i386 	redhat 	i386
#RHEL5.3-Client-20081013.nightly_nfs-x86_64 	redhat 	x86_64

distro_table = Table('distro', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('install_name',Unicode(255), unique=True, nullable=False),
    Column('name',Unicode(255)),
    Column('breed_id', Integer, ForeignKey('breed.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('variant',Unicode(25)),
    Column('method',Unicode(25)),
    Column('virt',Boolean),
    Column('date_created',DateTime),
)

lab_controller_distro_map = Table('distro_lab_controller_map', metadata,
    Column('distro_id', Integer, ForeignKey('distro.id')),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id')),
)

lab_controller_table = Table('lab_controller', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn',Unicode(255), unique=True),
    Column('username',Unicode(255)),
    Column('password',Unicode(255)),
    Column('distros_md5', String(40)),
    Column('systems_md5', String(40)),
)

osmajor_table = Table('osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor', Unicode(255), unique=True),
)

osversion_table = Table('osversion', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    Column('osminor',Unicode(255)),
)

breed_table = Table('breed', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('breed',Unicode(255), unique=True),
)

distro_tag_table = Table('distro_tag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('tag', Unicode(255), unique=True),
)

distro_tag_map = Table('distro_tag_map', metadata,
    Column('distro_id', Integer, ForeignKey('distro.id')),
    Column('distro_tag_id', Integer, ForeignKey('distro_tag.id')),
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

users_systems_table = Table('tg_system', metadata,
    Column('id', Integer, primary_key=True),
    Column('system_name', Unicode(16), unique=True),
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

# activity schema

# TODO This will require some indexes for performance.
activity_table = Table('activity', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('type', String(40), nullable=False),
    Column('field_name', String(40), nullable=False),
    Column('service', String(100), nullable=False),
    Column('action', String(40), nullable=False),
    Column('old_value', String(40)),
    Column('new_value', String(40))
)

system_activity_table = Table('system_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'))
)

group_activity_table = Table('group_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id'))
)

distro_activity_table = Table('distro_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('distro_id', Integer, ForeignKey('distro.id'))
)

# note schema
note_table = Table('note', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), index=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('text',TEXT, nullable=False)
)

#key_value schema
key_value_table = Table('key_value', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), index=True),
    Column('key_name',TEXT, nullable=False),
    Column('key_value',TEXT, nullable=False)
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
    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(group_name=name).one()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(group_id=id).one()

    def __repr__(self):
        return self.display_name

    @classmethod
    def list_by_name(cls, name):
        """
        A class method that can be used to search groups
        based on the group_name
        """
        return cls.query().filter(Group.group_name.like('%s%%' % name))

class UserSystem(object):
    """
    System Logins (RHTS, other schedulers...)
    """

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

    @classmethod
    def by_id(cls, id):
        return UserSystem.query.filter(UserSystem.id == id).one()

class User(object):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """
    uri = get("identity.soldapprovider.uri", "ldaps://localhost")
    basedn  = get("identity.soldapprovider.basedn", "dc=localhost")
    autocreate = get("identity.soldapprovider.autocreate", False)
    # Only needed for devel.  comment out for Prod.
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

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
        filter = "(uid=%s)" % username
        ldapcon = ldap.initialize(cls.uri)
        rc = ldapcon.search(cls.basedn, ldap.SCOPE_SUBTREE, filter)
        objects = ldapcon.result(rc)[1]
        if(len(objects) == 0):
            log.warning("No such LDAP user: %s" % username)
            return False
        elif(len(objects) > 1):
            log.error("Too Many users: %s" % username)
            return False
        user = cls.query.filter_by(user_name=username).first()
        if not user:
            if cls.autocreate:
                user = User()
                user.user_name = username
                user.display_name = objects[0][1]['cn'][0]
		user.email_address = objects[0][1]['mail'][0]
                session.save(user)
                session.flush()
            else:
                return None
        return user

    by_user_name = classmethod(by_user_name)

    def list_by_name(cls, username):
        filter = "(uid=%s*)" % username
        ldapcon = ldap.initialize(cls.uri)
        rc = ldapcon.search(cls.basedn, ldap.SCOPE_SUBTREE, filter)
        objects = ldapcon.result(rc)[1]
        return [object[0].split(',')[0].split('=')[1] for object in objects]
        
    list_by_name = classmethod(list_by_name)

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

    def __repr__(self):
        return self.display_name

    def is_admin(self):
        return u'admin' in [group.group_name for group in self.groups]


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

    def __init__(self, fqdn=None, status=None, contact=None, location=None,
                       model=None, type=None, serial=None, vendor=None,
                       owner=None):
        self.fqdn = fqdn
        self.status_id = status
        self.contact = contact
        self.location = location
        self.model = model
        self.type_id = type
        self.serial = serial
        self.vendor = vendor
        self.owner = owner


    @classmethod
    def all(cls, user=None):
        """
        Not Private or (Private and in Group)
        
        """
        if user:
            if 'admin' in [group.group_name for group in user.groups]:
                private = None
            else:
                private = or_(System.private==False,
                              and_(System.private==True,
                                   or_(User.user_id==user.user_id,
                                       System.owner==user,
                                        System.user==user)))
        else:
            private = System.private==False
        return cls.query.outerjoin(['groups','users']).filter(private)

#                                  or_(User.user_id==user.user_id, 
#                                      system_group_table.c.system_id==None))))

    @classmethod
    def free(cls, user):
        """
        A class method that can be used to search for systems that only
        user can see
        """
        return System.all(user).filter(and_(System.user==None,
                                            or_(System.owner==user,
                                                System.shared==True),
                                            or_(User.user_id==user.user_id,
                                                system_group_table.c.system_id==None))
                                      )

    @classmethod
    def available(cls, user):
        """
        A class method that can be used to search for systems that only
        user can see
        """
        return System.all(user).filter(and_(or_(System.owner==user,
                                                System.shared==True),
                                            or_(User.user_id==user.user_id,
                                                system_group_table.c.system_id==None))
                                      )

    @classmethod
    def mine(cls, user):
        """
        A class method that can be used to search for systems that only
        user can see
        """
        return cls.query.filter(or_(System.user==user,
                                    System.owner==user))

    @classmethod
    def by_fqdn(cls, fqdn, user):
        """
        A class method that can be used to search systems
        based on the fqdn since it is unique.
        """
        return System.all(user).filter(System.fqdn == fqdn).one()

    @classmethod
    def list_by_fqdn(cls, fqdn, user):
        """
        A class method that can be used to search systems
        based on the fqdn since it is unique.
        """
        return System.all(user).filter(System.fqdn.like('%s%%' % fqdn))

    @classmethod
    def by_id(cls, id, user):
        return System.all(user).filter(System.id == id).one()

    def excluded_families(self):
        """
        massage excluded_osmajor for Checkbox values
        """
        major = {}
        version = {}
        for arch in self.arch:
            major[arch.arch] = [osmajor.osmajor.id for osmajor in self.excluded_osmajor_byarch(arch)]
            version[arch.arch] = [osversion.osversion.id for osversion in self.excluded_osversion_byarch(arch)]

        return (major,version)
    excluded_families=property(excluded_families)

    def install_options(self, distro, ks_meta = '', kernel_options = '',
                           kernel_options_post = ''):
        """
        Return install options based on distro selected.
        Inherit options from Arch -> Family -> Update
        """
        results = dict(ks_meta = string_to_hash(ks_meta), 
                       kernel_options = string_to_hash(kernel_options), 
                       kernel_options_post = string_to_hash(kernel_options_post))
        if distro.arch in self.provisions:
            pa = self.provisions[distro.arch]
            node = self.provision_to_dict(pa)
            consolidate(node,results)
            if distro.osversion.osmajor in pa.provision_families:
                pf = pa.provision_families[distro.osversion.osmajor]
                node = self.provision_to_dict(pf)
                consolidate(node,results)
                if distro.osversion in pf.provision_family_updates:
                    pfu = pf.provision_family_updates[distro.osversion]
                    node = self.provision_to_dict(pfu)
                    consolidate(node,results)
        return results

    def provision_to_dict(self, provision):
        ks_meta = string_to_hash(provision.ks_meta)
        kernel_options = string_to_hash(provision.kernel_options)
        kernel_options_post = string_to_hash(provision.kernel_options_post)
        return dict(ks_meta = ks_meta, kernel_options = kernel_options,
                            kernel_options_post = kernel_options_post)

    def can_admin(self, user=None):
        if user:
            if user == self.owner or user.is_admin:
                return True
        return False

    def current_user(self, user=None):
        if user and self.user:
            if self.user == user or user.is_admin:
                return True
        return False
        
    def can_share(self, user=None):
        if user:
            # If its the owner always allow.
            if user == self.owner:
                return True
            if self.shared:
                # If the user is in the Systems groups
                if self.groups:
                    for group in user.groups:
                        if group in self.groups:
                            return True
                else:
                # If the system has no groups
                    return True
        return False
        
    def get_allowed_attr(self):
        attributes = ['vendor','model','memory']
        return attributes

    def get_update_method(self,obj_str):
        methods = dict ( Cpu = self.updateCpu, Arch = self.updateArch, 
                         Devices = self.updateDevices )
        return methods[obj_str]

    def update_legacy(self, inventory):
        """
        Update Key/Value pairs for legacy RHTS
        """
        #Remove any keys that will be added
        for i, mykey in enumerate(self.key_values):
            if mykey.key_name in inventory:
                del self.key_values[i]

        #Add the uploaded keys
        for key in inventory:
            if isinstance(inventory[key], list):
                for value in inventory[key]:
                    self.key_values.append(Key_Value(key,value))
            else:
                self.key_values.append(Key_Value(key,inventory[key]))
                    

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
        self.arch = []
        for arch in archinfo:
            try:
                new_arch = Arch.by_name(arch)
            except:
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

    def excluded_osmajor_byarch(self, arch):
        """
        List excluded osmajor for system by arch
        """
        excluded = session.query(ExcludeOSMajor).join('systems').\
                    join('arch').filter(and_(System.id==self.id,
                                             Arch.id==arch.id))
        return excluded

    def excluded_osversion_byarch(self, arch):
        """
        List excluded osversion for system by arch
        """
        excluded = session.query(ExcludeOSVersion).join('systems').\
                    join('arch').filter(and_(System.id==self.id,
                                             Arch.id==arch.id))
        return excluded

    def distros(self):
        """
        List of distros that support this system
        """
        distros = session.query(Distro).join(['arch','systems']).filter(
              and_(System.id==self.id,
                not_(or_(Distro.id.in_(select([distro_table.c.id]).
                  where(distro_table.c.arch_id==arch_table.c.id).
                  where(arch_table.c.id==exclude_osmajor_table.c.arch_id).
                  where(distro_table.c.osversion_id==osversion_table.c.id).
                  where(osversion_table.c.osmajor_id==osmajor_table.c.id).
                  where(osmajor_table.c.id==exclude_osmajor_table.c.osmajor_id).
                  where(exclude_osmajor_table.c.system_id==system_table.c.id)
                                      ),
                         Distro.id.in_(select([distro_table.c.id]).
                  where(distro_table.c.arch_id==arch_table.c.id).
                  where(arch_table.c.id==exclude_osversion_table.c.arch_id).
                  where(distro_table.c.osversion_id==osversion_table.c.id).
                  where(osversion_table.c.id==
                                        exclude_osversion_table.c.osversion_id).
                  where(exclude_osversion_table.c.system_id==system_table.c.id)
                                      )
                        )
                    )
                  )
        )
        return distros

    def action_auto_provision(self, distro=None,
                             ks_meta=None,
                             kernel_options=None,
                             kernel_options_post=None):
        print "ks_meta=",ks_meta
        results = self.install_options(distro, ks_meta,
                                               kernel_options,
                                               kernel_options_post)
        rc, result = self.action_provision(distro, **results)
        if rc == 0:
            rc, result = self.action_power(action="reboot")
        return rc, result

    def action_provision(self, distro=None, 
                        ks_meta=None,
                        kernel_options=None,
                        kernel_options_post=None,
                        kickstart=None):
        """
        Provision the System
        make xmlrpc call to lab controller
        """
        if not distro:
            return False
        if not self.lab_controller:
            return False
        print "ksmeta=",ks_meta
        data = dict(systemname          = self.fqdn,
                    profilename         = distro.install_name,
                    ksmeta              = ks_meta,
                    kernel_options      = kernel_options,
                    kernel_options_post = kernel_options_post)

        if kickstart:
            data['kickstart'] = kickstart
        labcontroller = self.lab_controller
        url = "http://%s/labcontroller/" % labcontroller.fqdn
        lc_xmlrpc = xmlrpclib.ServerProxy(url, BasicAuthTransport(labcontroller.username, labcontroller.password), allow_none=True)
        return lc_xmlrpc.provision(data)

    def action_power(self, action="reboot"):
        """
        Power cycle the system
        """
        if not self.power:
            return False
        if not self.lab_controller:
            return False

        data = dict( systemname    = self.fqdn,
                     power_type    = self.power.power_type.name,
                     power_address = self.power.power_address)
        if self.power.power_user:
            data['power_user'] = self.power.power_user
        if self.power.power_passwd:
            data['power_passwd'] = self.power.power_passwd
        if self.power.power_id:
            data['power_id'] = self.power.power_id

        labcontroller = self.lab_controller
        url = "http://%s/labcontroller/" % labcontroller.fqdn
        lc_xmlrpc = xmlrpclib.ServerProxy(url, BasicAuthTransport(labcontroller.username, labcontroller.password))
        return lc_xmlrpc.power(action, data)

    def __repr__(self):
        return self.fqdn

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

    @classmethod
    def get_all_types(cls):
        """
        Desktop, Server, Virtual
        """
        all_types = cls.query()
        return [(type.id, type.type) for type in all_types]

class SystemStatus(SystemObject):
    def __init__(self, status=None):
        self.status = status

    def __repr__(self):
        return self.status

    @classmethod
    def get_all_status(cls):
        """
        Available, InUse, Offline
        """
        all_status = cls.query()
        return [(status.id, status.status) for status in all_status]

class Arch(SystemObject):
    def __init__(self, arch=None):
        self.arch = arch

    def __repr__(self):
        return '%s' % self.arch

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, arch):
        return cls.query.filter_by(arch=arch).one()

    @classmethod
    def list_by_name(cls, name):
        """
        A class method that can be used to search arches
        based on the name
        """
        return cls.query().filter(Arch.arch.like('%s%%' % name))

class Provision(SystemObject):
    pass

class ProvisionFamily(SystemObject):
    pass

class ProvisionFamilyUpdate(SystemObject):
    pass

class ExcludeOSMajor(SystemObject):
    pass

class ExcludeOSVersion(SystemObject):
    pass

class Breed(SystemObject):
    def __init__(self, breed):
        self.breed = breed

    @classmethod
    def by_name(cls, breed):
        return cls.query.filter_by(breed=breed).one()

    def __repr__(self):
        return self.breed

class OSMajor(SystemObject):
    def __init__(self, osmajor):
        self.osmajor = osmajor

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, osmajor):
        return cls.query.filter_by(osmajor=osmajor).one()

    @classmethod
    def get_all(cls):
        all = cls.query()
        return [(0,"All")] + [(major.id, major.osmajor) for major in all]

    def __repr__(self):
        return '%s' % self.osmajor

class OSVersion(SystemObject):
    def __init__(self, osmajor, osminor):
        self.osmajor = osmajor
        self.osminor = osminor

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, osmajor, osminor):
        return cls.query.filter_by(osmajor=osmajor, osminor=osminor).one()

    @classmethod
    def get_all(cls):
        all = cls.query()
        return [(0,"All")] + [(version.id, version.osminor) for version in all]

    def __repr__(self):
        return "%s.%s" % (self.osmajor,self.osminor)

class LabController(SystemObject):
    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def get_all(cls):
        """
        Desktop, Server, Virtual
        """
        all = cls.query()
        return [(0,"None")] + [(lc.id, lc.fqdn) for lc in all]
        

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

    def __init__(self, name=None):
        self.name = name

    @classmethod
    def get_all(cls):
        """
        Apc, wti, etc..
        """
        all_types = cls.query()
        return [(0, "None")] + [(type.id, type.name) for type in all_types]

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

class Power(SystemObject):
    pass

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
    def __init__(self, install_name=None):
        self.install_name = install_name

    @classmethod
    def by_install_name(cls, install_name):
        return cls.query.filter_by(install_name=install_name).one()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_filter(cls, filter):
        """
        <distro>
         <And>
           <Require name='ARCH' operator='=' value='i386'/>
           <Require name='FAMILY' operator='=' value='rhelserver5'/>
           <Require name='TAG' operator='=' value='released'/>
         </And>
        </distro>
        """
        pass

    def systems_filter(self, user, filter):
        """
        Return Systems that match the following filter
        <host>
         <And>
           <Require name='MACHINE' operator='!=' value='dell-pe700-01.rhts.bos.redhat.com'/>
           <Require name='ARCH' operator='=' value='i386'/>
           <Require name='MEMORY' operator='>=' value='2048'/>
           <Require name='POWER' operator='=' value='True'/>
         </And>
        </host>
        System.query.\
           join('key_values',aliased=True).\ 
                filter_by(key_name='MEMORY').\
                filter(key_value_table.c.key_value > 2048).\
           join('key_values',aliased=True).\
                filter_by(key_name='CPUFLAGS').\
                filter(key_value_table.c.key_value == 'lm').\
              all()
        [hp-xw8600-02.rhts.bos.redhat.com]
        """
        pass

    def systems(self, user=None):
        """
        List of systems that support this distro
        Limit to what is available to user if user passed in.
        """
        if user:
            systems = System.available(user)
        else:
            systems = session.query(System)

        return systems.filter(
             and_(System.arch.contains(self.arch),
                not_(or_(System.id.in_(select([system_table.c.id]).
                  where(system_table.c.id==system_arch_map.c.system_id).
                  where(arch_table.c.id==system_arch_map.c.arch_id).
                  where(system_table.c.id==exclude_osmajor_table.c.system_id).
                  where(arch_table.c.id==exclude_osmajor_table.c.arch_id).
                  where(ExcludeOSMajor.osmajor==self.osversion.osmajor)
                                      ),
                         System.id.in_(select([system_table.c.id]).
                  where(system_table.c.id==system_arch_map.c.system_id).
                  where(arch_table.c.id==system_arch_map.c.arch_id).
                  where(system_table.c.id==exclude_osversion_table.c.system_id).
                  where(arch_table.c.id==exclude_osversion_table.c.arch_id).
                  where(ExcludeOSVersion.osversion==self.osversion)
                                      )
                        )
                    )
                 )
        )

    def ___repr__(self):
        return "%s" % self.install_name

class DistroTag(object):
    def __init__(self, name=None):
        self.name = name

# Activity model
class Activity(object):
    def __init__(self, user=None, service=None, action=None,
                 field_name=None, old_value=None, new_value=None):
        self.user = user
        self.service = service
        self.field_name = field_name
        self.action = action
        self.old_value = old_value
        self.new_value = new_value

    @classmethod
    def all(cls):
        return cls.query()

    def object_name(self):
        return None

class SystemActivity(Activity):
    def object_name(self):
        return "System: %s" % self.object.fqdn

class GroupActivity(Activity):
    def object_name(self):
        return "Group: %s" % self.object.display_name

class DistroActivity(Activity):
    def object_name(self):
        return "Distro: %s" % self.object.install_name

# note model
class Note(object):
    def __init__(self, user=None, text=None):
        self.user = user
        self.text = text

    @classmethod
    def all(cls):
        return cls.query()

# key_value model
class Key_Value(object):
    def __init__(self, key_name=None, key_value=None):
        self.key_name = key_name
        self.key_value = key_value

    def ___repr__(self):
        return "%s %s" % (self.key_name, self.key_value)

    @classmethod
    def all(cls):
        return cls.query()


# set up mappers between identity tables and classes

SystemType.mapper = mapper(SystemType, system_type_table)
SystemStatus.mapper = mapper(SystemStatus, system_status_table)
System.mapper = mapper(System, system_table,
       properties = {'devices':relation(Device,
                                        secondary=system_device_map),
                     'type':relation(SystemType, uselist=False),
                     'status':relation(SystemStatus, uselist=False),
                     'arch':relation(Arch,
                                        secondary=system_arch_map,
                                        backref='systems'),
                     'cpu':relation(Cpu, uselist=False),
                     'numa':relation(Numa, uselist=False),
                     'power':relation(Power, uselist=False),
                     'excluded_osmajor':relation(ExcludeOSMajor,
                                                 backref='systems'),
                     'excluded_osversion':relation(ExcludeOSVersion,
                                                 backref='systems'),
                     'provisions':relation(Provision, collection_class=attribute_mapped_collection('arch')),
                     'user':relation(User, uselist=False,
                          primaryjoin=system_table.c.user_id==users_table.c.user_id,foreign_keys=system_table.c.user_id),
                     'owner':relation(User, uselist=False,
                          primaryjoin=system_table.c.owner_id==users_table.c.user_id,foreign_keys=system_table.c.owner_id),
                     'lab_controller':relation(LabController, uselist=False,
                                               backref='systems'),
                     'notes':relation(Note,
                                      order_by=[note_table.c.created.desc()],
                                      cascade="all, delete, delete-orphan"),
                     'key_values':relation(Key_Value,
                                      cascade="all, delete, delete-orphan"),
                     'activity':relation(SystemActivity,
                                     order_by=[activity_table.c.created.desc()],
                                               backref='object')})
mapper(Arch, arch_table)
mapper(Provision, provision_table,
       properties = {'provision_families':relation(ProvisionFamily, collection_class=attribute_mapped_collection('osmajor')),
                     'arch':relation(Arch)})
mapper(ProvisionFamily, provision_family_table,
       properties = {'provision_family_updates':relation(ProvisionFamilyUpdate, collection_class=attribute_mapped_collection('osversion')),
                     'osmajor':relation(OSMajor)})
mapper(ProvisionFamilyUpdate, provision_family_update_table,
       properties = {'osversion':relation(OSVersion)})
mapper(ExcludeOSMajor, exclude_osmajor_table,
       properties = {'osmajor':relation(OSMajor, backref='excluded_osmajors'),
                     'arch':relation(Arch)})
mapper(ExcludeOSVersion, exclude_osversion_table,
       properties = {'osversion':relation(OSVersion),
                     'arch':relation(Arch)})
mapper(OSVersion, osversion_table,
       properties = {'osmajor':relation(OSMajor, uselist=False,
                                        backref='osversion')})
mapper(OSMajor, osmajor_table,
       properties = {'osminor':relation(OSVersion,
                                     order_by=[osversion_table.c.osminor])})
Cpu.mapper = mapper(Cpu, cpu_table,
       properties = {'flags':relation(CpuFlag)})
CpuFlag.mapper = mapper(CpuFlag, cpu_flag_table)
Numa.mapper = mapper(Numa, numa_table)
Device.mapper = mapper(Device, device_table,
       properties = {'device_class': relation(DeviceClass)})
mapper(DeviceClass, device_class_table)
mapper(Locked, locked_table)
mapper(PowerType, power_type_table)
mapper(Power, power_table,
        properties = {'power_type':relation(PowerType,
                                           backref='power_control')
    })
mapper(Serial, serial_table)
mapper(SerialType, serial_type_table)
mapper(Install, install_table)
mapper(LabController, lab_controller_table,
        properties = {'distros':relation(Distro,
                                          secondary=lab_controller_distro_map,
                                          backref='lab_controllers',
                                          cascade="all,delete-orphan"),
    })
mapper(Distro, distro_table,
        properties = {'osversion':relation(OSVersion, uselist=False,
                                           backref='distros'),
                      'breed':relation(Breed, backref='distros'),
                      'arch':relation(Arch, backref='distros'),
                      'tags':relation(DistroTag,
                                       secondary=distro_tag_map,
                                       backref='distros'),
    })
mapper(Breed, breed_table)
mapper(DistroTag, distro_tag_table)

mapper(UserSystem, users_systems_table,
    properties=dict(_password=users_systems_table.c.password))

mapper(Visit, visits_table)

mapper(VisitIdentity, visit_identity_table,
        properties=dict(users=relation(User, backref='visit_identity')))

mapper(User, users_table,
        properties=dict(_password=users_table.c.password))

mapper(Group, groups_table,
        properties=dict(users=relation(User,
                secondary=user_group_table, backref='groups'),
                        systems=relation(System,
                secondary=system_group_table, backref='groups')))

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))

mapper(Activity, activity_table,
        polymorphic_on=activity_table.c.type, polymorphic_identity='activity',
        properties=dict(user=relation(User, uselist=False,
                        backref='activity')))

mapper(SystemActivity, system_activity_table, inherits=Activity,
        polymorphic_identity='system_activity')

mapper(GroupActivity, group_activity_table, inherits=Activity,
        polymorphic_identity='group_activity',
        properties=dict(object=relation(Group, uselist=False,
                         backref='activity')))

mapper(DistroActivity, distro_activity_table, inherits=Activity,
       polymorphic_identity='distro_activity',
       properties=dict(object=relation(Distro, uselist=False,
                         backref='activity')))

mapper(Note, note_table,
        properties=dict(user=relation(User, uselist=False,
                        backref='notes')))

mapper(Key_Value, key_value_table)


#                     Column("comments"), MultipleJoin('Comment')

#    tags          = MultipleJoin("distroTag")

## Static list of device_classes -- used by master.kid
global _device_classes
_device_classes = None
def device_classes():
    global _device_classes
    if not _device_classes:
        _device_classes = DeviceClass.query.all()
    for device_class in _device_classes:
        yield device_class

