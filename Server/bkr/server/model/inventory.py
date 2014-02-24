
import sys
import logging
from datetime import datetime, timedelta
from hashlib import md5
import urllib
import xml.dom.minidom
import lxml.etree
from kid import XML
from markdown import markdown
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Index,
        Integer, Unicode, UnicodeText, DateTime, String, Boolean, Numeric, Float,
        BigInteger, VARCHAR, TEXT)
from sqlalchemy.sql import select, and_, or_, not_, case, func
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import (mapper, relationship, backref,
        column_property, dynamic_loader, contains_eager, validates)
from sqlalchemy.orm.interfaces import AttributeExtension
from sqlalchemy.orm.attributes import NEVER_SET
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears import url
from turbogears.config import get
from turbogears.database import session
from bkr.server import identity, metrics, mail
from bkr.server.bexceptions import (BX, InsufficientSystemPermissions,
        StaleCommandStatusException, StaleSystemUserException)
from bkr.server.helpers import make_link
from bkr.server.hybrid import hybrid_property, hybrid_method
from bkr.server.installopts import InstallOptions, global_install_options
from bkr.server.util import is_valid_fqdn
from .base import DeclarativeMappedObject
from .types import (SystemType, SystemStatus, ReleaseAction, CommandStatus,
        SystemPermission, TaskStatus)
from .activity import Activity, ActivityMixin
from .identity import User, Group, SystemGroup
from .lab import LabController
from .distrolibrary import (Arch, KernelType, OSMajor, OSVersion, Distro, DistroTree,
        LabControllerDistroTree)

log = logging.getLogger(__name__)

xmldoc = xml.dom.minidom.Document()

class SystemActivity(Activity):

    __tablename__ = 'system_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id'))
    __mapper_args__ = {'polymorphic_identity': u'system_activity'}

    def object_name(self):
        return "System: %s" % self.object.fqdn

class CallbackAttributeExtension(AttributeExtension):
    def set(self, state, value, oldvalue, initiator):
        instance = state.obj()
        if instance.callback:
            try:
                modname, _dot, funcname = instance.callback.rpartition(".")
                module = import_module(modname)
                cb = getattr(module, funcname)
                cb(instance, value)
            except Exception, e:
                log.error("command callback failed: %s" % e)
        return value

class CommandActivity(Activity):

    __tablename__ = 'command_queue'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    system = relationship('System')
    status = column_property(
            Column('status', CommandStatus.db_type(), nullable=False, index=True),
            extension=CallbackAttributeExtension())
    task_id = Column(String(255))
    delay_until = Column(DateTime, default=None)
    quiescent_period = Column(Integer, default=None)
    updated = Column(DateTime, default=datetime.utcnow)
    callback = Column(String(255))
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'))
    distro_tree = relationship(DistroTree)
    kernel_options = Column(UnicodeText)
    __mapper_args__ = {'polymorphic_identity': u'command_activity'}

    def __init__(self, user, service, action, status, callback=None, quiescent_period=0):
        Activity.__init__(self, user, service, action, u'Command', u'', u'')
        self.status = status
        self.callback = callback
        self.quiescent_period = quiescent_period

    def object_name(self):
        return "Command: %s %s" % (self.object.fqdn, self.action)

    def change_status(self, new_status):
        current_status = self.status
        if session.connection(CommandActivity).execute(CommandActivity.__table__.update(
                and_(CommandActivity.__table__.c.id == self.id,
                     CommandActivity.status == current_status)),
                status=new_status).rowcount != 1:
            raise StaleCommandStatusException(
                    'Status for command %s updated in another transaction'
                    % self.id)
        self.status = new_status

    def log_to_system_history(self):
        sa = SystemActivity(self.user, self.service, self.action, u'Power', u'',
                            self.new_value and u'%s: %s' % (self.status, self.new_value) \
                            or u'%s' % self.status)
        self.system.activity.append(sa)

    def abort(self, msg=None):
        log.error('Command %s aborted: %s', self.id, msg)
        self.status = CommandStatus.aborted
        self.new_value = msg
        self.log_to_system_history()

class Reservation(DeclarativeMappedObject):

    __tablename__ = 'reservation'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'), nullable=False)
    start_time = Column(DateTime, index=True, nullable=False,
            default=datetime.utcnow)
    finish_time = Column(DateTime, index=True)
    # type = 'manual' or 'recipe'
    # XXX Use Enum types
    type = Column(Unicode(30), index=True, nullable=False)
    user = relationship(User, backref=backref('reservations',
            order_by=[start_time.desc()]))

# this only really exists to make reporting efficient
class SystemStatusDuration(DeclarativeMappedObject):

    __tablename__ = 'system_status_duration'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id'), nullable=False)
    status = Column(SystemStatus.db_type(), nullable=False)
    start_time = Column(DateTime, index=True, nullable=False,
            default=datetime.utcnow)
    finish_time = Column(DateTime, index=True)

system_device_map = Table('system_device_map', DeclarativeMappedObject.metadata,
    Column('system_id', Integer,
           ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True),
    Column('device_id', Integer,
           ForeignKey('device.id'),
           primary_key=True),
    mysql_engine='InnoDB',
)

system_arch_map = Table('system_arch_map', DeclarativeMappedObject.metadata,
    Column('system_id', Integer,
           ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True),
    mysql_engine='InnoDB',
)


class SystemStatusAttributeExtension(AttributeExtension):
    def set(self, state, child, oldchild, initiator):
        obj = state.obj()
        log.debug('%r status changed from %r to %r', obj, oldchild, child)
        if child == oldchild:
            return child
        if oldchild in (None, NEVER_SET):
            # First time system.status has been set, there will be no duration 
            # rows yet.
            assert not obj.status_durations
            obj.status_durations.insert(0, SystemStatusDuration(status=child))
            return child
        # Otherwise, there should be exactly one "open" duration row, 
        # with NULL finish_time.
        open_sd = obj.status_durations[0]
        assert open_sd.finish_time is None
        assert open_sd.status == oldchild
        if open_sd in session.new:
            # The current open row is not actually persisted yet. This 
            # happens when system.status is set more than once in 
            # a session. In this case we can just update the same row and 
            # return, no reason to insert another.
            open_sd.status = child
            return child
        # Need to close the open row using a conditional UPDATE to ensure 
        # we don't race with another transaction
        now = datetime.utcnow()
        if session.query(SystemStatusDuration)\
                .filter_by(finish_time=None, id=open_sd.id)\
                .update({'finish_time': now}, synchronize_session=False) \
                != 1:
            raise RuntimeError('System status updated in another transaction')
        # Make the ORM aware of it as well
        open_sd.finish_time = now
        obj.status_durations.insert(0, SystemStatusDuration(status=child))
        return child

