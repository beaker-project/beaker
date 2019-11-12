
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os.path
from datetime import datetime
import subprocess
import shutil
import logging
import rpm
import lxml.etree
from sqlalchemy import (Table, Column, ForeignKey, Integer, Unicode, Boolean,
                        DateTime)
from sqlalchemy.sql.expression import and_, or_, not_, true
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import relationship
from turbogears.config import get
from turbogears.database import session
from bkr.common.helpers import (AtomicFileReplacement, Flock,
                                makedirs_ignore, unlink_ignore)
from bkr.server import identity, testinfo
from bkr.server.bexceptions import BX
from bkr.server.hybrid import hybrid_method
from bkr.server.util import absolute_url, run_createrepo, convert_db_lookup_error
from .base import DeclarativeMappedObject
from .identity import User
from .distrolibrary import Arch, OSMajor

log = logging.getLogger(__name__)

class TaskPackage(DeclarativeMappedObject):
    """
    A list of packages that a tasks should be run for.
    """

    __tablename__ = 'task_package'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_collate': 'utf8_bin'}
    id = Column(Integer, primary_key=True)
    package = Column(Unicode(255), nullable=False, unique=True)
    tasks = relationship('Task', secondary='task_packages_runfor_map',
            back_populates='runfor')

    @classmethod
    def by_name(cls, package):
        return cls.query.filter_by(package=package).one()

    def __repr__(self):
        return self.package

    def to_xml(self):
        package = lxml.etree.Element("package")
        package.set("name", "%s" % self.package)
        return package

