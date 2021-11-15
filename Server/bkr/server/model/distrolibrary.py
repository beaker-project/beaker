
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
from datetime import datetime
import urlparse
import xml.dom.minidom
import lxml.etree
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Integer,
        String, Unicode, DateTime, UnicodeText, Boolean)
from sqlalchemy.sql import select, exists, or_
from sqlalchemy.orm import (relationship, backref, dynamic_loader, synonym,
                            validates)
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.database import session
from bkr.server import identity
from bkr.server.helpers import make_link
from bkr.server.util import convert_db_lookup_error
from bkr.server.installopts import InstallOptions, global_install_options
from .sql import ConditionalInsert
from .base import DeclarativeMappedObject
from .types import ImageType, SystemStatus
from .activity import Activity, ActivityMixin
from .lab import LabController


def split_osmajor_name_version(osmajor):
    return re.match(r'(.*?)(rawhide|\d*)$', osmajor).groups()


def default_install_options_for_distro(osmajor_name, osminor, variant, arch):
    """
    Returns the default install options supplied by Beaker (rather than the
    admin) based on some hardcoded OS major names.
    This is where installer feature test variables are populated.
    """
    # Some convenience variables to make the name-based checks simpler:
    name, version = split_osmajor_name_version(osmajor_name)
    rhel, fedora = False, False
    rhel_like = ['RedHatEnterpriseLinux', 'CentOS', 'OracleLinux']
    if any(distro in name for distro in rhel_like):
        rhel = version
    if osmajor_name in ('RedHatStorage2', 'RedHatStorageSoftwareAppliance3',
                        'RedHatGlusterStorage3'):
        rhel = '6'
    if osmajor_name in ('RHVH4',):
        # Due to great semver RHVH4 changed underlying operating system
        # in minor version - RHVH4.4+ => EL8
        rhel = '7' if int(osminor) <= 3 else '8'
    if name == 'Fedora':
        fedora = version

    # We default to assuming all features are present, with features
    # conditionally turned off if needed. That way, unrecognised custom
    # distros will be assumed to support all features. The admin can
    # override these in OS major or distro install options if necessary.
    ks_meta = {}

    # Default harness for all distributions
    # User can always opt-out by defining harness in ks_meta
    ks_meta['harness'] = 'restraint-rhts'

    # %end
    ks_meta['end'] = '%end'
    if rhel == '5':
        ks_meta['end'] = ''
    # key option for RHEL 5
    if rhel and int(rhel) == 5:
        ks_meta['has_key'] = True
    # autopart --type
    ks_meta['has_autopart_type'] = True
    if rhel in ('5', '6') or \
            (fedora and fedora != 'rawhide' and int(fedora) < 18):
        del ks_meta['has_autopart_type']
    # chrony
    ks_meta['has_chrony'] = True
    if rhel in ('5', '6'):
        del ks_meta['has_chrony']
    # DHCP option 26
    ks_meta['has_dhcp_mtu_support'] = True
    # GPT on BIOS
    ks_meta['has_gpt_bios_support'] = True
    if rhel in ('5', '6'):
        del ks_meta['has_gpt_bios_support']
    # bootloader --leavebootorder
    ks_meta['has_leavebootorder'] = True
    if rhel in ('5', '6') or \
            (fedora and fedora != 'rawhide' and int(fedora) < 18):
        del ks_meta['has_leavebootorder']
    # repo --cost
    ks_meta['has_repo_cost'] = True
    if rhel == '5':
        del ks_meta['has_repo_cost']
    # reqpart
    ks_meta['has_reqpart'] = True
    if rhel == '7' and osminor in ('0', '1'): # added in RHEL7.2
        del ks_meta['has_reqpart']
    if rhel in ('5', '6') or \
            (fedora and fedora != 'rawhide' and int(fedora) < 23):
        del ks_meta['has_reqpart']
    # systemd vs. SysV init
    ks_meta['has_systemd'] = True
    if rhel in ('5', '6') or \
            (fedora and fedora != 'rawhide' and int(fedora) < 15):
        del ks_meta['has_systemd']
    # unsupported_hardware
    ks_meta['has_unsupported_hardware'] = True
    if rhel == '5':
        del ks_meta['has_unsupported_hardware']
    # support for %onerror
    ks_meta['has_onerror'] = True
    if rhel in ('5', '6') or (rhel == '7' and int(osminor) <= 3):
        del ks_meta['has_onerror']

    # mode
    if rhel == '6':
        ks_meta['mode'] = 'cmdline'
    if rhel == '5':
        ks_meta['mode'] = ''
    # docker package name
    ks_meta['docker_package'] = 'docker'
    if (fedora and fedora != 'rawhide' and int(fedora) < 22)  or (rhel and int(rhel) <= 6):
        ks_meta['docker_package'] = 'docker-io'
    # recommended boot partition size
    if rhel in ('5', '6'):
        ks_meta['boot_partition_size'] = 250
    # names of package groups containing conflicts
    if name in ('RedHatEnterpriseLinux', 'RedHatEnterpriseLinuxServer',
        'RedHatEnterpriseLinuxClient'):
        if int(rhel) >= 5:
            ks_meta['conflicts_groups'] = ['conflicts']
        if (int(rhel) >= 6) and variant:
            ks_meta['conflicts_groups'] = ['conflicts-%s' % variant.lower()]
    elif name == 'CentOS' and int(rhel) >= 6:
        ks_meta['conflicts_groups'] = [
                'conflicts-client',
                'conflicts-server',
                'conflicts-workstation',
        ]
    else:
        ks_meta['conflicts_groups'] = []

    # clearpart --cdl
    if arch.arch == 's390x' and (rhel == '7' and int(osminor) >= 6
                                 or rhel == '8' and int(osminor) >= 0):
        ks_meta['has_clearpart_cdl'] = True

    ks_meta['has_ignoredisk_interactive'] = False  # --interactive is deprecated
    if (rhel and int(rhel) < 8) or (fedora and fedora != 'rawhide' and int(fedora) < 29):
        ks_meta['has_ignoredisk_interactive'] = True

    # Remove Fedora disabled root/password ssh combination
    # introduced in Fedora 31
    if (fedora and (fedora == 'rawhide' or int(fedora) > 30)) or (rhel and int(rhel) >= 9):
        ks_meta['disabled_root_access'] = True

    kernel_options = {}
    # set arch specific default netboot loader paths
    # relative to the TFTP root directory
    netbootloader = {'i386': 'pxelinux.0',
                     # We can't distinguish between UEFI and BIOS systems at this level
                     # so, we default to pxelinux.0
                     'x86_64': 'pxelinux.0',
                     'ia64': 'elilo-ia64.efi',
                     'ppc': 'yaboot',
                     'ppc64': 'boot/grub2/powerpc-ieee1275/core.elf',
                     'ppc64le': 'boot/grub2/powerpc-ieee1275/core.elf',
                     'aarch64': 'aarch64/bootaa64.efi',
                     }
    if rhel and (int(rhel) <= 6 or (int(rhel) == 7 and osminor == '0')):
        netbootloader['ppc64'] = 'yaboot'
        netbootloader['ppc64le'] = 'yaboot'
    # for s390, s390x and armhfp, we default to ''
    kernel_options['netbootloader'] = netbootloader.get(arch.arch, '')
    if arch.arch in ['ppc', 'ppc64', 'ppc64le']:
        if rhel and int(rhel) < 9 or \
                (fedora and fedora != 'rawhide' and int(fedora) < 34):
            kernel_options['leavebootorder'] = None
        else:
            kernel_options['inst.leavebootorder'] = None

    # Keep old kernel options for older distros
    if rhel and int(rhel) < 9 or \
            (fedora and fedora != 'rawhide' and int(fedora) < 34):
        kernel_options['ksdevice'] = 'bootif'
        ks_meta['ks_keyword'] = 'ks'

    return InstallOptions(ks_meta, kernel_options, {})