class System(DeclarativeMappedObject, ActivityMixin):

    __tablename__ = 'system'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    fqdn = Column(Unicode(255), nullable=False)
    serial = Column(Unicode(1024))
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime)
    date_lastcheckin = Column(DateTime)
    location = Column(String(255))
    vendor = Column(Unicode(255))
    model = Column(Unicode(255))
    lender = Column(Unicode(255))
    owner_id = Column(Integer, ForeignKey('tg_user.user_id'), nullable=False)
    owner = relationship(User, primaryjoin=owner_id == User.user_id)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'))
    user = relationship(User, primaryjoin=user_id == User.user_id)
    type = Column(SystemType.db_type(), nullable=False)
    status = column_property(Column(SystemStatus.db_type(), nullable=False),
            extension=SystemStatusAttributeExtension())
    status_reason = Column(Unicode(255))
    deleted = Column(Boolean, default=False)
    memory = Column(Integer)
    checksum = Column(String(32))
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id'))
    lab_controller = relationship(LabController, backref='systems')
    mac_address = Column(String(18))
    loan_id = Column(Integer, ForeignKey('tg_user.user_id'))
    loaned = relationship(User, primaryjoin=loan_id == User.user_id)
    loan_comment = Column(Unicode(1000))
    release_action = Column(ReleaseAction.db_type())
    reprovision_distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'))
    reprovision_distro_tree = relationship(DistroTree)
    hypervisor_id = Column(Integer, ForeignKey('hypervisor.id'))
    hypervisor = relationship('Hypervisor')
    kernel_type_id = Column(Integer, ForeignKey('kernel_type.id'),
           default=select([KernelType.id], limit=1).where(KernelType.kernel_type==u'default').correlate(None),
           nullable=False)
    kernel_type = relationship('KernelType')
    devices = relationship('Device', secondary=system_device_map, backref='systems')
    disks = relationship('Disk', backref='system', cascade='all, delete, delete-orphan')
    arch = relationship(Arch, order_by=[Arch.arch], secondary=system_arch_map,
            backref='systems')
    labinfo = relationship('LabInfo', uselist=False, backref='system',
            cascade='all, delete, delete-orphan')
    cpu = relationship('Cpu', uselist=False, backref='system',
            cascade='all, delete, delete-orphan')
    numa = relationship('Numa', uselist=False, backref='system',
            cascade='all, delete, delete-orphan')
    power = relationship('Power', uselist=False, backref='system',
            cascade='all, delete, delete-orphan')
    excluded_osmajor = relationship('ExcludeOSMajor', backref='system',
            cascade='all, delete, delete-orphan')
    excluded_osversion = relationship('ExcludeOSVersion', backref='system',
            cascade='all, delete, delete-orphan')
    provisions = relationship('Provision', backref='system',
            cascade='all, delete, delete-orphan',
            collection_class=attribute_mapped_collection('arch'))
    group_assocs = relationship(SystemGroup, backref='system',
            cascade='all, delete-orphan')
    key_values_int = relationship('Key_Value_Int', backref='system',
            cascade='all, delete, delete-orphan')
    key_values_string = relationship('Key_Value_String', backref='system',
            cascade='all, delete, delete-orphan')
    activity = relationship(SystemActivity, backref='object', cascade='all, delete',
            order_by=[SystemActivity.created.desc(), SystemActivity.id.desc()])
    dyn_activity = dynamic_loader(SystemActivity,
            order_by=[SystemActivity.created.desc(), SystemActivity.id.desc()])
    command_queue = relationship(CommandActivity, backref='object',
            cascade='all, delete, delete-orphan',
            order_by=[CommandActivity.created.desc(), CommandActivity.id.desc()])
    dyn_command_queue = dynamic_loader(CommandActivity)
    _system_ccs = relationship('SystemCc', backref='system',
            cascade='all, delete, delete-orphan')
    reservations = relationship(Reservation, backref='system',
            order_by=[Reservation.start_time.desc()])
    dyn_reservations = dynamic_loader(Reservation)
    open_reservation = relationship(Reservation, uselist=False, viewonly=True,
            primaryjoin=and_(id == Reservation.system_id, Reservation.finish_time == None))
    status_durations = relationship(SystemStatusDuration, backref='system',
            cascade='all, delete, delete-orphan',
            order_by=[SystemStatusDuration.start_time.desc(),
                      SystemStatusDuration.id.desc()])
    dyn_status_durations = dynamic_loader(SystemStatusDuration)

    activity_type = SystemActivity

    def __init__(self, fqdn=None, status=SystemStatus.broken, contact=None, location=None,
                       model=None, type=SystemType.machine, serial=None, vendor=None,
                       owner=None, lab_controller=None, lender=None,
                       hypervisor=None, loaned=None, memory=None,
                       kernel_type=None, cpu=None):

        # Ensure the fqdn is valid
        self.fqdn = fqdn

        super(System, self).__init__()
        self.status = status
        self.contact = contact
        self.location = location
        self.model = model
        self.type = type
        self.serial = serial
        self.vendor = vendor
        self.owner = owner
        self.lab_controller = lab_controller
        self.lender = lender
        self.hypervisor = hypervisor
        self.loaned = loaned
        self.memory = memory
        self.kernel_type = kernel_type
        self.cpu = cpu

    @validates('fqdn')
    def validate_fqdn(self, key, fqdn):
        if not fqdn:
            raise ValueError('System must have an associated FQDN')
        if not is_valid_fqdn(fqdn):
            raise ValueError('System has an invalid FQDN: %s' % fqdn)

        return fqdn

    def to_xml(self, clone=False):
        """ Return xml describing this system """
        fields = dict(
                      hostname    = 'fqdn',
                      system_type = 'type',
                     )

        host_requires = xmldoc.createElement('hostRequires')
        xmland = xmldoc.createElement('and')
        for key in fields.keys():
            require = xmldoc.createElement(key)
            require.setAttribute('op', '=')
            value = getattr(self, fields[key], None) or u''
            require.setAttribute('value', unicode(value))
            xmland.appendChild(require)
        host_requires.appendChild(xmland)
        return host_requires

    @classmethod
    def all(cls, user=None, system=None):
        """
        Only systems that the current user has permission to see

        """
        if system is None:
            system = cls.query
        return cls.permissable_systems(query=system, user=user)

    @classmethod
    def permissable_systems(cls, query, user=None, *arg, **kw):

        if user is None:
            try:
                user = identity.current.user
            except AttributeError:
                user = None

        if user:
            if not user.is_admin() and \
               not user.has_permission(u'secret_visible'):
                query = query.outerjoin(System.custom_access_policy).filter(
                            or_(SystemAccessPolicy.grants(user, SystemPermission.view),
                                System.owner == user,
                                System.loaned == user,
                                System.user == user))
        else:
            query = query.outerjoin(System.custom_access_policy).filter(
                    SystemAccessPolicy.grants_everybody(SystemPermission.view))

        return query


    @classmethod
    def free(cls, user, systems=None):
        """
        Builds on available.  Only systems with no users, and not Loaned.
        """
        return System.available(user,systems).\
            filter(and_(System.user==None, or_(System.loaned==None, System.loaned==user))). \
            join(System.lab_controller).filter(LabController.disabled==False)

    @classmethod
    def available_for_schedule(cls, user, systems=None):
        """
        Will return systems that are available to user for scheduling
        """
        return cls._available(user, systems=systems, system_status=SystemStatus.automated)

    @classmethod
    def _available(self, user, system_status=None, systems=None):
        """
        Builds on all.  Only systems which this user has permission to reserve.
        Can take varying system_status' as args as well
        """

        query = System.all(user, system=systems)
        if system_status is None:
            query = query.filter(or_(System.status==SystemStatus.automated,
                    System.status==SystemStatus.manual))
        elif isinstance(system_status, list):
            query = query.filter(or_(*[System.status==k for k in system_status]))
        else:
            query = query.filter(System.status==system_status)

        # these filter conditions correspond to can_reserve
        query = query.outerjoin(System.custom_access_policy).filter(or_(
                System.owner == user,
                System.loaned == user,
                SystemAccessPolicy.grants(user, SystemPermission.reserve)))
        return query


    @classmethod
    def available(cls, user, systems=None):
        """
        Will return systems that are available to user
        """
        return cls._available(user, systems=systems)

    @classmethod
    def scheduler_ordering(cls, user, query):
        # Order by:
        #   System Owner
        #   System group
        #   Single procesor bare metal system
        return query.outerjoin(System.cpu).order_by(
            case([(System.owner==user, 1),
                (and_(System.owner!=user, System.group_assocs != None), 2)],
                else_=3),
                and_(System.hypervisor == None, Cpu.processors == 1))

    @classmethod
    def mine(cls, user):
        """
        A class method that can be used to search for systems that only
        user can see
        """
        return cls.query.filter(or_(System.user==user,
                                    System.loaned==user))

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

    @classmethod
    def by_group(cls,group_id,*args,**kw):
        return System.query.join(SystemGroup,Group).filter(Group.group_id == group_id)

    @classmethod
    def by_type(cls,type,user=None,systems=None):
        if systems:
            query = systems
        else:
            if user:
                query = System.all(user)
            else:
                query = System.all()
        return query.filter(System.type == type)

    @classmethod
    def by_arch(cls,arch,query=None):
        if query:
            return query.filter(System.arch.any(Arch.arch == arch))
        else:
            return System.query.filter(System.arch.any(Arch.arch == arch))

    def has_manual_reservation(self, user):
        """Does the specified user currently have a manual reservation?"""
        reservation = self.open_reservation
        return (reservation and reservation.type == u'manual' and
                user and self.user == user)

    def unreserve_manually_reserved(self, *args, **kw):
        open_reservation = self.open_reservation
        if not open_reservation:
            raise BX(_(u'System %s is not currently reserved' % self.fqdn))
        reservation_type = open_reservation.type
        if reservation_type == 'recipe':
            recipe_id = open_reservation.recipe.id
            raise BX(_(u'Currently running R:%s' % recipe_id))
        self.unreserve(reservation=open_reservation, *args, **kw)

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

    def install_options(self, distro_tree):
        """
        Return install options based on distro selected.
        Inherit options from Arch -> Family -> Update
        """
        osmajor = distro_tree.distro.osversion.osmajor
        result = global_install_options()
        # arch=None means apply to all arches
        if None in osmajor.install_options_by_arch:
            op = osmajor.install_options_by_arch[None]
            op_opts = InstallOptions.from_strings(op.ks_meta, op.kernel_options,
                    op.kernel_options_post)
            result = result.combined_with(op_opts)
        if distro_tree.arch in osmajor.install_options_by_arch:
            opa = osmajor.install_options_by_arch[distro_tree.arch]
            opa_opts = InstallOptions.from_strings(opa.ks_meta, opa.kernel_options,
                    opa.kernel_options_post)
            result = result.combined_with(opa_opts)
        result = result.combined_with(distro_tree.install_options())
        if distro_tree.arch in self.provisions:
            pa = self.provisions[distro_tree.arch]
            pa_opts = InstallOptions.from_strings(pa.ks_meta, pa.kernel_options,
                    pa.kernel_options_post)
            result = result.combined_with(pa_opts)
            if distro_tree.distro.osversion.osmajor in pa.provision_families:
                pf = pa.provision_families[distro_tree.distro.osversion.osmajor]
                pf_opts = InstallOptions.from_strings(pf.ks_meta,
                        pf.kernel_options, pf.kernel_options_post)
                result = result.combined_with(pf_opts)
                if distro_tree.distro.osversion in pf.provision_family_updates:
                    pfu = pf.provision_family_updates[distro_tree.distro.osversion]
                    pfu_opts = InstallOptions.from_strings(pfu.ks_meta,
                            pfu.kernel_options, pfu.kernel_options_post)
                    result = result.combined_with(pfu_opts)
        return result

    def is_free(self):
        try:
            user = identity.current.user
        except Exception:
            user = None

        if not self.user and (not self.loaned or self.loaned == user):
            return True
        else:
            return False

    def _ensure_user_is_authenticated(self, user):
        if user is None:
            raise RuntimeError("Cannot check permissions for an "
                               "unauthenticated user.")

    def can_change_owner(self, user):
        """
        Does the given user have permission to change the owner of this system?
        """
        # At least for now, any user that can edit the access policy can
        # also change the system owner (this matches the powers previously
        # granted to "admin" groups for a system)
        return self.can_edit_policy(user)

    def can_edit_policy(self, user):
        """
        Does the given user have permission to edit this system's access policy?
        """
        self._ensure_user_is_authenticated(user)
        if self.owner == user:
            return True
        if user.is_admin():
            return True
        if (self.custom_access_policy and
            self.custom_access_policy.grants(user, SystemPermission.edit_policy)):
            return True
        return False

    def can_edit(self, user):
        """
        Does the given user have permission to edit details (inventory info, 
        power config, etc) of this system?
        """
        self._ensure_user_is_authenticated(user)
        if self.owner == user:
            return True
        if user.is_admin():
            return True
        if (self.custom_access_policy and
            self.custom_access_policy.grants(user, SystemPermission.edit_system)):
            return True
        return False

    def can_lend(self, user):
        """
        Does the given user have permission to loan this system to another user?
        """
        self._ensure_user_is_authenticated(user)
        # System owner is always a loan admin
        if self.owner == user:
            return True
        # Beaker instance admins are loan admins for every system
        if user.is_admin():
            return True
        # Anyone else needs the "loan_any" permission
        if (self.custom_access_policy and
            self.custom_access_policy.grants(user, SystemPermission.loan_any)):
            return True
        return False

    def can_borrow(self, user):
        """
        Does the given user have permission to loan this system to themselves?
        """
        self._ensure_user_is_authenticated(user)
        # Loan admins can always loan to themselves
        if self.can_lend(user):
            return True
        # "loan_self" only lets you take an unloaned system and update the
        # details on a loan already granted to you
        if ((not self.loaned or self.loaned == user) and
                self.custom_access_policy and
                self.custom_access_policy.grants(user,
                                                 SystemPermission.loan_self)):
            return True
        return False

    def can_return_loan(self, user):
        """
        Does the given user have permission to cancel the current loan for this 
        system?
        """
        self._ensure_user_is_authenticated(user)
        # Users can always return their own loans
        if self.loaned and self.loaned == user:
            return True
        # Loan admins can return anyone's loan
        return self.can_lend(user)

    def can_reserve(self, user):
        """
        Does the given user have permission to reserve this system?

        Note that if is_free() returns False, the user may still not be able
        to reserve it *right now*.
        """
        self._ensure_user_is_authenticated(user)
        # System owner can always reserve the system
        if self.owner == user:
            return True
        # Loans grant the ability to reserve the system
        if self.loaned and self.loaned == user:
            return True
        # Anyone else needs the "reserve" permission
        if (self.custom_access_policy and
            self.custom_access_policy.grants(user, SystemPermission.reserve)):
            return True
        # Beaker admins can effectively reserve any system, but need to
        # grant themselves the appropriate permissions first (or loan the
        # system to themselves)
        return False

    def can_reserve_manually(self, user):
        """
        Does the given user have permission to manually reserve this system?
        """
        self._ensure_user_is_authenticated(user)
        # Manual reservations are permitted only for systems that are
        # either not automated or are currently loaned to this user
        if (self.status != SystemStatus.automated or
              (self.loaned and self.loaned == user)):
            return self.can_reserve(user)
        return False

    def can_unreserve(self, user):
        """
        Does the given user have permission to return the current reservation 
        on this system?
        """
        self._ensure_user_is_authenticated(user)
        # Users can always return their own reservations
        if self.user and self.user == user:
            return True
        # Loan admins can return anyone's reservation
        return self.can_lend(user)

    def can_power(self, user):
        """
        Does the given user have permission to run power/netboot commands on 
        this system?
        """
        self._ensure_user_is_authenticated(user)
        # Current user can always control the system
        if self.user and self.user == user:
            return True
        # System owner can always control the system
        if self.owner == user:
            return True
        # Beaker admins can control any system
        if user.is_admin():
            return True
        # Anyone else needs the "control_system" permission
        if (self.custom_access_policy and
            self.custom_access_policy.grants(user, SystemPermission.control_system)):
            return True
        return False

    def get_loan_details(self):
        """Returns details of the loan as a dict"""
        if not self.loaned:
            return {}
        return {
                   "recipient": self.loaned.user_name,
                   "comment": self.loan_comment,
               }

    def grant_loan(self, recipient, comment, service):
        """Grants a loan to the designated user if permitted"""
        if recipient is None:
            recipient = identity.current.user.user_name
        self.change_loan(recipient, comment, service)

    def return_loan(self, service):
        """Grants a loan to the designated user if permitted"""
        self.change_loan(None, None, service)

    def change_loan(self, user_name, comment=None, service='WEBUI'):
        """Changes the current system loan

        change_loan() updates the user a system is loaned to, by
        either adding a new loanee, changing the existing to another,
        or by removing the existing loanee. It also changes the comment
        associated with the loan.

        It checks all permissions that are needed and
        updates SystemActivity.

        Returns the name of the user now holding the loan (if any), otherwise
        returns the empty string.
        """
        loaning_to = user_name
        if loaning_to:
            user = User.by_user_name(loaning_to)
            if not user:
                # This is an error condition
                raise ValueError('user name %s is invalid' % loaning_to)
            if user == identity.current.user:
                if not self.can_borrow(identity.current.user):
                    msg = '%s cannot borrow this system' % user
                    raise InsufficientSystemPermissions(msg)
            else:
                if not self.can_lend(identity.current.user):
                    msg = ('%s cannot lend this system to %s' %
                                           (identity.current.user, user))
                    raise InsufficientSystemPermissions(msg)
        else:
            if not self.can_return_loan(identity.current.user):
                msg = '%s cannot return system loan' % identity.current.user
                raise InsufficientSystemPermissions(msg)
            user = None
            comment = None

        if user != self.loaned:
            activity = SystemActivity(identity.current.user, service,
                u'Changed', u'Loaned To',
                u'%s' % self.loaned if self.loaned else '',
                u'%s' % user if user else '')
            self.loaned = user
            self.activity.append(activity)

        if self.loan_comment != comment:
            activity = SystemActivity(identity.current.user, service,
                u'Changed', u'Loan Comment', u'%s' % self.loan_comment if
                self.loan_comment else '' , u'%s' % comment if
                comment else '')
            self.activity.append(activity)
            self.loan_comment = comment

        return loaning_to if loaning_to else ''

    ALLOWED_ATTRS = ['vendor', 'model', 'memory'] #: attributes which the inventory scripts may set
    PRESERVED_ATTRS = ['vendor', 'model'] #: attributes which should only be set when empty

    def get_update_method(self,obj_str):
        methods = dict ( Cpu = self.updateCpu, Arch = self.updateArch,
                         Devices = self.updateDevices, Numa = self.updateNuma,
                         Hypervisor = self.updateHypervisor, Disk = self.updateDisk)
        return methods[obj_str]

    def update_legacy(self, inventory):
        """
        Update Key/Value pairs for legacy RHTS
        """
        keys_to_update = set()
        new_int_kvs = set()
        new_string_kvs = set()
        for key_name, values in inventory.items():
            try:
                key = Key.by_name(key_name)
            except InvalidRequestError:
                continue
            keys_to_update.add(key)
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if isinstance(value, bool):
                    # MySQL will int-ify these, so we do it here 
                    # to make our comparisons accurate
                    value = int(value)
                if key.numeric:
                    new_int_kvs.add((key, int(value)))
                else:
                    new_string_kvs.add((key, unicode(value)))

        # Examine existing key-values to find what we already have, and what 
        # needs to be removed
        for kv in list(self.key_values_int):
            if kv.key in keys_to_update:
                if (kv.key, kv.key_value) in new_int_kvs:
                    new_int_kvs.remove((kv.key, kv.key_value))
                else:
                    self.key_values_int.remove(kv)
                    self.activity.append(SystemActivity(user=identity.current.user,
                            service=u'XMLRPC', action=u'Removed', field_name=u'Key/Value',
                            old_value=u'%s/%s' % (kv.key.key_name, kv.key_value),
                            new_value=None))
        for kv in list(self.key_values_string):
            if kv.key in keys_to_update:
                if (kv.key, kv.key_value) in new_string_kvs:
                    new_string_kvs.remove((kv.key, kv.key_value))
                else:
                    self.key_values_string.remove(kv)
                    self.activity.append(SystemActivity(user=identity.current.user,
                            service=u'XMLRPC', action=u'Removed', field_name=u'Key/Value',
                            old_value=u'%s/%s' % (kv.key.key_name, kv.key_value),
                            new_value=None))

        # Now we can just add the new ones
        for key, value in new_int_kvs:
            self.key_values_int.append(Key_Value_Int(key, value))
            self.activity.append(SystemActivity(user=identity.current.user,
                    service=u'XMLRPC', action=u'Added',
                    field_name=u'Key/Value', old_value=None,
                    new_value=u'%s/%s' % (key.key_name, value)))
        for key, value in new_string_kvs:
            self.key_values_string.append(Key_Value_String(key, value))
            self.activity.append(SystemActivity(user=identity.current.user,
                    service=u'XMLRPC', action=u'Added',
                    field_name=u'Key/Value', old_value=None,
                    new_value=u'%s/%s' % (key.key_name, value)))

        self.date_modified = datetime.utcnow()
        return 0


    def update(self, inventory):
        """ Update Inventory """

        # Update last checkin even if we don't change anything.
        self.date_lastcheckin = datetime.utcnow()

        md5sum = md5("%s" % inventory).hexdigest()
        if self.checksum == md5sum:
            return 0
        self.activity.append(SystemActivity(user=identity.current.user,
                service=u'XMLRPC', action=u'Changed', field_name=u'checksum',
                old_value=self.checksum, new_value=md5sum))
        self.checksum = md5sum
        for key in inventory:
            if key in self.ALLOWED_ATTRS:
                if key in self.PRESERVED_ATTRS and getattr(self, key, None):
                    continue
                setattr(self, key, inventory[key])
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Changed',
                        field_name=key, old_value=None,
                        new_value=inventory[key]))
            else:
                try:
                    method = self.get_update_method(key)
                except KeyError:
                    log.warning('Attempted to update unknown inventory property \'%s\' on %s' %
                                (key, self.fqdn))
                else:
                    method(inventory[key])
        self.date_modified = datetime.utcnow()
        return 0

    def updateHypervisor(self, hypervisor):
        if hypervisor:
            try:
                hvisor = Hypervisor.by_name(hypervisor)
            except InvalidRequestError:
                raise BX(_('Invalid Hypervisor: %s' % hypervisor))
        else:
            hvisor = None
        if self.hypervisor != hvisor:
            self.activity.append(SystemActivity(
                    user=identity.current.user,
                    service=u'XMLRPC', action=u'Changed',
                    field_name=u'Hypervisor', old_value=self.hypervisor,
                    new_value=hvisor))
            self.hypervisor = hvisor

    def updateArch(self, archinfo):
        for arch in archinfo:
            new_arch = Arch.lazy_create(arch=arch)
            if new_arch not in self.arch:
                self.arch.append(new_arch)
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Added',
                        field_name=u'Arch', old_value=None,
                        new_value=new_arch.arch))

    def updateDisk(self, diskinfo):
        currentDisks = []
        self.disks = getattr(self, 'disks', [])

        for disk in diskinfo['Disks']:
            disk = Disk(**disk)
            if disk not in self.disks:
                self.disks.append(disk)
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Added',
                        field_name=u'Disk', old_value=None,
                        new_value=disk.size))
            currentDisks.append(disk)

        for disk in self.disks:
            if disk not in currentDisks:
                self.disks.remove(disk)
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Removed',
                        field_name=u'Disk', old_value=disk.size,
                        new_value=None))

    def updateDevices(self, deviceinfo):
        currentDevices = []
        for device in deviceinfo:
            device_class = DeviceClass.lazy_create(device_class=device['type'])
            mydevice = Device.lazy_create(vendor_id = device['vendorID'],
                                   device_id = device['deviceID'],
                                   subsys_vendor_id = device['subsysVendorID'],
                                   subsys_device_id = device['subsysDeviceID'],
                                   bus = device['bus'],
                                   driver = device['driver'],
                                   device_class_id = device_class.id,
                                   description = device['description'])
            if mydevice not in self.devices:
                self.devices.append(mydevice)
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Added',
                        field_name=u'Device', old_value=None,
                        new_value=mydevice.id))
            currentDevices.append(mydevice)
        # Remove any old entries
        for device in self.devices[:]:
            if device not in currentDevices:
                self.devices.remove(device)
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Removed',
                        field_name=u'Device', old_value=device.id,
                        new_value=None))

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
        self.activity.append(SystemActivity(
                user=identity.current.user,
                service=u'XMLRPC', action=u'Changed',
                field_name=u'CPU', old_value=None,
                new_value=None)) # XXX find a good way to record the actual changes

    def updateNuma(self, numainfo):
        if self.numa:
            session.delete(self.numa)
        if numainfo.get('nodes', None) is not None:
            self.numa = Numa(nodes=numainfo['nodes'])
        self.activity.append(SystemActivity(
                user=identity.current.user,
                service=u'XMLRPC', action=u'Changed',
                field_name=u'NUMA', old_value=None,
                new_value=None)) # XXX find a good way to record the actual changes

    def excluded_osmajor_byarch(self, arch):
        """
        List excluded osmajor for system by arch
        """
        excluded = ExcludeOSMajor.query.join('system').\
                    join('arch').filter(and_(System.id==self.id,
                                             Arch.id==arch.id))
        return excluded

    def excluded_osversion_byarch(self, arch):
        """
        List excluded osversion for system by arch
        """
        excluded = ExcludeOSVersion.query.join('system').\
                    join('arch').filter(and_(System.id==self.id,
                                             Arch.id==arch.id))
        return excluded

    def distro_trees(self, only_in_lab=True):
        """
        List of distro trees that support this system
        """
        query = DistroTree.query\
                .join(DistroTree.distro, Distro.osversion, OSVersion.osmajor)\
                .options(contains_eager(DistroTree.distro, Distro.osversion, OSVersion.osmajor))
        if only_in_lab:
            query = query.filter(DistroTree.lab_controller_assocs.any(
                    LabControllerDistroTree.lab_controller == self.lab_controller))
        else:
            query = query.filter(DistroTree.lab_controller_assocs.any())
        query = query.filter(DistroTree.arch_id.in_([a.id for a in self.arch]))\
                .filter(not_(OSMajor.excluded_osmajors.any(and_(
                    ExcludeOSMajor.system == self,
                    ExcludeOSMajor.arch_id == DistroTree.arch_id))
                    .correlate(DistroTree.__table__)))\
                .filter(not_(OSVersion.excluded_osversions.any(and_(
                    ExcludeOSVersion.system == self,
                    ExcludeOSVersion.arch_id == DistroTree.arch_id))
                    .correlate(DistroTree.__table__)))
        return query

    def action_release(self, service=u'Scheduler'):
        # Attempt to remove Netboot entry and turn off machine
        self.clear_netboot(service=service)
        if self.release_action:
            if self.release_action == ReleaseAction.power_off:
                self.action_power(action=u'off', service=service)
            elif self.release_action == ReleaseAction.leave_on:
                self.action_power(action=u'on', service=service)
            elif self.release_action == ReleaseAction.reprovision:
                if self.reprovision_distro_tree:
                    # There are plenty of things that can go wrong here if the 
                    # system or distro tree is misconfigured. But we don't want 
                    # that to prevent the recipe from being stopped, so we log 
                    # and ignore any errors.
                    try:
                        from bkr.server.kickstart import generate_kickstart
                        install_options = self.install_options(self.reprovision_distro_tree)
                        if 'ks' not in install_options.kernel_options:
                            rendered_kickstart = generate_kickstart(install_options,
                                    distro_tree=self.reprovision_distro_tree,
                                    system=self, user=self.owner)
                            install_options.kernel_options['ks'] = rendered_kickstart.link
                        self.configure_netboot(self.reprovision_distro_tree,
                                install_options.kernel_options_str,
                                service=service)
                        self.action_power(action=u'reboot', service=service)
                    except Exception:
                        log.exception('Failed to re-provision %s on %s, ignoring',
                                self.reprovision_distro_tree, self)
            else:
                raise ValueError('Not a valid ReleaseAction: %r' % self.release_action)
        # Default is to power off, if we can
        elif self.power:
            self.action_power(action=u'off', service=service)

    def configure_netboot(self, distro_tree, kernel_options, service=u'Scheduler',
            callback=None):
        try:
            user = identity.current.user
        except Exception:
            user = None
        if self.lab_controller:
            self.command_queue.append(CommandActivity(user=user,
                    service=service, action=u'clear_logs',
                    status=CommandStatus.queued, callback=callback))
            command = CommandActivity(user=user,
                    service=service, action=u'configure_netboot',
                    status=CommandStatus.queued, callback=callback)
            command.distro_tree = distro_tree
            command.kernel_options = kernel_options
            self.command_queue.append(command)
        else:
            return False

    def action_power(self, action=u'reboot', service=u'Scheduler',
            callback=None, delay=0):
        try:
            user = identity.current.user
        except Exception:
            user = None

        if self.lab_controller and self.power:
            status = CommandStatus.queued
            activity = CommandActivity(user, service, action, status, callback,
                 self.power.power_quiescent_period)
            if delay:
                activity.delay_until = datetime.utcnow() + timedelta(seconds=delay)
            self.command_queue.append(activity)
            return activity
        else:
            return False

    def clear_netboot(self, service=u'Scheduler'):
        try:
            user = identity.current.user
        except Exception:
            user = None
        if self.lab_controller:
            self.command_queue.append(CommandActivity(user=user,
                    service=service, action=u'clear_netboot',
                    status=CommandStatus.queued))

    def __repr__(self):
        return self.fqdn

    @property
    def href(self):
        """Returns a relative URL for this system's page."""
        return urllib.quote((u'/view/%s' % self.fqdn).encode('utf8'))

    def link(self):
        """ Return a link to this system
        """
        return make_link(url = '/view/%s' % self.fqdn,
                         text = self.fqdn)

    link = property(link)

    def report_problem_href(self, **kwargs):
        return url('/report_problem', system_id=self.id, **kwargs)

    def mark_broken(self, reason, recipe=None, service=u'Scheduler'):
        """Sets the system status to Broken and notifies its owner."""
        try:
            user = identity.current.user
        except Exception:
            user = None
        log.warning('Marking system %s as broken' % self.fqdn)
        sa = SystemActivity(user, service, u'Changed', u'Status', unicode(self.status), u'Broken')
        self.activity.append(sa)
        self.status = SystemStatus.broken
        self.date_modified = datetime.utcnow()
        mail.broken_system_notify(self, reason, recipe)

    def suspicious_abort(self):
        # Delayed import to avoid circular dependency
        from . import Recipe
        if self.status == SystemStatus.broken:
            return # nothing to do
        if self.type != SystemType.machine:
            return # prototypes get more leeway, and virtual machines can't really "break"...
        reliable_distro_tag = get('beaker.reliable_distro_tag', None)
        if not reliable_distro_tag:
            return
        # Since its last status change, has this system had an 
        # uninterrupted run of aborted recipes leading up to this one, with 
        # at least two different STABLE distros?
        # XXX this query is stupidly big, I need to do something about it
        session.flush()
        status_change_subquery = session.query(func.max(SystemActivity.created))\
            .filter(and_(
                SystemActivity.system_id == self.id,
                SystemActivity.field_name == u'Status',
                SystemActivity.action == u'Changed'))\
            .subquery()
        nonaborted_recipe_subquery = self.dyn_recipes\
            .filter(Recipe.status != TaskStatus.aborted)\
            .with_entities(func.max(Recipe.finish_time))\
            .subquery()
        count = self.dyn_recipes.join(Recipe.distro_tree, DistroTree.distro)\
            .filter(and_(
                Distro.tags.contains(reliable_distro_tag.decode('utf8')),
                Recipe.start_time >
                    func.ifnull(status_change_subquery.as_scalar(), self.date_added),
                Recipe.finish_time > nonaborted_recipe_subquery.as_scalar().correlate(None)))\
            .value(func.count(DistroTree.id.distinct()))
        if count >= 2:
            # Broken!
            metrics.increment('counters.suspicious_aborts')
            reason = unicode(_(u'System has a run of aborted recipes '
                    'with reliable distros'))
            log.warn(reason)
            self.mark_broken(reason=reason)

    def reserve_manually(self, service, user=None):
        if user is None:
            user = identity.current.user
        self._check_can_reserve(user)
        if not self.can_reserve_manually(user):
            raise BX(_(u'Cannot manually reserve automated system, '
                    'without borrowing it first. Schedule a job instead'))
        return self._reserve(service, user, u'manual')

    def reserve_for_recipe(self, service, user=None):
        if user is None:
            user = identity.current.user
        self._check_can_reserve(user)
        return self._reserve(service, user, u'recipe')

    def _check_can_reserve(self, user):
        # Throw an exception if the given user can't reserve the system.
        if self.user is not None and self.user == user:
            raise StaleSystemUserException(_(u'User %s has already reserved '
                'system %s') % (user, self))
        if not self.can_reserve(user):
            raise InsufficientSystemPermissions(_(u'User %s cannot '
                'reserve system %s') % (user, self))
        if self.loaned:
            # loans give exclusive rights to reserve
            if user != self.loaned and user != self.owner:
                raise InsufficientSystemPermissions(_(u'User %s cannot reserve '
                        'system %s while it is loaned to user %s')
                        % (user, self, self.loaned))

    def _reserve(self, service, user, reservation_type):
        # Atomic operation to reserve the system
        session.flush()
        if session.connection(System).execute(System.__table__.update(
                and_(System.id == self.id,
                     System.user_id == None)),
                user_id=user.user_id).rowcount != 1:
            raise StaleSystemUserException(_(u'System %r is already '
                'reserved') % self)
        self.user = user # do it here too, so that the ORM is aware
        reservation = Reservation(user=user, type=reservation_type)
        self.reservations.append(reservation)
        self.activity.append(SystemActivity(user=user,
                service=service, action=u'Reserved', field_name=u'User',
                old_value=u'', new_value=user.user_name))
        log.debug('Created reservation for system %r with type %r, service %r, user %r',
                self, reservation_type, service, user)
        return reservation

    def unreserve(self, service=None, reservation=None, user=None):
        if user is None:
            user = identity.current.user

        if self.user is None:
            raise BX(_(u'System is not reserved'))
        if not self.can_unreserve(user):
            raise InsufficientSystemPermissions(
                    _(u'User %s cannot unreserve system %s, reserved by %s')
                    % (user, self, self.user))

        # Update reservation atomically first, to avoid races
        session.flush()
        my_reservation_id = reservation.id
        if session.connection(System).execute(Reservation.__table__.update(
                and_(Reservation.id == my_reservation_id,
                     Reservation.finish_time == None)),
                finish_time=datetime.utcnow()).rowcount != 1:
            raise BX(_(u'System does not have an open reservation'))
        session.expire(reservation, ['finish_time'])
        old_user = self.user
        self.user = None
        self.action_release(service=service)
        activity = SystemActivity(user=user,
                service=service, action=u'Returned', field_name=u'User',
                old_value=old_user.user_name, new_value=u'')
        self.activity.append(activity)

    def add_note(self, text, user, service=u'WEBUI'):
        note = Note(user=user, text=text)
        self.notes.append(note)
        self.record_activity(user=user, service=service,
                             action='Added', field='Note',
                             old='', new=text)
        self.date_modified = datetime.utcnow()

    cc = association_proxy('_system_ccs', 'email_address')

    groups = association_proxy('group_assocs', 'group',
            creator=lambda group: SystemGroup(group=group))

