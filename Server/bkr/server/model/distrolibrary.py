
import re
from datetime import datetime
import urlparse
import xml.dom.minidom
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Integer,
        String, Unicode, DateTime, UnicodeText, Boolean)
from sqlalchemy.sql import select, exists, and_, or_, not_
from sqlalchemy.orm import relationship, backref, dynamic_loader
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.database import session
from bkr.server import identity
from bkr.server.helpers import make_link
from bkr.server.installopts import InstallOptions
from .sql import ConditionalInsert
from .base import DeclarativeMappedObject
from .types import ImageType
from .activity import Activity
from .lab import LabController

xmldoc = xml.dom.minidom.Document()

osversion_arch_map = Table('osversion_arch_map', DeclarativeMappedObject.metadata,
    Column('osversion_id', Integer,
           ForeignKey('osversion.id'),
           primary_key=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True),
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
    distro_id = Column(Integer, ForeignKey('distro.id'))
    __mapper_args__ = {'polymorphic_identity': u'distro_activity'}

    def object_name(self):
        return "Distro: %s" % self.object.name

class DistroTreeActivity(Activity):

    __tablename__ = 'distro_tree_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'))
    __mapper_args__ = {'polymorphic_identity': u'distro_tree_activity'}

    def object_name(self):
        return u'DistroTree: %s' % self.object

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
            backref='osmajor', cascade='all, delete-orphan')

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
        name, version = re.match(r'(.*?)(\d*)$', self.osmajor.lower()).groups()
        if version:
            version = int(version)
        return (name, version)

    def tasks(self):
        """
        List of tasks that support this OSMajor
        """
        # Delayed import to avoid circular dependency
        from . import Task, TaskExcludeOSMajor
        return Task.query.filter(
                not_(
                     Task.id.in_(select([Task.id]).
                 where(Task.id==TaskExcludeOSMajor.task_id).
                 where(TaskExcludeOSMajor.osmajor_id==OSMajor.id).
                 where(OSMajor.id==self.id)
                                ),
                    )
        )

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
    osmajor_id = Column(Integer, ForeignKey('osmajor.id'))
    osminor = Column(Unicode(255))
    osmajor = relationship(OSMajor, backref=backref('osversion', order_by=[osminor]))
    arches = relationship(Arch, secondary=osversion_arch_map)

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
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id'), nullable=False)
    lab_controller = relationship(LabController,
            backref=backref('_distro_trees', cascade='all, delete-orphan'))
    # 255 chars is probably not enough, but MySQL index limitations leave us no choice
    url = Column(Unicode(255), nullable=False)


class Distro(DeclarativeMappedObject):

    __tablename__ = 'distro'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(Unicode(255), nullable=False, unique=True)
    osversion_id = Column(Integer, ForeignKey('osversion.id'), nullable=False)
    osversion = relationship(OSVersion, backref='distros')
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    _tags = relationship('DistroTag', secondary=distro_tag_map, backref='distros')
    activity = relationship(DistroActivity, backref='object',
            order_by=[DistroActivity.created.desc(), DistroActivity.id.desc()])
    dyn_trees = dynamic_loader('DistroTree')

    @classmethod
    def lazy_create(cls, name, osversion):
        return super(Distro, cls).lazy_create(name=name,
                _extra_attrs=dict(osversion_id=osversion.id))

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf8')

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)

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

class DistroTree(DeclarativeMappedObject):

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
    distro = relationship(Distro, backref=backref('trees', order_by=[variant, arch_id]))
    arch = relationship(Arch, backref='distro_trees')
    lab_controller_assocs = relationship(LabControllerDistroTree,
            backref='distro_tree', cascade='all, delete-orphan')
    activity = relationship(DistroTreeActivity, backref='object',
            order_by=[DistroTreeActivity.created.desc(), DistroTreeActivity.id.desc()])

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
                      distro_name    = ['distro', 'name'],
                      distro_arch    = ['arch','arch'],
                      distro_variant = 'variant',
                      distro_family  = ['distro', 'osversion','osmajor','osmajor'],
                     )

        distro_requires = xmldoc.createElement('distroRequires')
        xmland = xmldoc.createElement('and')
        for key in fields.keys():
            require = xmldoc.createElement(key)
            require.setAttribute('op', '=')
            if isinstance(fields[key], list):
                obj = self
                for field in fields[key]:
                    obj = getattr(obj, field, None)
                require.setAttribute('value', obj or '')
            else:
                value_text = getattr(self,fields[key],None) or ''
                require.setAttribute('value', str(value_text))
            xmland.appendChild(require)
        distro_requires.appendChild(xmland)
        return distro_requires

    def systems_filter(self, user, filter, only_in_lab=False):
        # Delayed import to avoid circular dependency
        from . import System
        from bkr.server.needpropertyxml import apply_system_filter
        systems = System.query
        systems = apply_system_filter(filter, systems)
        systems = self.all_systems(user, systems)
        if only_in_lab:
            systems = systems.join(System.lab_controller)\
                    .filter(LabController._distro_trees.any(
                    LabControllerDistroTree.distro_tree == self))
        return systems

    def tasks(self):
        """
        List of tasks that support this distro
        """
        # Delayed import to avoid circular dependency
        from . import Task, TaskExcludeArch, TaskExcludeOSMajor
        return Task.query\
                .filter(not_(Task.excluded_arch.any(
                    TaskExcludeArch.arch == self.arch)))\
                .filter(not_(Task.excluded_osmajor.any(
                    TaskExcludeOSMajor.osmajor == self.distro.osversion.osmajor)))

    def systems(self, user=None, systems=None):
        """
        List of systems that support this distro
        Limit to only lab controllers which have the distro.
        Limit to what is available to user if user passed in.
        """
        # Delayed import to avoid circular dependency
        from . import System
        return self.all_systems(user=user, systems=systems)\
                .join(System.lab_controller)\
                .filter(LabController._distro_trees.any(
                    LabControllerDistroTree.distro_tree == self))

    def all_systems(self, user=None, systems=None):
        """
        List of systems that support this distro tree.
        Will return all possible systems even if the tree is not on the lab controller yet.
        Limit to what is available to user if user passed in.
        """
        # Delayed import to avoid circular dependency
        from . import System, ExcludeOSMajor, ExcludeOSVersion
        if user:
            systems = System.available_for_schedule(user, systems=systems)
            systems = System.scheduler_ordering(user, query=systems)
        elif not systems:
            systems = System.query

        return systems.filter(and_(
                System.arch.contains(self.arch),
                not_(System.excluded_osmajor.any(and_(
                        ExcludeOSMajor.osmajor == self.distro.osversion.osmajor,
                        ExcludeOSMajor.arch == self.arch))),
                not_(System.excluded_osversion.any(and_(
                        ExcludeOSVersion.osversion == self.distro.osversion,
                        ExcludeOSVersion.arch == self.arch))),
                ))

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
                if lca.lab_controller == lab_controller)
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

class DistroTreeRepo(DeclarativeMappedObject):

    __tablename__ = 'distro_tree_repo'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'), primary_key=True)
    repo_id = Column(Unicode(255), nullable=False, primary_key=True)
    repo_type = Column(Unicode(255), index=True)
    path = Column(UnicodeText, nullable=False)
    distro_tree = relationship(DistroTree, backref=backref('repos',
            cascade='all, delete-orphan', order_by=[repo_type, repo_id]))

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
    distro_tree = relationship(DistroTree,
            backref=backref('images', cascade='all, delete-orphan'))
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