def install_options_for_distro(osmajor_name, osminor, variant, arch):
    sources = []
    sources.append(global_install_options())
    sources.append(default_install_options_for_distro(
            osmajor_name, osminor, variant, arch))
    try:
        osmajor = OSMajor.by_name(osmajor_name)
    except NoResultFound:
        pass # not known to Beaker
    else:
        # arch=None means apply to all arches
        if None in osmajor.install_options_by_arch:
            op = osmajor.install_options_by_arch[None]
            sources.append(InstallOptions.from_strings(
                    op.ks_meta, op.kernel_options, op.kernel_options_post))
        if arch in osmajor.install_options_by_arch:
            opa = osmajor.install_options_by_arch[arch]
            sources.append(InstallOptions.from_strings(
                    opa.ks_meta, opa.kernel_options, opa.kernel_options_post))
    return InstallOptions.reduce(sources)

xmldoc = xml.dom.minidom.Document()

osversion_arch_map = Table('osversion_arch_map', DeclarativeMappedObject.metadata,
    Column('osversion_id', Integer,
           ForeignKey('osversion.id'),
           primary_key=True, index=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True, index=True),
    mysql_engine='InnoDB',
)

distro_tag_map = Table('distro_tag_map', DeclarativeMappedObject.metadata,
    Column('distro_id', Integer, ForeignKey('distro.id'),
                                         primary_key=True),
    Column('distro_tag_id', Integer, ForeignKey('distro_tag.id'),
                                         primary_key=True),
    mysql_engine='InnoDB',
)