class SystemCc(DeclarativeMappedObject):

    __tablename__ = 'system_cc'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    system_id = Column(Integer, ForeignKey('system.id', ondelete='CASCADE',
            onupdate='CASCADE'), primary_key=True)
    email_address = Column(Unicode(255), primary_key=True, index=True)

    def __init__(self, email_address):
        super(SystemCc, self).__init__()
        self.email_address = email_address


class Hypervisor(DeclarativeMappedObject):

    __tablename__ = 'hypervisor'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    hypervisor = Column(Unicode(100), nullable=False)

    def __repr__(self):
        return self.hypervisor

    @classmethod
    def get_all_types(cls):
        """
        return an array of tuples containing id, hypervisor
        """
        return [(hvisor.id, hvisor.hypervisor) for hvisor in cls.query]

    @classmethod
    def get_all_names(cls):
        return [h.hypervisor for h in cls.query]

    @classmethod
    def by_name(cls, hvisor):
        return cls.query.filter_by(hypervisor=hvisor).one()


class SystemAccessPolicy(DeclarativeMappedObject):

    """
    A list of rules controlling who is allowed to do what to a system.
    """
    __tablename__ = 'system_access_policy'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, nullable=False, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
            name='system_access_policy_system_id_fk'))
    system = relationship(System,
            backref=backref('custom_access_policy', uselist=False))

    @hybrid_method
    def grants(self, user, permission):
        """
        Does this policy grant the given permission to the given user?
        """
        return any(rule.permission == permission and
                (rule.user == user or rule.group in user.groups or rule.everybody)
                for rule in self.rules)

    @grants.expression
    def grants(cls, user, permission):
        # need to avoid passing an empty list to in_
        clauses = [SystemAccessPolicyRule.user == user, SystemAccessPolicyRule.everybody]
        if user.groups:
            clauses.append(SystemAccessPolicyRule.group_id.in_(
                    [g.group_id for g in user.groups]))
        return cls.rules.any(and_(SystemAccessPolicyRule.permission == permission,
                or_(*clauses)))

    @hybrid_method
    def grants_everybody(self, permission):
        """
        Does this policy grant the given permission to all users?
        """
        return any(rule.permission == permission and rule.everybody
                for rule in self.rules)

    @grants_everybody.expression
    def grants_everybody(cls, permission):
        return cls.rules.any(and_(SystemAccessPolicyRule.permission == permission,
                SystemAccessPolicyRule.everybody))

    def add_rule(self, permission, user=None, group=None, everybody=False):
        """
        Pass either user, or group, or everybody=True.
        """
        if user is not None and group is not None:
            raise RuntimeError('Rules are for a user or a group, not both')
        if user is None and group is None and not everybody:
            raise RuntimeError('Did you mean to pass everybody=True to add_rule?')
        session.flush() # make sure self is persisted, for lazy_create
        self.rules.append(SystemAccessPolicyRule.lazy_create(policy_id=self.id,
                permission=permission,
                user_id=user.user_id if user else None,
                group_id=group.group_id if group else None))
        return self.rules[-1]

