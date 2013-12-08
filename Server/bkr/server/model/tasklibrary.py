
import os.path
from datetime import datetime
import subprocess
import shutil
import logging
import rpm
import xml.dom.minidom
import lxml.etree
from sqlalchemy import (Table, Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import mapper, relation
from turbogears.config import get
from turbogears.database import session, metadata
from rhts import testinfo
from bkr.common.helpers import (AtomicFileReplacement, Flock,
                                makedirs_ignore, unlink_ignore)
from bkr.server import identity
from bkr.server.bexceptions import BX
from bkr.server.util import absolute_url, run_createrepo
from .base import MappedObject
from .identity import User
from .distrolibrary import Arch, OSMajor

log = logging.getLogger(__name__)

xmldoc = xml.dom.minidom.Document()

task_exclude_arch_table = Table('task_exclude_arch', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('task_id', Integer, ForeignKey('task.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    mysql_engine='InnoDB',
)

task_exclude_osmajor_table = Table('task_exclude_osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('task_id', Integer, ForeignKey('task.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    mysql_engine='InnoDB',
)

task_table = Table('task',metadata,
        Column('id', Integer, primary_key=True),
        Column('name', Unicode(255), unique=True),
        Column('rpm', Unicode(255), unique=True),
        Column('path', Unicode(4096)),
        Column('description', Unicode(2048)),
        Column('repo', Unicode(256)),
        Column('avg_time', Integer, default=0),
        Column('destructive', Boolean),
        Column('nda', Boolean),
        # This should be a map table
        #Column('notify', Unicode(2048)),

        Column('creation_date', DateTime, default=datetime.utcnow),
        Column('update_date', DateTime, onupdate=datetime.utcnow),
        Column('uploader_id', Integer, ForeignKey('tg_user.user_id')),
        Column('owner', Unicode(255), index=True),
        Column('version', Unicode(256)),
        Column('license', Unicode(256)),
        Column('priority', Unicode(256)),
        Column('valid', Boolean, default=True),
        mysql_engine='InnoDB',
)

task_bugzilla_table = Table('task_bugzilla',metadata,
        Column('id', Integer, primary_key=True),
        Column('bugzilla_id', Integer),
        Column('task_id', Integer,
                ForeignKey('task.id')),
        mysql_engine='InnoDB',
)

task_packages_runfor_map = Table('task_packages_runfor_map', metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

task_packages_required_map = Table('task_packages_required_map', metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

task_property_needed_table = Table('task_property_needed', metadata,
        Column('id', Integer, primary_key=True),
        Column('task_id', Integer,
                ForeignKey('task.id')),
        Column('property', Unicode(2048)),
        mysql_engine='InnoDB',
)

task_package_table = Table('task_package',metadata,
        Column('id', Integer, primary_key=True),
        Column('package', Unicode(255), nullable=False, unique=True),
        mysql_engine='InnoDB',
        mysql_collate='utf8_bin',
)

task_type_table = Table('task_type',metadata,
        Column('id', Integer, primary_key=True),
        Column('type', Unicode(255), nullable=False, unique=True),
        mysql_engine='InnoDB',
)

task_type_map = Table('task_type_map',metadata,
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
        return get("basepath.rpms", "/var/www/beaker/rpms")

    def get_rpm_path(self, rpm_name):
        return os.path.join(self.rpmspath, rpm_name)

    def _unlink_locked_rpm(self, rpm_name):
        # Internal call that assumes the flock is already held
        unlink_ignore(self.get_rpm_path(rpm_name))

    def unlink_rpm(self, rpm_name):
        """
        Ensures an RPM is no longer present in the task library
        """
        with Flock(self.rpmspath):
            self._unlink_locked_rpm(rpm_name)

    def _update_locked_repo(self):
        # Internal call that assumes the flock is already held
        # Removed --baseurl, if upgrading you will need to manually
        # delete repodata directory before this will work correctly.
        command, returncode, out, err = run_createrepo(cwd=self.rpmspath)
        if out:
            log.debug("stdout from %s: %s", command, out)
        if err:
            log.warn("stderr from %s: %s", command, err)
        if returncode != 0:
            raise RuntimeError('Createrepo failed.\nreturncode:%s cmd:%s err:%s'
                % (returncode, command, err))

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
        """Updates the specified task

           write_rpm must be a callable that takes a file object as its
           sole argument and populates it with the raw task RPM contents

           Expects to be called in a transaction, and for that transaction
           to be rolled back if an exception is thrown.
        """
        # XXX (ncoghlan): How do we get rid of that assumption about the
        # transaction handling? Assuming we're *not* already in a transaction
        # won't work either.
        rpm_path = self.get_rpm_path(rpm_name)
        upgrade = AtomicFileReplacement(rpm_path)
        f = upgrade.create_temp()
        try:
            write_rpm(f)
            f.flush()
            f.seek(0)
            task = Task.create_from_taskinfo(self.read_taskinfo(f))
            old_rpm_name = task.rpm
            task.rpm = rpm_name
            with Flock(self.rpmspath):
                upgrade.replace_dest()
                try:
                    self._update_locked_repo()
                except:
                    # We assume the current transaction is going to be rolled back,
                    # so the Task possibly defined above, or changes to an existing
                    # task, will never by written to the database (even if it was
                    # the _update_locked_repo() call that failed).
                    # Accordingly, we also throw away the newly created RPM.
                    self._unlink_locked_rpm(rpm_name)
                    raise
                # New task has been added, throw away the old one
                if old_rpm_name:
                    self._unlink_locked_rpm(old_rpm_name)
                    # Since it existed when we called _update_locked_repo()
                    # above, this RPM will still be referenced from the
                    # metadata, albeit not as the latest version.
                    # However, it's too expensive (several seconds of IO
                    # with the task repo locked) to do it twice for every
                    # task update, so we rely on the fact that tasks are
                    # referenced by name rather than requesting specific
                    # versions, and thus will always grab the latest.
        finally:
            # This is a no-op if we successfully replaced the destination
            upgrade.destroy_temp()
        return task

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
        for file in taskinfo['hdr']['files']:
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


class Task(MappedObject):
    """
    Tasks that are available to schedule
    """

    library = TaskLibrary()

    @classmethod
    def by_name(cls, name, valid=None):
        query = cls.query.filter(Task.name==name)
        if valid is not None:
            query = query.filter(Task.valid==bool(valid))
        return query.one()

    @classmethod
    def by_id(cls, id, valid=None):
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
    def get_rpm_path(cls, rpm_name):
        return cls.library.get_rpm_path(rpm_name)

    @classmethod
    def update_task(cls, rpm_name, write_rpm):
        return cls.library.update_task(rpm_name, write_rpm)

    @classmethod
    def make_snapshot_repo(cls, repo_dir):
        return cls.library.make_snapshot_repo(repo_dir)

    @classmethod
    def create_from_taskinfo(cls, raw_taskinfo):
        """Create a new task object based on details retrieved from an RPM"""

        tinfo = testinfo.parse_string(raw_taskinfo['desc'])

        if len(tinfo.test_name) > 255:
            raise BX(_("Task name should be <= 255 characters"))
        if tinfo.test_name.endswith('/'):
            raise BX(_(u'Task name must not end with slash'))
        if '//' in tinfo.test_name:
            raise BX(_(u'Task name must not contain redundant slashes'))

        task = cls.lazy_create(name=tinfo.test_name)

        # RPM is the same version we have. don't process
        if task.version == raw_taskinfo['hdr']['ver']:
            raise BX(_("Failed to import,  %s is the same version we already have" % task.version))

        task.version = raw_taskinfo['hdr']['ver']
        task.description = tinfo.test_description
        task.types = []
        task.bugzillas = []
        task.required = []
        task.runfor = []
        task.needs = []
        task.excluded_osmajor = []
        task.excluded_arch = []
        includeFamily=[]
        for family in tinfo.releases:
            if family.startswith('-'):
                try:
                    if family.lstrip('-') not in task.excluded_osmajor:
                        task.excluded_osmajor.append(TaskExcludeOSMajor(osmajor=OSMajor.by_name_alias(family.lstrip('-'))))
                except InvalidRequestError:
                    pass
            else:
                try:
                    includeFamily.append(OSMajor.by_name_alias(family).osmajor)
                except InvalidRequestError:
                    pass
        families = set([ '%s' % family.osmajor for family in OSMajor.query])
        if includeFamily:
            for family in families.difference(set(includeFamily)):
                if family not in task.excluded_osmajor:
                    task.excluded_osmajor.append(TaskExcludeOSMajor(osmajor=OSMajor.by_name_alias(family)))
        if tinfo.test_archs:
            arches = set([ '%s' % arch.arch for arch in Arch.query])
            for arch in arches.difference(set(tinfo.test_archs)):
                if arch not in task.excluded_arch:
                    task.excluded_arch.append(TaskExcludeArch(arch=Arch.by_name(arch)))
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

        return task

    def to_dict(self):
        """ return a dict of this object """
        return dict(id = self.id,
                    name = self.name,
                    rpm = self.rpm,
                    path = self.path,
                    description = self.description,
                    repo = '%s' % self.repo,
                    max_time = self.avg_time,
                    destructive = self.destructive,
                    nda = self.nda,
                    creation_date = '%s' % self.creation_date,
                    update_date = '%s' % self.update_date,
                    owner = self.owner,
                    uploader = self.uploader and self.uploader.user_name,
                    version = self.version,
                    license = self.license,
                    priority = self.priority,
                    valid = self.valid or False,
                    types = ['%s' % type.type for type in self.types],
                    excluded_osmajor = ['%s' % osmajor.osmajor for osmajor in self.excluded_osmajor],
                    excluded_arch = ['%s' % arch.arch for arch in self.excluded_arch],
                    runfor = ['%s' % package for package in self.runfor],
                    required = ['%s' % package for package in self.required],
                    bugzillas = ['%s' % bug.bugzilla_id for bug in self.bugzillas],
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
        if self.excluded_osmajor:
            excluded = lxml.etree.Element('excludedDistroFamilies')
            for excluded_osmajor in self.excluded_osmajor:
                osmajor_elem = lxml.etree.Element('distroFamily')
                osmajor_elem.text = excluded_osmajor.osmajor.osmajor
                excluded.append(osmajor_elem)
            task.append(excluded)
        if self.excluded_arch:
            excluded = lxml.etree.Element('excludedArches')
            for excluded_arch in self.excluded_arch:
                arch_elem = lxml.etree.Element('arch')
                arch_elem.text=excluded_arch.arch.arch
                excluded.append(arch_elem)
            task.append(excluded)
        return lxml.etree.tostring(task, pretty_print=pretty)

    def elapsed_time(self, suffixes=(' year',' week',' day',' hour',' minute',' second'), add_s=True, separator=', '):
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


class TaskExcludeOSMajor(MappedObject):
    """
    A task can be excluded by arch, osmajor, or osversion
                        RedHatEnterpriseLinux3, RedHatEnterpriseLinux4
    """
    def __cmp__(self, other):
        """ Used to compare excludes that are already stored.
        """
        if other == "%s" % self.osmajor.osmajor or \
           other == "%s" % self.osmajor.alias:
            return 0
        else:
            return 1

class TaskExcludeArch(MappedObject):
    """
    A task can be excluded by arch
                        i386, s390
    """
    def __cmp__(self, other):
        """ Used to compare excludes that are already stored.
        """
        if other == "%s" % self.arch.arch:
            return 0
        else:
            return 1

class TaskType(MappedObject):
    """
    A task can be classified into serveral task types which can be used to
    select tasks for batch runs
    """
    @classmethod
    def by_name(cls, type):
        return cls.query.filter_by(type=type).one()


class TaskPackage(MappedObject):
    """
    A list of packages that a tasks should be run for.
    """
    @classmethod
    def by_name(cls, package):
        return cls.query.filter_by(package=package).one()

    def __repr__(self):
        return self.package

    def to_xml(self):
        package = xmldoc.createElement("package")
        package.setAttribute("name", "%s" % self.package)
        return package

class TaskPropertyNeeded(MappedObject):
    """
    Tasks can have requirements on the systems that they run on.
         *not currently implemented*
    """
    pass


class TaskBugzilla(MappedObject):
    """
    Bugzillas that apply to this Task.
    """
    pass

mapper(Task, task_table,
        properties = {'types':relation(TaskType,
                                        secondary=task_type_map,
                                        backref='tasks'),
                      'excluded_osmajor':relation(TaskExcludeOSMajor,
                                        backref='task'),
                      'excluded_arch':relation(TaskExcludeArch,
                                        backref='task'),
                      'runfor':relation(TaskPackage,
                                        secondary=task_packages_runfor_map,
                                        backref='tasks'),
                      'required':relation(TaskPackage,
                                        secondary=task_packages_required_map,
                                        order_by=[task_package_table.c.package]),
                      'needs':relation(TaskPropertyNeeded),
                      'bugzillas':relation(TaskBugzilla, backref='task',
                                            cascade='all, delete-orphan'),
                      'uploader':relation(User, uselist=False, backref='tasks'),
                     }
      )

mapper(TaskExcludeOSMajor, task_exclude_osmajor_table,
       properties = {
                     'osmajor':relation(OSMajor),
                    }
      )

mapper(TaskExcludeArch, task_exclude_arch_table,
       properties = {
                     'arch':relation(Arch),
                    }
      )

mapper(TaskPackage, task_package_table)
mapper(TaskPropertyNeeded, task_property_needed_table)
mapper(TaskType, task_type_table)
mapper(TaskBugzilla, task_bugzilla_table)