class DistroActivity(Activity):

    __tablename__ = 'distro_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    distro_id = Column(Integer, ForeignKey('distro.id'), index=True, nullable=False)
    object_id = synonym('distro_id')
    object = relationship('Distro', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'distro_activity'}

    def object_name(self):
        return "Distro: %s" % self.object.name

    def __json__(self):
        result = super(DistroActivity, self).__json__()
        result['distro'] = {
            'id': self.object.id,
            'name': self.object.name,
        }
        return result

class DistroTreeActivity(Activity):

    __tablename__ = 'distro_tree_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'), index=True, nullable=False)
    object_id = synonym('distro_tree_id')
    object = relationship('DistroTree', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'distro_tree_activity'}

    def object_name(self):
        return u'DistroTree: %s' % self.object

    def __json__(self):
        result = super(DistroTreeActivity, self).__json__()
        result['distro_tree'] = {
            'id': self.object.id,
            'distro': {
                'id': self.object.distro.id,
                'name': self.object.distro.name,
            },
            'variant': self.object.variant,
            'arch': self.object.arch,
        }
        return result

class KernelType(DeclarativeMappedObject):

    __tablename__ = 'kernel_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    kernel_type = Column(Unicode(100), nullable=False)
    uboot = Column(Boolean, default=False)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.kernel_type)

    def __unicode__(self):
        return self.kernel_type

    def __str__(self):
        return unicode(self).encode('utf8')

    def __json__(self):
        return unicode(self)

    @classmethod
    def get_all_types(cls):
        """
        return an array of tuples containing id, kernel_type
        """
        return [(ktype.id, ktype.kernel_type) for ktype in cls.query]

    @classmethod
    def get_all_names(cls):
        return [ktype.kernel_type for ktype in cls.query]

    @classmethod
    def by_name(cls, kernel_type):
        try:
            return cls.query.filter_by(kernel_type=kernel_type).one()
        except NoResultFound:
            raise ValueError('No such kernel type %r' % kernel_type)

class Arch(DeclarativeMappedObject):

    __tablename__ = 'arch'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    arch = Column(String(20), unique=True)
    distro_trees = relationship('DistroTree', back_populates='arch')
    systems = relationship('System', secondary='system_arch_map', back_populates='arch')

    def __init__(self, arch=None):
        super(Arch, self).__init__()
        self.arch = arch

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.arch)

    def __unicode__(self):
        return self.arch

    def __str__(self):
        return unicode(self).encode('utf8')

    def __json__(self):
        return unicode(self)

    @classmethod
    def get_all(cls):
        return [(0,"All")] + [(arch.id, arch.arch) for arch in cls.query]

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, arch):
        try:
            return cls.query.filter_by(arch=arch).one()
        except NoResultFound:
            raise ValueError('No such arch %r' % arch)

    @classmethod
    def list_by_name(cls, name):
        """
        A class method that can be used to search arches
        based on the name
        """
        return cls.query.filter(Arch.arch.like('%s%%' % name))