class SystemAccessPolicyRule(DeclarativeMappedObject):

    """
    A single rule in a system access policy. Policies can have one or more of these.

    The existence of a row in this table means that the given permission is 
    granted to the given user or group in this policy.
    """
    __tablename__ = 'system_access_policy_rule'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    # It would be nice to have a constraint like:
    #    UniqueConstraint('policy_id', 'user_id', 'group_id', 'permission')
    # but we can't because user_id and group_id are NULLable and MySQL has
    # non-standard behaviour for that which makes the constraint useless :-(

    id = Column(Integer, nullable=False, primary_key=True)
    policy_id = Column(Integer, ForeignKey('system_access_policy.id',
            name='system_access_policy_rule_policy_id_fk'), nullable=False)
    policy = relationship(SystemAccessPolicy, backref=backref('rules',
            cascade='all, delete, delete-orphan'))
    # Either user or group is set, to indicate who the rule applies to.
    # If both are NULL, the rule applies to everyone.
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            name='system_access_policy_rule_user_id_fk'))
    user = relationship(User)
    group_id = Column(Integer, ForeignKey('tg_group.group_id',
            name='system_access_policy_rule_group_id_fk'))
    group = relationship(Group)
    permission = Column(SystemPermission.db_type())

    def __repr__(self):
        return '<grant %s to %s>' % (self.permission,
                self.group or self.user or 'everybody')

    @hybrid_property
    def everybody(self):
        return (self.user == None) & (self.group == None)