task_packages_runfor_map = Table('task_packages_runfor_map', DeclarativeMappedObject.metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

task_packages_required_map = Table('task_packages_required_map', DeclarativeMappedObject.metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

task_type_map = Table('task_type_map', DeclarativeMappedObject.metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('task_type_id', Integer, ForeignKey('task_type.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

# Helper for manipulating the task library

class TaskLibrary(object):

    @property
    def rpmspath(self):
        # Lazy lookup so module can be imported prior to configuration
        return get("basepath.rpms")

    def get_rpm_path(self, rpm_name):
        return os.path.join(self.rpmspath, rpm_name)

    def _unlink_locked_rpms(self, rpm_names):
        # Internal call that assumes the flock is already held
        for rpm_name in rpm_names:
            unlink_ignore(self.get_rpm_path(rpm_name))

    def _unlink_locked_rpm(self, rpm_name):
        # Internal call that assumes the flock is already held
        self._unlink_locked_rpms([rpm_name])

    def unlink_rpm(self, rpm_name):
        """
        Ensures an RPM is no longer present in the task library
        """
        with Flock(self.rpmspath):
            self._unlink_locked_rpm(rpm_name)

    def _update_locked_repo(self):
        # Internal call that assumes the flock is already held
        # If the createrepo command crashes for some reason it may leave behind
        # its work directories. createrepo_c refuses to run if .repodata exists.
        workdirs = [os.path.join(self.rpmspath, dirname) for dirname in
                ['.repodata', '.olddata']]
        for workdir in workdirs:
            if os.path.exists(workdir):
                log.warn('Removing stale createrepo directory %s', workdir)
                shutil.rmtree(workdir, ignore_errors=True)
        # Removed --baseurl, if upgrading you will need to manually
        # delete repodata directory before this will work correctly.
        command, returncode, out, err = run_createrepo(
                cwd=self.rpmspath, update=True)
        if out:
            log.debug("stdout from %s: %s", command, out)
        if err:
            log.warn("stderr from %s: %s", command, err)
        if returncode != 0:
            if returncode < 0:
                msg = '%s killed with signal %s' % (command, -returncode)
            else:
                msg = '%s failed with exit status %s' % (command, returncode)
            if err:
                msg = '%s\n%s' % (msg, err)
            raise RuntimeError(msg)

    def update_repo(self):
        """Update the task library yum repo metadata"""
        with Flock(self.rpmspath):
            self._update_locked_repo()

    def _all_rpms(self):
        """Iterator over the task RPMs currently on disk"""
        basepath = self.rpmspath
        for name in os.listdir(basepath):
            if not name.endswith("rpm"):
                continue
            srcpath = os.path.join(basepath, name)
            if os.path.isdir(srcpath):
                continue
            yield srcpath, name

    def _link_rpms(self, dst):
        """Hardlink the task rpms into dst"""
        makedirs_ignore(dst, 0755)
        for srcpath, name in self._all_rpms():
            dstpath = os.path.join(dst, name)
            unlink_ignore(dstpath)
            os.link(srcpath, dstpath)

    def make_snapshot_repo(self, repo_dir):
        """Create a snapshot of the current state of the task library"""
        # This should only run if we are missing repodata in the rpms path
        # since this should normally be updated when new tasks are uploaded
        src_meta = os.path.join(self.rpmspath, 'repodata')
        if not os.path.isdir(src_meta):
            log.info("Task library repodata missing, generating...")
            self.update_repo()
        dst_meta = os.path.join(repo_dir, 'repodata')
        if os.path.isdir(dst_meta):
            log.info("Destination repodata already exists, skipping snapshot")
        else:
            # Copy updated repo to recipe specific repo
            log.debug("Generating task library snapshot")
            with Flock(self.rpmspath):
                self._link_rpms(repo_dir)
                shutil.copytree(src_meta, dst_meta)

    def update_task(self, rpm_name, write_rpm):
        tasks = self.update_tasks([(rpm_name, write_rpm)])
        return tasks[0]

    def update_tasks(self, rpm_names_write_rpm):
        """Updates the the task rpm library

           rpm_names_write_rpm is a list of two element tuples,
           where the first element is the name of the rpm to be written, and
           the second element is callable that takes a file object as its
           only arg and writes to that file object.


           write_rpm must be a callable that takes a file object as its
           sole argument and populates it with the raw task RPM contents

           Expects to be called in a transaction, and for that transaction
           to be rolled back if an exception is thrown.
        """
        # XXX (ncoghlan): How do we get rid of that assumption about the
        # transaction handling? Assuming we're *not* already in a transaction
        # won't work either.

        to_sync = []
        try:
            for rpm_name, write_rpm in rpm_names_write_rpm:
                rpm_path = self.get_rpm_path(rpm_name)
                upgrade = AtomicFileReplacement(rpm_path)
                to_sync.append((rpm_name, upgrade,))
                f = upgrade.create_temp()
                write_rpm(f)
                f.flush()
        except Exception, e:
            log.error('Error: Failed to copy task %s, aborting.' % rpm_name)
            for __, atomic_file in to_sync:
                atomic_file.destroy_temp()
            raise

        old_rpms = []
        new_tasks = []


        try:
            with Flock(self.rpmspath):
                for rpm_name, atomic_file in to_sync:
                    f = atomic_file.temp_file
                    f.seek(0)
                    task, downgrade = Task.create_from_taskinfo(self.read_taskinfo(f))
                    old_rpm_name = task.rpm
                    task.rpm = rpm_name
                    if old_rpm_name:
                        old_rpms.append(old_rpm_name)
                    atomic_file.replace_dest()
                    new_tasks.append(task)
                    session.add(task)
                    session.flush()

                try:
                    self._update_locked_repo()
                except:
                    # We assume the current transaction is going to be rolled back,
                    # so the Task possibly defined above, or changes to an existing
                    # task, will never by written to the database (even if it was
                    # the _update_locked_repo() call that failed).
                    # Accordingly, we also throw away the newly created RPMs.
                    log.error('Failed to update task library repo, aborting')
                    self._unlink_locked_rpms([task.rpm for task in new_tasks])
                    raise
                # Since it existed when we called _update_locked_repo()
                # metadata, albeit not as the latest version.
                # However, it's too expensive (several seconds of IO
                # with the task repo locked) to do it twice for every
                # task update, so we rely on the fact that tasks are
                # referenced by name rather than requesting specific
                # versions, and thus will always grab the latest.
                self._unlink_locked_rpms(old_rpms)
                # if this is a downgrade, we run createrepo once more
                # so that the metadata doesn't contain the record for the
                # now unlinked newer version of the task
                if downgrade:
                    self._update_locked_repo()

        finally:
            # Some or all of these may have already been destroyed
            for __, atomic_file in to_sync:
                atomic_file.destroy_temp()
        return new_tasks

    def get_rpm_info(self, fd):
        """Returns rpm information by querying a rpm"""
        ts = rpm.ts()
        fd.seek(0)
        try:
            hdr = ts.hdrFromFdno(fd.fileno())
        except rpm.error:
            ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
            fd.seek(0)
            hdr = ts.hdrFromFdno(fd.fileno())
        return { 'name': hdr[rpm.RPMTAG_NAME],
                    'ver' : "%s-%s" % (hdr[rpm.RPMTAG_VERSION],
                                    hdr[rpm.RPMTAG_RELEASE]),
                    'epoch': hdr[rpm.RPMTAG_EPOCH],
                    'arch': hdr[rpm.RPMTAG_ARCH] ,
                    'files': hdr['filenames']}

    def read_taskinfo(self, fd):
        """Retrieve Beaker task details from an RPM"""
        taskinfo = dict(desc = '',
                        hdr  = '',
                        )
        taskinfo['hdr'] = self.get_rpm_info(fd)
        taskinfo_file = None
        for file in taskinfo['hdr']['files']: #pylint: disable=invalid-sequence-index
            if file.endswith('testinfo.desc'):
                taskinfo_file = file
        if taskinfo_file:
            fd.seek(0)
            p1 = subprocess.Popen(["rpm2cpio"],
                                  stdin=fd.fileno(), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            p2 = subprocess.Popen(["cpio", "--quiet", "--extract",
                                   "--to-stdout", ".%s" % taskinfo_file],
                                  stdin=p1.stdout, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            taskinfo['desc'] = p2.communicate()[0]
        return taskinfo


class Task(DeclarativeMappedObject):
    """
    Tasks that are available to schedule
    """

    __tablename__ = 'task'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column('name', Unicode(255), nullable=False, unique=True)
    rpm = Column('rpm', Unicode(255), nullable=False, unique=True)
    path = Column('path', Unicode(4096), nullable=False)
    description = Column('description', Unicode(2048), nullable=False)
    avg_time = Column(Integer, nullable=False, default=0)
    destructive = Column(Boolean(create_constraint=False))
    nda = Column(Boolean(create_constraint=False))
    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    update_date = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    # uploader may be NULL on old tasks uploaded before Beaker tracked this
    uploader_id = Column(Integer, ForeignKey('tg_user.user_id'))
    uploader = relationship(User, back_populates='tasks')
    owner = Column(Unicode(255), index=True, nullable=False)
    version = Column(Unicode(256), nullable=False)
    license = Column(Unicode(256), nullable=False)
    priority = Column(Unicode(256))
    valid = Column(Boolean, default=True, nullable=False)
    types = relationship('TaskType', secondary=task_type_map, back_populates='tasks')
    excluded_osmajors = relationship('OSMajor', secondary='task_exclude_osmajor')
    exclusive_osmajors = relationship('OSMajor', secondary='task_exclusive_osmajor')
    excluded_arches = relationship('Arch', secondary='task_exclude_arch')
    exclusive_arches = relationship('Arch', secondary='task_exclusive_arch')
    runfor = relationship(TaskPackage, secondary=task_packages_runfor_map,
            back_populates='tasks')
    required = relationship(TaskPackage, secondary=task_packages_required_map,
            order_by=[TaskPackage.package])
    needs = relationship('TaskPropertyNeeded')
    bugzillas = relationship('TaskBugzilla', back_populates='task',
            cascade='all, delete-orphan')

    library = TaskLibrary()

    @classmethod
    def exists_by_name(cls, name, valid=None):
        query = cls.query.filter(Task.name == name)
        if valid is not None:
            query = query.filter(Task.valid == bool(valid))
        return query.count() > 0

    @classmethod
    def by_name(cls, name, valid=None):
        with convert_db_lookup_error('No such task: %s' % name):
            query = cls.query.filter(cls.name == name)
            if valid is not None:
                query = query.filter(Task.valid==bool(valid))
            return query.one()

    @classmethod
    def by_id(cls, id, valid=None):
        with convert_db_lookup_error('No such task with ID: %s' % id):
            query = cls.query.filter(Task.id==id)
            if valid is not None:
                query = query.filter(Task.valid==bool(valid))
            return query.one()

    @classmethod
    def by_type(cls, type, query=None):
        if not query:
            query=cls.query
        return query.join('types').filter(TaskType.type==type)

    @classmethod
    def by_package(cls, package, query=None):
        if not query:
            query=cls.query
        return query.join('runfor').filter(TaskPackage.package==package)

    @classmethod
    def compatible_with_distro(cls, distro):
        return cls.compatible_with_osmajor(distro.osversion.osmajor)

    @classmethod
    def compatible_with_osmajor(cls, osmajor):
        return and_(
                or_(not_(Task.exclusive_osmajors.any()),
                    Task.exclusive_osmajors.any(OSMajor.id == osmajor.id)),
                not_(Task.excluded_osmajors.any(OSMajor.id == osmajor.id)))

    @classmethod
    def get_rpm_path(cls, rpm_name):
        return cls.library.get_rpm_path(rpm_name)

    @classmethod
    def update_task(cls, rpm_name, write_rpm):
        return cls.library.update_task(rpm_name, write_rpm)

    @classmethod
    def make_snapshot_repo(cls, repo_dir):
        return cls.library.make_snapshot_repo(repo_dir)

    @staticmethod
    def check_downgrade(old_version, new_version):
        old_version, old_release = old_version.rsplit('-', 1)
        new_version, new_release = new_version.rsplit('-', 1)
        # labelCompare returns 1 if tup1 > tup2
        # It is ok to default epoch to 0, since rhts-devel doesn't generate
        # task packages with epoch > 0
        return rpm.labelCompare(('0', old_version, old_release),
                                ('0', new_version, new_release)) == 1

    @classmethod
    def create_from_taskinfo(cls, raw_taskinfo):
        """Create a new task object based on details retrieved from an RPM"""

        tinfo = testinfo.parse_string(raw_taskinfo['desc'].decode('utf8'))

        if len(tinfo.test_name) > 255:
            raise BX(_("Task name should be <= 255 characters"))
        if tinfo.test_name.endswith('/'):
            raise BX(_(u'Task name must not end with slash'))
        if '//' in tinfo.test_name: # pylint:disable=unsupported-membership-test
            raise BX(_(u'Task name must not contain redundant slashes'))

        existing_task = Task.query.filter(Task.name == tinfo.test_name).first()
        if existing_task is not None:
            task = existing_task
            # RPM is the same version we have. don't process
            if existing_task.version == raw_taskinfo['hdr']['ver']:
                raise BX(_("Failed to import,  %s is the same version we already have" % task.version))
            # if the task is already present, check if a downgrade has been requested
            downgrade = cls.check_downgrade(task.version, raw_taskinfo['hdr']['ver'])
        else:
            task = Task(name=tinfo.test_name)
            downgrade = False

        task.version = raw_taskinfo['hdr']['ver']
        task.description = tinfo.test_description
        task.types = []
        task.bugzillas = []
        task.required = []
        task.runfor = []
        task.needs = []
        task.excluded_osmajors = []
        task.exclusive_osmajors = []
        task.excluded_arches = []
        task.exclusive_arches = []
        for family in tinfo.releases:
            if family.startswith('-'):
                try:
                    osmajor = OSMajor.by_name_alias(family.lstrip('-'))
                    if osmajor not in task.excluded_osmajors:
                        task.excluded_osmajors.append(osmajor)
                except NoResultFound:
                    pass
            else:
                try:
                    osmajor = OSMajor.by_name_alias(family)
                    if osmajor not in task.exclusive_osmajors:
                        task.exclusive_osmajors.append(osmajor)
                except NoResultFound:
                    pass
        for value in tinfo.test_archs:
            if value.startswith('-'):
                try:
                    arch = Arch.by_name(value.lstrip('-'))
                except ValueError:
                    pass
                else:
                    if arch not in task.excluded_arches:
                        task.excluded_arches.append(arch)
            else:
                try:
                    arch = Arch.by_name(value)
                except ValueError:
                    pass
                else:
                    if arch not in task.exclusive_arches:
                        task.exclusive_arches.append(arch)
        task.avg_time = tinfo.avg_test_time
        for type in tinfo.types:
            ttype = TaskType.lazy_create(type=type)
            task.types.append(ttype)
        for bug in tinfo.bugs:
            task.bugzillas.append(TaskBugzilla(bugzilla_id=bug))
        task.path = tinfo.test_path
        # Bug 772882. Remove duplicate required package here
        # Avoid ORM insert in task_packages_required_map twice.
        tinfo.runfor = list(set(tinfo.runfor))
        for runfor in tinfo.runfor:
            package = TaskPackage.lazy_create(package=runfor)
            task.runfor.append(package)
        task.priority = tinfo.priority
        task.destructive = tinfo.destructive
        # Bug 772882. Remove duplicate required package here
        # Avoid ORM insert in task_packages_required_map twice.
        tinfo.requires = list(set(tinfo.requires))
        for require in tinfo.requires:
            package = TaskPackage.lazy_create(package=require)
            task.required.append(package)
        for need in tinfo.needs:
            task.needs.append(TaskPropertyNeeded(property=need))
        task.license = tinfo.license
        task.owner = tinfo.owner

        try:
            task.uploader = identity.current.user
        except identity.RequestRequiredException:
            task.uploader = User.query.get(1)

        task.valid = True

        return task, downgrade

    def to_dict(self):
        """ return a dict of this object """
        return dict(id = self.id,
                    name = self.name,
                    rpm = self.rpm,
                    path = self.path,
                    description = self.description,
                    repo = u'None', # for compatibility only
                    max_time = self.avg_time,
                    destructive = self.destructive,
                    nda = self.nda,
                    creation_date = '%s' % self.creation_date,
                    update_date = '%s' % self.update_date,
                    owner = self.owner,
                    uploader = self.uploader and self.uploader.user_name,
                    uploading_user = self.uploader and self.uploader.__json__(),
                    version = self.version,
                    license = self.license,
                    priority = self.priority,
                    valid = self.valid or False,
                    types = ['%s' % type.type for type in self.types],
                    excluded_osmajor = ['%s' % osmajor for osmajor in self.excluded_osmajors],
                    exclusive_osmajor = ['%s' % osmajor for osmajor in self.exclusive_osmajors],
                    excluded_arch = ['%s' % arch for arch in self.excluded_arches],
                    exclusive_arch = ['%s' % arch for arch in self.exclusive_arches],
                    runfor = ['%s' % package for package in self.runfor],
                    required = ['%s' % package for package in self.required],
                    bugzillas = ['%s' % bug.bugzilla_id for bug in self.bugzillas],
                    expected_time = self.expected_time(),
                    needs = ['%s' % need.property for need in self.needs],
                   )

    def to_xml(self, pretty=False):
        task = lxml.etree.Element('task',
                                  name=self.name,
                                  creation_date=str(self.creation_date),
                                  version=str(self.version),
                                  )

        # 'destructive' and 'nda' field could be NULL if it's missing from
        # testinfo.desc. To satisfy the Relax NG schema, such attributes
        # should be omitted. So only set these attributes when they're present.
        optional_attrs = ['destructive', 'nda']
        for attr in optional_attrs:
            if getattr(self, attr) is not None:
                task.set(attr, str(getattr(self, attr)).lower())

        desc =  lxml.etree.Element('description')
        desc.text =u'%s' % self.description
        task.append(desc)

        owner = lxml.etree.Element('owner')
        owner.text = u'%s' % self.owner
        task.append(owner)

        path = lxml.etree.Element('path')
        path.text = u'%s' % self.path
        task.append(path)

        rpms = lxml.etree.Element('rpms')
        rpms.append(lxml.etree.Element('rpm',
                                       url=absolute_url('/rpms/%s' % self.rpm),
                                       name=u'%s' % self.rpm))
        task.append(rpms)
        if self.bugzillas:
            bzs = lxml.etree.Element('bugzillas')
            for bz in self.bugzillas:
                bz_elem = lxml.etree.Element('bugzilla')
                bz_elem.text = str(bz.bugzilla_id)
                bzs.append(bz_elem)
            task.append(bzs)
        if self.runfor:
            runfor = lxml.etree.Element('runFor')
            for package in self.runfor:
                package_elem = lxml.etree.Element('package')
                package_elem.text = package.package
                runfor.append(package_elem)
            task.append(runfor)
        if self.required:
            requires = lxml.etree.Element('requires')
            for required in self.required:
                required_elem = lxml.etree.Element('package')
                required_elem.text = required.package
                requires.append(required_elem)
            task.append(requires)
        if self.types:
            types = lxml.etree.Element('types')
            for type in self.types:
                type_elem = lxml.etree.Element('type')
                type_elem.text = type.type
                types.append(type_elem)
            task.append(types)
        if self.excluded_osmajors:
            excluded = lxml.etree.Element('excludedDistroFamilies')
            for excluded_osmajor in self.excluded_osmajors:
                osmajor_elem = lxml.etree.Element('distroFamily')
                osmajor_elem.text = excluded_osmajor.osmajor
                excluded.append(osmajor_elem)
            task.append(excluded)
        if self.excluded_arches:
            excluded = lxml.etree.Element('excludedArches')
            for excluded_arch in self.excluded_arches:
                arch_elem = lxml.etree.Element('arch')
                arch_elem.text = excluded_arch.arch
                excluded.append(arch_elem)
            task.append(excluded)
        return lxml.etree.tostring(task, pretty_print=pretty, encoding='utf8')

    def expected_time(self, suffixes=(' year',' week',' day',' hour',' minute',' second'), add_s=True, separator=', '):
        """
        Takes an amount of seconds and turns it into a human-readable amount of
        time.
        """
        seconds = self.avg_time
        # the formatted time string to be returned
        time = []

        # the pieces of time to iterate over (days, hours, minutes, etc)
        # - the first piece in each tuple is the suffix (d, h, w)
        # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
        parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
                (suffixes[1], 60 * 60 * 24 * 7),
                (suffixes[2], 60 * 60 * 24),
                (suffixes[3], 60 * 60),
                (suffixes[4], 60),
                (suffixes[5], 1)]

        # for each time piece, grab the value and remaining seconds,
        # and add it to the time string
        for suffix, length in parts:
            value = seconds / length
            if value > 0:
                seconds = seconds % length
                time.append('%s%s' % (str(value),
                            (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
            if seconds < 1:
                break

        return separator.join(time)

    def disable(self):
        """
        Disable task so it can't be used.
        """
        self.library.unlink_rpm(self.rpm)
        self.valid = False
        return

task_exclude_osmajor = Table(
    'task_exclude_osmajor', DeclarativeMappedObject.metadata,
    Column('task_id', Integer,
           ForeignKey('task.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    Column('osmajor_id', Integer,
           ForeignKey('osmajor.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    mysql_engine='InnoDB',
)

task_exclusive_osmajor = Table('task_exclusive_osmajor', DeclarativeMappedObject.metadata,
    Column('task_id', Integer,
           ForeignKey('task.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    Column('osmajor_id', Integer,
           ForeignKey('osmajor.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    mysql_engine='InnoDB',
)

task_exclude_arch = Table(
    'task_exclude_arch', DeclarativeMappedObject.metadata,
    Column('task_id', Integer,
           ForeignKey('task.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    mysql_engine='InnoDB',
)

task_exclusive_arch = Table('task_exclusive_arch', DeclarativeMappedObject.metadata,
    Column('task_id', Integer,
           ForeignKey('task.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True, nullable=False, index=True),
    mysql_engine='InnoDB',
)

class TaskType(DeclarativeMappedObject):
    """
    A task can be classified into serveral task types which can be used to
    select tasks for batch runs
    """

    __tablename__ = 'task_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    type = Column(Unicode(255), nullable=False, unique=True)
    tasks = relationship(Task, secondary=task_type_map, back_populates='types')

    @classmethod
    def by_name(cls, type):
        return cls.query.filter_by(type=type).one()


class TaskPropertyNeeded(DeclarativeMappedObject):
    """
    Tasks can have requirements on the systems that they run on.
         *not currently implemented*
    """

    __tablename__ = 'task_property_needed'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('task.id'))
    property = Column(Unicode(2048))


class TaskBugzilla(DeclarativeMappedObject):
    """
    Bugzillas that apply to this Task.
    """

    __tablename__ = 'task_bugzilla'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    bugzilla_id = Column(Integer)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=False)
    task = relationship(Task, back_populates='bugzillas')