class OSMajor(DeclarativeMappedObject):

    __tablename__ = 'osmajor'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    osmajor = Column(Unicode(255), unique=True)
    alias = Column(Unicode(25), unique=True)
    install_options_by_arch = relationship('OSMajorInstallOptions',
            collection_class=attribute_mapped_collection('arch'),
            back_populates='osmajor', cascade='all, delete-orphan')
    osversions = relationship('OSVersion', order_by='OSVersion.osminor',
            back_populates='osmajor')
    excluded_osmajors = relationship('ExcludeOSMajor', back_populates='osmajor')

    def __init__(self, osmajor):
        super(OSMajor, self).__init__()
        self.osmajor = osmajor

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, osmajor):
        return cls.query.filter_by(osmajor=osmajor).one()

    @classmethod
    def by_alias(cls, alias):
        return cls.query.filter_by(alias=alias).one()

    @classmethod
    def by_name_alias(cls, name_alias):
        return cls.query.filter(or_(OSMajor.osmajor==name_alias,
                                    OSMajor.alias==name_alias)).one()

    @classmethod
    def in_any_lab(cls, query=None):
        if query is None:
            query = cls.query
        return query.filter(exists([1], from_obj=
                LabControllerDistroTree.__table__
                    .join(DistroTree.__table__)
                    .join(Distro.__table__)
                    .join(OSVersion.__table__))
                .where(OSVersion.osmajor_id == OSMajor.id)
                .correlate(OSMajor.__table__))

    @classmethod
    def in_lab(cls, lab, query=None):
        if query is None:
            query = cls.query
        return query.filter(exists([1], from_obj=
                LabControllerDistroTree.__table__
                    .join(DistroTree.__table__)
                    .join(Distro.__table__)
                    .join(OSVersion.__table__))
                .where(OSVersion.osmajor_id == OSMajor.id)
                .where(LabControllerDistroTree.lab_controller == lab)
                .correlate(OSMajor.__table__))

    @classmethod
    def used_by_any_recipe(cls, query=None):
        # Delayed import to avoid circular dependency
        from . import Recipe
        if query is None:
            query = cls.query
        return query.filter(exists([1], from_obj=
                Recipe.__table__
                    .join(DistroTree.__table__)
                    .join(Distro.__table__)
                    .join(OSVersion.__table__))
                .where(OSVersion.osmajor_id == OSMajor.id)
                .correlate(OSMajor.__table__))

    @classmethod
    def ordered_by_osmajor(cls, query=None):
        if query is None:
            query = cls.query
        return sorted(query, key=cls._sort_key)

    def _sort_key(self):
        # Separate out the trailing digits, so that Fedora9 sorts before Fedora10
        name, version = split_osmajor_name_version(self.osmajor)
        if version == 'rawhide':
            version = 999
        elif version:
            version = int(version)
        return (name.lower(), version)

    @property
    def name(self):
        name, version = split_osmajor_name_version(self.osmajor)
        return name

    @property
    def number(self):
        """
        Numeric portion of the OS major, e.g. 18 for Fedora18.
        Note that this is not an int because it may be 'rawhide'!
        """
        # This property is called number to avoid confusion with OSVersion.
        name, version = split_osmajor_name_version(self.osmajor)
        return version

    @staticmethod
    def _validate_osmajor(osmajor):
        if not osmajor:
            raise ValueError('OSMajor cannot be empty')

    @validates('osmajor')
    def validate_osmajor(self, key, value):
        self._validate_osmajor(value)
        return value

    def __repr__(self):
        return '%s' % self.osmajor

    def arches(self):
        return Arch.query.distinct().join(DistroTree).join(Distro)\
                .join(OSVersion).filter(OSVersion.osmajor == self)


