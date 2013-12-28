
import re
from datetime import datetime
import urlparse
import xml.dom.minidom
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Integer,
        String, Unicode, DateTime, UnicodeText, Boolean)
from sqlalchemy.sql import select, exists, and_, or_, not_
from sqlalchemy.orm import mapper, relation, backref, dynamic_loader
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.database import session, metadata
from bkr.server import identity
from bkr.server.helpers import make_link
from bkr.server.installopts import InstallOptions
from .sql import ConditionalInsert
from .base import MappedObject
from .types import ImageType
from .activity import Activity, activity_table
from .lab import LabController

xmldoc = xml.dom.minidom.Document()

kernel_type_table = Table('kernel_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('kernel_type', Unicode(100), nullable=False),
    Column('uboot', Boolean(), default=False),
    mysql_engine='InnoDB',
)

arch_table = Table('arch', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('arch', String(20), unique=True),
    mysql_engine='InnoDB',
)

osversion_arch_map = Table('osversion_arch_map', metadata,
    Column('osversion_id', Integer,
           ForeignKey('osversion.id'),
           primary_key=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True),
    mysql_engine='InnoDB',
)

distro_table = Table('distro', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('name', Unicode(255), nullable=False, unique=True),
    Column('osversion_id', Integer, ForeignKey('osversion.id'), nullable=False),
    Column('date_created', DateTime, nullable=False, default=datetime.utcnow),
    mysql_engine='InnoDB',
)

distro_tree_table = Table('distro_tree', metadata,
    Column('id', Integer, autoincrement=True,
            nullable=False, primary_key=True),
    Column('distro_id', Integer, ForeignKey('distro.id'), nullable=False),
    Column('arch_id', Integer, ForeignKey('arch.id'), nullable=False),
    Column('variant', Unicode(25)),
    Column('ks_meta', UnicodeText),
    Column('kernel_options', UnicodeText),
    Column('kernel_options_post', UnicodeText),
    Column('date_created', DateTime, nullable=False, default=datetime.utcnow),
    UniqueConstraint('distro_id', 'arch_id', 'variant'),
    mysql_engine='InnoDB',
)

distro_tree_repo_table = Table('distro_tree_repo', metadata,
    Column('distro_tree_id', Integer, ForeignKey('distro_tree.id'),
            nullable=False, primary_key=True),
    Column('repo_id', Unicode(255), nullable=False, primary_key=True),
    Column('repo_type', Unicode(255), index=True),
    Column('path', UnicodeText, nullable=False),
    mysql_engine='InnoDB',
)

distro_tree_image_table = Table('distro_tree_image', metadata,
    Column('distro_tree_id', Integer, ForeignKey('distro_tree.id'),
            nullable=False, primary_key=True),
    Column('image_type', ImageType.db_type(),
            nullable=False, primary_key=True),
    Column('kernel_type_id', Integer,
           ForeignKey('kernel_type.id'),
           default=select([kernel_type_table.c.id], limit=1).where(kernel_type_table.c.kernel_type==u'default').correlate(None),
           nullable=False, primary_key=True),
    Column('path', UnicodeText, nullable=False),
    mysql_engine='InnoDB',
)

distro_tree_lab_controller_map = Table('distro_tree_lab_controller_map', metadata,
    Column('id', Integer, autoincrement=True,
            nullable=False, primary_key=True),
    Column('distro_tree_id', Integer, ForeignKey('distro_tree.id'),
            nullable=False),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id'),
            nullable=False),
    # 255 chars is probably not enough, but MySQL index limitations leave us no choice
    Column('url', Unicode(255), nullable=False),
    UniqueConstraint('distro_tree_id', 'lab_controller_id', 'url'),
    mysql_engine='InnoDB',
)

osmajor_table = Table('osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor', Unicode(255), unique=True),
    Column('alias', Unicode(25), unique=True),
    mysql_engine='InnoDB',
)

osmajor_install_options_table = Table('osmajor_install_options', metadata,
    Column('id', Integer, autoincrement=True,
        nullable=False, primary_key=True),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id',
        onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('arch_id', Integer, ForeignKey('arch.id'), nullable=True),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
    mysql_engine='InnoDB',
)

osversion_table = Table('osversion', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    Column('osminor',Unicode(255)),
    UniqueConstraint('osmajor_id', 'osminor', name='osversion_uix_1'),
    mysql_engine='InnoDB',
)

distro_tag_table = Table('distro_tag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('tag', Unicode(255), unique=True),
    mysql_engine='InnoDB',
)

distro_tag_map = Table('distro_tag_map', metadata,
    Column('distro_id', Integer, ForeignKey('distro.id'),
                                         primary_key=True),
    Column('distro_tag_id', Integer, ForeignKey('distro_tag.id'),
                                         primary_key=True),
    mysql_engine='InnoDB',
)

distro_activity_table = Table('distro_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('distro_id', Integer, ForeignKey('distro.id')),
    mysql_engine='InnoDB',
)

distro_tree_activity_table = Table('distro_tree_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('distro_tree_id', Integer, ForeignKey('distro_tree.id')),
    mysql_engine='InnoDB',
)

class KernelType(MappedObject):

    def __repr__(self):
        return self.kernel_type

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
        return cls.query.filter_by(kernel_type=kernel_type).one()

class Arch(MappedObject):
    def __init__(self, arch=None):
        super(Arch, self).__init__()
        self.arch = arch

    def __repr__(self):
        return '%s' % self.arch

    @classmethod
    def get_all(cls):
        return [(0,"All")] + [(arch.id, arch.arch) for arch in cls.query]

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
        return cls.query.filter(Arch.arch.like('%s%%' % name))