class Provision(DeclarativeMappedObject):

    __tablename__ = 'provision'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    ks_meta = Column(String(1024))
    kernel_options = Column(String(1024))
    kernel_options_post = Column(String(1024))
    arch_id = Column(Integer, ForeignKey('arch.id'), nullable=False)
    arch = relationship(Arch)
    provision_families = relationship('ProvisionFamily',
            collection_class=attribute_mapped_collection('osmajor'),
            cascade='all, delete, delete-orphan')


class ProvisionFamily(DeclarativeMappedObject):

    __tablename__ = 'provision_family'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    provision_id = Column(Integer, ForeignKey('provision.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    osmajor_id = Column(Integer, ForeignKey('osmajor.id'), nullable=False)
    osmajor = relationship(OSMajor)
    ks_meta = Column(String(1024))
    kernel_options = Column(String(1024))
    kernel_options_post = Column(String(1024))
    provision_family_updates = relationship('ProvisionFamilyUpdate',
            collection_class=attribute_mapped_collection('osversion'),
            cascade='all, delete, delete-orphan')


class ProvisionFamilyUpdate(DeclarativeMappedObject):

    __tablename__ = 'provision_update_family'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    provision_family_id = Column(Integer, ForeignKey('provision_family.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    osversion_id = Column(Integer, ForeignKey('osversion.id'), nullable=False)
    osversion = relationship(OSVersion)
    ks_meta = Column(String(1024))
    kernel_options = Column(String(1024))
    kernel_options_post = Column(String(1024))


class ExcludeOSMajor(DeclarativeMappedObject):

    __tablename__ = 'exclude_osmajor'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    arch_id = Column(Integer, ForeignKey('arch.id'), nullable=False)
    arch = relationship(Arch)
    osmajor_id = Column(Integer, ForeignKey('osmajor.id'), nullable=False)
    osmajor = relationship(OSMajor, backref='excluded_osmajors')


class ExcludeOSVersion(DeclarativeMappedObject):

    __tablename__ = 'exclude_osversion'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    arch_id = Column(Integer, ForeignKey('arch.id'), nullable=False)
    arch = relationship(Arch)
    osversion_id = Column(Integer, ForeignKey('osversion.id'), nullable=False)
    osversion = relationship(OSVersion, backref='excluded_osversions')


class LabInfo(DeclarativeMappedObject):

    __tablename__ = 'labinfo'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    orig_cost = Column(Numeric(precision=16, scale=2, asdecimal=True))
    curr_cost = Column(Numeric(precision=16, scale=2, asdecimal=True))
    dimensions = Column(String(255))
    weight = Column(Numeric(asdecimal=False))
    wattage = Column(Numeric(asdecimal=False))
    cooling = Column(Numeric(asdecimal=False))

    fields = ['orig_cost', 'curr_cost', 'dimensions', 'weight', 'wattage', 'cooling']


class Cpu(DeclarativeMappedObject):

    __tablename__ = 'cpu'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    vendor = Column(String(255))
    model = Column(Integer)
    model_name = Column(String(255))
    family = Column(Integer)
    stepping = Column(Integer)
    speed = Column(Float)
    processors = Column(Integer)
    cores = Column(Integer)
    sockets = Column(Integer)
    hyper = Column(Boolean)
    flags = relationship('CpuFlag', cascade='all, delete, delete-orphan')

    def __init__(self, vendor=None, model=None, model_name=None, family=None, stepping=None,speed=None,processors=None,cores=None,sockets=None,flags=None):
        super(Cpu, self).__init__()
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
        if flags != None:
            for cpuflag in flags:
                new_flag = CpuFlag(flag=cpuflag)
                self.flags.append(new_flag)

class CpuFlag(DeclarativeMappedObject):

    __tablename__ = 'cpu_flag'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    cpu_id = Column(Integer, ForeignKey('cpu.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    flag = Column(String(255))

    def __init__(self, flag=None):
        super(CpuFlag, self).__init__()
        self.flag = flag

    def __repr__(self):
        return self.flag

    def by_flag(cls, flag):
        return cls.query.filter_by(flag=flag)

    by_flag = classmethod(by_flag)


class Numa(DeclarativeMappedObject):

    __tablename__ = 'numa'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    nodes = Column(Integer)

    def __init__(self, nodes=None):
        super(Numa, self).__init__()
        self.nodes = nodes

    def __repr__(self):
        return str(self.nodes)


class DeviceClass(DeclarativeMappedObject):

    __tablename__ = 'device_class'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    device_class = Column(VARCHAR(24), nullable=False, unique=True)
    description = Column(TEXT)

    @classmethod
    def lazy_create(cls, device_class=None, **kwargs):
        """
        Like the normal lazy_create, but with special handling for
        device_class None -> "NONE".
        """
        if not device_class:
            device_class = 'NONE'
        return super(DeviceClass, cls).lazy_create(
                device_class=device_class, **kwargs)

    def __init__(self, device_class=None, description=None):
        super(DeviceClass, self).__init__()
        if not device_class:
            device_class = "NONE"
        self.device_class = device_class
        self.description = description

    def __repr__(self):
        return self.device_class


class Device(DeclarativeMappedObject):

    __tablename__ = 'device'
    __table_args__ = (
        UniqueConstraint('vendor_id', 'device_id', 'subsys_device_id',
               'subsys_vendor_id', 'bus', 'driver', 'description',
               name='device_uix_1'),
        {'mysql_engine': 'InnoDB'}
    )
    id = Column(Integer, autoincrement=True, primary_key=True)
    vendor_id = Column(String(4))
    device_id = Column(String(4))
    subsys_device_id = Column(String(4))
    subsys_vendor_id = Column(String(4))
    bus = Column(String(255))
    driver = Column(String(255), index=True)
    description = Column(String(255))
    device_class_id = Column(Integer, ForeignKey('device_class.id'), nullable=False)
    device_class = relationship(DeviceClass)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)

Index('ix_device_pciid', Device.vendor_id, Device.device_id)

class Disk(DeclarativeMappedObject):

    __tablename__ = 'disk'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id'), nullable=False)
    model = Column(String(255))
    # sizes are in bytes
    size = Column(BigInteger)
    sector_size = Column(Integer)
    phys_sector_size = Column(Integer)

    def __init__(self, size=None, sector_size=None, phys_sector_size=None, model=None):
        super(Disk, self).__init__()
        self.size = int(size)
        self.sector_size = int(sector_size)
        self.phys_sector_size = int(phys_sector_size)
        self.model = model

class PowerType(DeclarativeMappedObject):

    __tablename__ = 'power_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String(255), nullable=False)

    def __init__(self, name=None):
        super(PowerType, self).__init__()
        self.name = name

    @classmethod
    def get_all(cls):
        """
        Apc, wti, etc..
        """
        all_types = cls.query
        return [(0, "None")] + [(type.id, type.name) for type in all_types]

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name=name).one()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def list_by_name(cls,name,find_anywhere=False):
        if find_anywhere:
            q = cls.query.filter(PowerType.name.like('%%%s%%' % name))
        else:
            q = cls.query.filter(PowerType.name.like('%s%%' % name))
        return q

class Power(DeclarativeMappedObject):

    __tablename__ = 'power'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    power_type_id = Column(Integer, ForeignKey('power_type.id'), nullable=False)
    power_type = relationship(PowerType, backref='power_control')
    system_id = Column(Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    power_address = Column(String(255), nullable=False)
    power_user = Column(String(255))
    power_passwd = Column(String(255))
    power_id = Column(String(255))
    # 5(seconds) was the default sleep time for commands in beaker-provision
    power_quiescent_period = Column(Integer, default=5, nullable=False)

# note model
class Note(DeclarativeMappedObject):

    __tablename__ = 'note'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id', onupdate='CASCADE',
            ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'), index=True)
    user = relationship(User, backref='notes')
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    text = Column(TEXT, nullable=False)
    deleted = Column(DateTime, nullable=True, default=None)
    system = relationship(System, backref=backref('notes',
            cascade='all, delete, delete-orphan', order_by=[created.desc()]))

    def __init__(self, user=None, text=None):
        super(Note, self).__init__()
        self.user = user
        self.text = text

    @classmethod
    def all(cls):
        return cls.query

    @property
    def html(self):
        """
        The note's text rendered to HTML using Markdown.
        """
        # Try rendering as markdown, if that fails for any reason, just
        # return the raw text string. The template will take care of the
        # difference (this really doesn't belong in the model, though...)
        try:
            rendered = markdown(self.text, safe_mode='escape')
        except Exception:
            return self.text
        return XML(rendered)


class Key(DeclarativeMappedObject):

    __tablename__ = 'key_'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    key_name = Column(String(50), nullable=False, unique=True)
    numeric = Column(Boolean, default=False)

    # Obsoleted keys are ones which have been replaced by real, structured 
    # columns on the system table (and its related tables). We disallow users 
    # from searching on these keys in the web UI, to encourage them to migrate 
    # to the structured columns instead (and to avoid the costly queries that 
    # sometimes result).
    obsoleted_keys = [u'MODULE', u'PCIID']

    @classmethod
    def get_all_keys(cls):
        """
        This method's name is deceptive, it actually excludes "obsoleted" keys.
        """
        all_keys = cls.query
        return [key.key_name for key in all_keys
                if key.key_name not in cls.obsoleted_keys]

    @classmethod
    def by_name(cls, key_name):
        return cls.query.filter_by(key_name=key_name).one()


    @classmethod
    def list_by_name(cls, name, find_anywhere=False):
        """
        A class method that can be used to search keys
        based on the key_name
        """
        if find_anywhere:
            q = cls.query.filter(Key.key_name.like('%%%s%%' % name))
        else:
            q = cls.query.filter(Key.key_name.like('%s%%' % name))
        return q

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    def __init__(self, key_name=None, numeric=False):
        super(Key, self).__init__()
        self.key_name = key_name
        self.numeric = numeric

    def __repr__(self):
        return "%s" % self.key_name


# key_value model
class Key_Value_String(DeclarativeMappedObject):

    __tablename__ = 'key_value_string'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id', onupdate='CASCADE',
            ondelete='CASCADE'), nullable=False, index=True)
    key_id = Column(Integer, ForeignKey('key_.id', onupdate='CASCADE',
            ondelete='CASCADE'), nullable=False, index=True)
    key = relationship(Key, backref=backref('key_value_string',
            cascade='all, delete-orphan'))
    key_value = Column(TEXT, nullable=False)

    key_type = 'string'

    def __init__(self, key, key_value, system=None):
        super(Key_Value_String, self).__init__()
        self.system = system
        self.key = key
        self.key_value = key_value

    def __repr__(self):
        return "%s %s" % (self.key, self.key_value)

    @classmethod
    def by_key_value(cls, system, key, value):
        return cls.query.filter(and_(Key_Value_String.key==key,
                                  Key_Value_String.key_value==value,
                                  Key_Value_String.system==system)).one()


class Key_Value_Int(DeclarativeMappedObject):

    __tablename__ = 'key_value_int'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id', onupdate='CASCADE',
            ondelete='CASCADE'), nullable=False, index=True)
    key_id = Column(Integer, ForeignKey('key_.id', onupdate='CASCADE',
            ondelete='CASCADE'), nullable=False, index=True)
    key = relationship(Key, backref=backref('key_value_int',
            cascade='all, delete-orphan'))
    key_value = Column(Integer, nullable=False)

    key_type = 'int'

    def __init__(self, key, key_value, system=None):
        super(Key_Value_Int, self).__init__()
        self.system = system
        self.key = key
        self.key_value = key_value

    def __repr__(self):
        return "%s %s" % (self.key, self.key_value)

    @classmethod
    def by_key_value(cls, system, key, value):
        return cls.query.filter(and_(Key_Value_Int.key==key,
                                  Key_Value_Int.key_value==value,
                                  Key_Value_Int.system==system)).one()

# available in python 2.7+ importlib
def import_module(modname):
    __import__(modname)
    return sys.modules[modname]