class OSMajorInstallOptions(DeclarativeMappedObject):

    __tablename__ = 'osmajor_install_options'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    osmajor_id = Column(Integer, ForeignKey('osmajor.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    osmajor = relationship(OSMajor, back_populates='install_options_by_arch')
    arch_id = Column(Integer, ForeignKey('arch.id'), nullable=True)
    arch = relationship(Arch)
    ks_meta = Column(String(1024))
    kernel_options = Column(String(1024))
    kernel_options_post = Column(String(1024))


class OSVersion(DeclarativeMappedObject):

    __tablename__ = 'osversion'
    __table_args__ = (
        UniqueConstraint('osmajor_id', 'osminor', name='osversion_uix_1'),
        {'mysql_engine': 'InnoDB'}
    )
    id = Column(Integer, autoincrement=True, primary_key=True)
    osmajor_id = Column(Integer, ForeignKey('osmajor.id'), index=True, nullable=False)
    osminor = Column(Unicode(255))
    osmajor = relationship(OSMajor, back_populates='osversions')
    arches = relationship(Arch, secondary=osversion_arch_map)
    distros = relationship('Distro', back_populates='osversion')
    excluded_osversions = relationship('ExcludeOSVersion', back_populates='osversion')

    @classmethod
    def lazy_create(cls, osmajor, osminor):
        return super(OSVersion, cls).lazy_create(osmajor_id=osmajor.id,
                osminor=osminor)

    def __init__(self, osmajor, osminor, arches=None):
        super(OSVersion, self).__init__()
        self.osmajor = osmajor
        self.osminor = osminor
        if arches:
            self.arches = arches
        else:
            self.arches = []

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, osmajor, osminor):
        return cls.query.filter_by(osmajor=osmajor, osminor=osminor).one()

    @classmethod
    def get_all(cls):
        all = cls.query
        return [(0,"All")] + [(version.id, version.osminor) for version in all]

    @classmethod
    def list_osmajor_by_name(cls,name,find_anywhere=False):
        if find_anywhere:
            q = cls.query.join('osmajor').filter(OSMajor.osmajor.like('%%%s%%' % name))
        else:
            q = cls.query.join('osmajor').filter(OSMajor.osmajor.like('%s%%' % name))
        return q


    def __repr__(self):
        return "%s.%s" % (self.osmajor,self.osminor)

    def add_arch(self, arch):
        """
        Adds the given arch to this OSVersion if it's not already present.
        """
        session.connection(self.__class__).execute(ConditionalInsert(
                osversion_arch_map,
                {osversion_arch_map.c.osversion_id: self.id,
                 osversion_arch_map.c.arch_id: arch.id}))


class LabControllerDistroTree(DeclarativeMappedObject):

    __tablename__ = 'distro_tree_lab_controller_map'
    __table_args__ = (
        UniqueConstraint('distro_tree_id', 'lab_controller_id', 'url'),
        {'mysql_engine': 'InnoDB'}
    )
    id = Column(Integer, autoincrement=True, primary_key=True)
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'), nullable=False)
    distro_tree = relationship('DistroTree', back_populates='lab_controller_assocs')
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id'), nullable=False)
    lab_controller = relationship(LabController, back_populates='_distro_trees')
    # 255 chars is probably not enough, but MySQL index limitations leave us no choice
    url = Column(Unicode(255), nullable=False)


class Distro(DeclarativeMappedObject, ActivityMixin):

    __tablename__ = 'distro'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(Unicode(255), nullable=False, unique=True)
    osversion_id = Column(Integer, ForeignKey('osversion.id'), nullable=False)
    osversion = relationship(OSVersion, back_populates='distros')
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    _tags = relationship('DistroTag', secondary=distro_tag_map, back_populates='distros')
    activity = relationship(DistroActivity, back_populates='object',
            order_by=[DistroActivity.created.desc(), DistroActivity.id.desc()])
    trees = relationship('DistroTree', back_populates='distro',
            order_by='[DistroTree.variant, DistroTree.arch_id]')
    dyn_trees = dynamic_loader('DistroTree')

    activity_type = DistroActivity

    @staticmethod
    def _validate_name(name):
        if not name:
            raise ValueError('Distro name cannot be empty')

    @validates('name')
    def validate_name(self, key, value):
        self._validate_name(value)
        return value

    @classmethod
    def lazy_create(cls, name, osversion):
        cls._validate_name(name)
        return super(Distro, cls).lazy_create(name=name,
                _extra_attrs=dict(osversion_id=osversion.id))

    @classmethod
    def by_name(cls, name):
        with convert_db_lookup_error('No such distro: %s' % name):
            return cls.query.filter_by(name=name).one()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf8')

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)

    def __json__(self):
        return {
            'id': self.id,
            'name': self.name,
        }

    @property
    def link(self):
        return make_link(url = '/distros/view?id=%s' % self.id,
                         text = self.name)

    def expire(self, service=u'XMLRPC'):
        for tree in self.trees:
            tree.expire(service=service)

    tags = association_proxy('_tags', 'tag',
            creator=lambda tag: DistroTag.lazy_create(tag=tag))

    def add_tag(self, tag):
        """
        Adds the given tag to this distro if it's not already present.
        """
        tagobj = DistroTag.lazy_create(tag=tag)
        session.connection(self.__class__).execute(ConditionalInsert(
                distro_tag_map,
                {distro_tag_map.c.distro_id: self.id,
                 distro_tag_map.c.distro_tag_id: tagobj.id}))