class OSMajor(MappedObject):
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
                distro_tree_lab_controller_map
                    .join(distro_tree_table)
                    .join(distro_table)
                    .join(osversion_table))
                .where(OSVersion.osmajor_id == OSMajor.id)
                .correlate(osmajor_table))

    @classmethod
    def used_by_any_recipe(cls, query=None):
        # Delayed import to avoid circular dependency
        from . import recipe_table
        if query is None:
            query = cls.query
        return query.filter(exists([1], from_obj=
                recipe_table
                    .join(distro_tree_table)
                    .join(distro_table)
                    .join(osversion_table))
                .where(OSVersion.osmajor_id == OSMajor.id)
                .correlate(osmajor_table))

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
        from . import Task, task_table, task_exclude_osmajor_table
        return Task.query.filter(
                not_(
                     Task.id.in_(select([task_table.c.id]).
                 where(task_table.c.id==task_exclude_osmajor_table.c.task_id).
                 where(task_exclude_osmajor_table.c.osmajor_id==osmajor_table.c.id).
                 where(osmajor_table.c.id==self.id)
                                ),
                    )
        )

    def __repr__(self):
        return '%s' % self.osmajor

    def arches(self):
        return Arch.query.distinct().join(DistroTree).join(Distro)\
                .join(OSVersion).filter(OSVersion.osmajor == self)


class OSMajorInstallOptions(MappedObject): pass


class OSVersion(MappedObject):

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


class LabControllerDistroTree(MappedObject):
    pass


class Distro(MappedObject):

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

class DistroTree(MappedObject):

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

    def systems(self, user=None):
        """
        List of systems that support this distro
        Limit to only lab controllers which have the distro.
        Limit to what is available to user if user passed in.
        """
        # Delayed import to avoid circular dependency
        from . import System
        return self.all_systems(user).join(System.lab_controller)\
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

class DistroTreeRepo(MappedObject):

    @classmethod
    def lazy_create(cls, distro_tree, repo_id, repo_type, path):
        return super(DistroTreeRepo, cls).lazy_create(
                distro_tree_id=distro_tree.id,
                repo_id=repo_id,
                _extra_attrs=dict(repo_type=repo_type, path=path))

class DistroTreeImage(MappedObject):

    @classmethod
    def lazy_create(cls, distro_tree, image_type, kernel_type, path):
        return super(DistroTreeImage, cls).lazy_create(
                distro_tree_id=distro_tree.id,
                image_type=image_type, kernel_type_id=kernel_type.id,
                _extra_attrs=dict(path=path))

class DistroTag(MappedObject):
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

class DistroActivity(Activity):
    def object_name(self):
        return "Distro: %s" % self.object.name

class DistroTreeActivity(Activity):
    def object_name(self):
        return u'DistroTree: %s' % self.object

KernelType.mapper = mapper(KernelType, kernel_type_table)
mapper(Arch, arch_table)
mapper(OSVersion, osversion_table,
       properties = {'osmajor':relation(OSMajor, uselist=False,
                                        backref='osversion'),
                     'arches':relation(Arch,secondary=osversion_arch_map),
                    }
      )
mapper(OSMajor, osmajor_table, properties={
    'osminor': relation(OSVersion, order_by=[osversion_table.c.osminor]),
    'install_options_by_arch': relation(OSMajorInstallOptions,
        collection_class=attribute_mapped_collection('arch'),
        backref='osmajor', cascade='all, delete-orphan'),
})
mapper(OSMajorInstallOptions, osmajor_install_options_table, properties={
    'arch': relation(Arch),
})
mapper(LabControllerDistroTree, distro_tree_lab_controller_map, properties={
    'lab_controller': relation(LabController,
        backref=backref('_distro_trees', cascade='all, delete-orphan')),
})
mapper(Distro, distro_table,
        properties = {'osversion':relation(OSVersion, uselist=False,
                                           backref='distros'),
                      '_tags':relation(DistroTag,
                                       secondary=distro_tag_map,
                                       backref='distros'),
                      'activity': relation(DistroActivity,
                        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                        backref='object',),
                      'dyn_trees': dynamic_loader(DistroTree),
    })
mapper(DistroTag, distro_tag_table)
mapper(DistroTree, distro_tree_table, properties={
    'distro': relation(Distro, backref=backref('trees',
        order_by=[distro_tree_table.c.variant, distro_tree_table.c.arch_id])),
    'arch': relation(Arch, backref='distro_trees'),
    'lab_controller_assocs': relation(LabControllerDistroTree,
        backref='distro_tree', cascade='all, delete-orphan'),
    'activity': relation(DistroTreeActivity, backref='object',
        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()]),
})
mapper(DistroTreeRepo, distro_tree_repo_table, properties={
    'distro_tree': relation(DistroTree, backref=backref('repos',
        cascade='all, delete-orphan',
        order_by=[distro_tree_repo_table.c.repo_type, distro_tree_repo_table.c.repo_id])),
})
mapper(DistroTreeImage, distro_tree_image_table, properties={
    'distro_tree': relation(DistroTree, backref=backref('images',
        cascade='all, delete-orphan')),
    'kernel_type':relation(KernelType, uselist=False),
})
mapper(DistroActivity, distro_activity_table, inherits=Activity,
       polymorphic_identity=u'distro_activity')
mapper(DistroTreeActivity, distro_tree_activity_table, inherits=Activity,
       polymorphic_identity=u'distro_tree_activity')