class DistroTree(DeclarativeMappedObject, ActivityMixin):

    __tablename__ = 'distro_tree'
    __table_args__ = (
        UniqueConstraint('distro_id', 'arch_id', 'variant'),
        {'mysql_engine': 'InnoDB'}
    )
    id = Column(Integer, autoincrement=True, primary_key=True)
    distro_id = Column('distro_id', Integer, ForeignKey('distro.id'), nullable=False)
    arch_id = Column('arch_id', Integer, ForeignKey('arch.id'), nullable=False)
    variant = Column('variant', Unicode(25))
    ks_meta = Column('ks_meta', UnicodeText)
    kernel_options = Column('kernel_options', UnicodeText)
    kernel_options_post = Column('kernel_options_post', UnicodeText)
    date_created = Column('date_created', DateTime, nullable=False, default=datetime.utcnow)
    distro = relationship(Distro, back_populates='trees')
    arch = relationship(Arch, back_populates='distro_trees')
    lab_controller_assocs = relationship(LabControllerDistroTree,
            back_populates='distro_tree', cascade='all, delete-orphan')
    activity = relationship(DistroTreeActivity, back_populates='object',
            order_by=[DistroTreeActivity.created.desc(), DistroTreeActivity.id.desc()])
    repos = relationship('DistroTreeRepo', back_populates='distro_tree',
            cascade='all, delete-orphan',
            order_by='[DistroTreeRepo.repo_type, DistroTreeRepo.repo_id]')
    images = relationship('DistroTreeImage', back_populates='distro_tree',
            cascade='all, delete-orphan')
    recipes = relationship('Recipe', back_populates='distro_tree', cascade_backrefs=False)

    activity_type = DistroTreeActivity

    @classmethod
    def lazy_create(cls, distro, variant, arch):
        return super(DistroTree, cls).lazy_create(distro_id=distro.id,
                variant=variant, arch_id=arch.id)

    @classmethod
    def by_filter(cls, filter):
        # Delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import apply_distro_filter
        # Limit to distro trees which exist in at least one lab
        query = cls.query.filter(DistroTree.lab_controller_assocs.any())
        query = apply_distro_filter(filter, query)
        return query.order_by(DistroTree.date_created.desc())

    def __json__(self):
        return {
            'id': self.id,
            'distro': self.distro,
            'variant': self.variant,
            'arch': self.arch,
        }

    def expire(self, lab_controller=None, service=u'XMLRPC'):
        """ Expire this tree """
        for lca in list(self.lab_controller_assocs):
            if not lab_controller or lca.lab_controller == lab_controller:
                self.lab_controller_assocs.remove(lca)
                self.activity.append(DistroTreeActivity(
                    user=identity.current.user, service=service,
                    action=u'Removed', field_name=u'lab_controller_assocs',
                    old_value=u'%s %s' % (lca.lab_controller, lca.url),
                    new_value=None))

    def to_xml(self, clone=False):
        """ Return xml describing this distro """
        fields = dict(
            distro_name=['distro', 'name'],
            distro_arch=['arch', 'arch'],
            distro_variant='variant',
            distro_family=['distro', 'osversion', 'osmajor', 'osmajor'],
        )

        distro_requires = lxml.etree.Element('distroRequires')
        xmland = lxml.etree.Element('and')
        for key in fields.keys():
            require = lxml.etree.Element(key)
            require.set('op', '=')
            if isinstance(fields[key], list):
                obj = self
                for field in fields[key]:
                    obj = getattr(obj, field, None)
                require.set('value', obj or '')
            else:
                value_text = getattr(self, fields[key], None) or ''
                require.set('value', str(value_text))
            xmland.append(require)
        distro_requires.append(xmland)
        return distro_requires

    @property
    def link(self):
        return make_link(url='/distrotrees/%s' % self.id, text=unicode(self))

    def __unicode__(self):
        if self.variant:
            return u'%s %s %s' % (self.distro, self.variant, self.arch)
        else:
            return u'%s %s' % (self.distro, self.arch)

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return '%s(distro=%r, variant=%r, arch=%r)' % (
                self.__class__.__name__, self.distro, self.variant, self.arch)

    def url_in_lab(self, lab_controller, scheme=None, required=False):
        """
        Returns an absolute URL for this distro tree in the given lab.

        If *scheme* is a string, the URL returned will use that scheme. Callers
        can also pass a list of allowed schemes in order of preference; the URL
        returned will use one of them. If *scheme* is None or absent, any
        scheme will be used.

        If the *required* argument is false or absent, then None will be
        returned if this distro tree is not in the given lab. If *required* is
        true, then an exception will be raised.
        """
        if isinstance(scheme, basestring):
            scheme = [scheme]
        urls = dict((urlparse.urlparse(lca.url).scheme, lca.url)
                for lca in self.lab_controller_assocs
                if lca.lab_controller.fqdn == lab_controller.fqdn)
        if scheme is not None:
            for s in scheme:
                if s in urls:
                    return urls[s]
        else:
            for s in ['nfs', 'http', 'ftp']:
                if s in urls:
                    return urls[s]
            # caller didn't specify any schemes, so pick anything if we have it
            if urls:
                return urls.itervalues().next()
        # nothing suitable found
        if required:
            raise ValueError('No usable URL found for %r in %r' % (self, lab_controller))
        else:
            return None

    def repo_by_id(self, repoid):
        for repo in self.repos:
            if repo.repo_id == repoid:
                return repo

    def image_by_type(self, image_type, kernel_type):
        for image in self.images:
            if image.image_type == image_type and \
               image.kernel_type == kernel_type:
                return image

    def install_options(self):
        return InstallOptions.from_strings(self.ks_meta,
                self.kernel_options, self.kernel_options_post)

    def create_installation_from_tree(self):
        # delayed import to avoid circular dependency
        from bkr.server.model.installation import Installation
        installation = Installation()
        installation.distro_tree = self
        installation.arch = self.arch
        installation.distro_name = self.distro.name
        installation.osmajor = self.distro.osversion.osmajor.osmajor
        installation.osminor = self.distro.osversion.osminor
        installation.variant = self.variant
        return installation

class DistroTreeRepo(DeclarativeMappedObject):

    __tablename__ = 'distro_tree_repo'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'), primary_key=True)
    repo_id = Column(Unicode(255), nullable=False, primary_key=True)
    repo_type = Column(Unicode(255), index=True)
    path = Column(UnicodeText, nullable=False)
    distro_tree = relationship(DistroTree, back_populates='repos')

    @classmethod
    def lazy_create(cls, distro_tree, repo_id, repo_type, path):
        return super(DistroTreeRepo, cls).lazy_create(
                distro_tree_id=distro_tree.id,
                repo_id=repo_id,
                _extra_attrs=dict(repo_type=repo_type, path=path))

class DistroTreeImage(DeclarativeMappedObject):

    __tablename__ = 'distro_tree_image'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'), primary_key=True)
    distro_tree = relationship(DistroTree, back_populates='images')
    image_type = Column(ImageType.db_type(), nullable=False, primary_key=True)
    kernel_type_id = Column(Integer, ForeignKey('kernel_type.id'),
            default=select([KernelType.id], limit=1).where(KernelType.kernel_type == u'default').correlate(None),
            nullable=False, primary_key=True)
    kernel_type = relationship(KernelType)
    path = Column(UnicodeText, nullable=False)

    @classmethod
    def lazy_create(cls, distro_tree, image_type, kernel_type, path):
        return super(DistroTreeImage, cls).lazy_create(
                distro_tree_id=distro_tree.id,
                image_type=image_type, kernel_type_id=kernel_type.id,
                _extra_attrs=dict(path=path))

class DistroTag(DeclarativeMappedObject):

    __tablename__ = 'distro_tag'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    tag = Column(Unicode(255), unique=True)
    distros = relationship(Distro, secondary=distro_tag_map, back_populates='_tags')

    def __init__(self, tag=None):
        super(DistroTag, self).__init__()
        self.tag = tag

    def __repr__(self):
        return "%s" % self.tag

    @classmethod
    def by_tag(cls, tag):
        """
        A class method to lookup tags
        """
        return cls.query.filter(DistroTag.tag == tag).one()

    @classmethod
    def list_by_tag(cls, tag):
        """
        A class method that can be used to search tags
        """
        return cls.query.filter(DistroTag.tag.like('%s%%' % tag))

    @classmethod
    def used(cls, query=None):
        if query is None:
            query = cls.query
        return query.filter(DistroTag.distros.any())
