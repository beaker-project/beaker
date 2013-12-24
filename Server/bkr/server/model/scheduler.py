
import os.path
import logging
from datetime import datetime, timedelta
from copy import copy
import re
import shutil
import string
import random
import crypt
import xml.dom.minidom
from collections import defaultdict
import uuid
import urlparse
import netaddr
from kid import Element
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Index,
        Integer, Unicode, DateTime, Boolean, UnicodeText, String, Numeric)
from sqlalchemy.sql import select, union, and_, or_, not_, func, literal
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import mapper, relation, backref, object_mapper, dynamic_loader
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears import url
from turbogears.config import get
from turbogears.database import session, metadata
from bkr.common.helpers import makedirs_ignore
from bkr.server import identity, metrics, mail, dynamic_virt
from bkr.server.bexceptions import BX, BeakerException, StaleTaskStatusException
from bkr.server.helpers import make_link, make_fake_link
from bkr.server.hybrid import hybrid_method, hybrid_property
from bkr.server.installopts import InstallOptions, global_install_options
from bkr.server.util import absolute_url
from .types import (UUID, MACAddress, TaskResult, TaskStatus, TaskPriority,
        ResourceType, RecipeVirtStatus, mac_unix_padded_dialect)
from .base import MappedObject
from .activity import Activity, activity_table
from .identity import User, Group, users_table
from .lab import LabController, lab_controller_table
from .distrolibrary import OSMajor, OSVersion, Distro, DistroTree
from .tasklibrary import Task, TaskPackage
from .inventory import System, SystemActivity, Reservation, system_table

log = logging.getLogger(__name__)

xmldoc = xml.dom.minidom.Document()

def node(element, value):
    node = xmldoc.createElement(element)
    node.appendChild(xmldoc.createTextNode(value))
    return node

watchdog_table = Table('watchdog', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('recipe_id', Integer, ForeignKey('recipe.id'), nullable=False),
    Column('recipetask_id', Integer, ForeignKey('recipe_task.id')),
    Column('subtask', Unicode(255)),
    Column('kill_time', DateTime),
    mysql_engine='InnoDB',
)

recipe_set_nacked_table = Table('recipe_set_nacked', metadata,
    Column('recipe_set_id', Integer, ForeignKey('recipe_set.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True,nullable=False),
    Column('response_id', Integer, ForeignKey('response.id',
        onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('comment', Unicode(255),nullable=True),
    Column('created',DateTime,nullable=False,default=datetime.utcnow),
    mysql_engine='InnoDB',
)

beaker_tag_table = Table('beaker_tag', metadata,
    Column('id', Integer, primary_key=True, nullable = False),
    Column('tag', Unicode(20), nullable=False),
    Column('type', Unicode(40), nullable=False),
    UniqueConstraint('tag', 'type'),
    mysql_engine='InnoDB',
)

retention_tag_table = Table('retention_tag', metadata,
    Column('id', Integer, ForeignKey('beaker_tag.id', onupdate='CASCADE', ondelete='CASCADE'),nullable=False, primary_key=True),
    Column('default_', Boolean),
    Column('expire_in_days', Integer, default=0),
    Column('needs_product', Boolean),
    mysql_engine='InnoDB',
)

product_table = Table('product', metadata,
    Column('id', Integer, autoincrement=True, nullable=False,
        primary_key=True),
    Column('name', Unicode(100),unique=True, index=True, nullable=False),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    mysql_engine='InnoDB',
)

response_table = Table('response', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True, nullable=False),
    Column('response',Unicode(50), nullable=False),
    mysql_engine='InnoDB',
)

recipeset_activity_table = Table('recipeset_activity', metadata,
    Column('id', Integer,ForeignKey('activity.id'), primary_key=True),
    Column('recipeset_id', Integer, ForeignKey('recipe_set.id')),
    mysql_engine='InnoDB',
)

job_table = Table('job',metadata,
        Column('id', Integer, primary_key=True),
        Column('dirty_version', UUID, nullable=False),
        Column('clean_version', UUID, nullable=False),
        Column('owner_id', Integer,
                ForeignKey('tg_user.user_id'), index=True),
        Column('submitter_id', Integer,
                ForeignKey('tg_user.user_id', name='job_submitter_id_fk')),
        Column('group_id', Integer, ForeignKey('tg_group.group_id', \
            name='job_group_id_fk'), default=None),
        Column('whiteboard',Unicode(2000)),
        Column('retention_tag_id', Integer, ForeignKey('retention_tag.id'), nullable=False),
        Column('product_id', Integer, ForeignKey('product.id'),nullable=True),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new, index=True),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new, index=True),
        Column('deleted', DateTime, default=None, index=True),
        Column('to_delete', DateTime, default=None, index=True),
        # Total tasks
	Column('ttasks', Integer, default=0),
        # Total Passing tasks
        Column('ptasks', Integer, default=0),
        # Total Warning tasks
        Column('wtasks', Integer, default=0),
        # Total Failing tasks
        Column('ftasks', Integer, default=0),
        # Total Panic tasks
        Column('ktasks', Integer, default=0),
        mysql_engine='InnoDB',
)
# for fast dirty_version != clean_version comparisons:
Index('ix_job_dirty_clean_version', job_table.c.dirty_version, job_table.c.clean_version)

job_cc_table = Table('job_cc', metadata,
        Column('job_id', Integer, ForeignKey('job.id', ondelete='CASCADE',
            onupdate='CASCADE'), primary_key=True),
        Column('email_address', Unicode(255), primary_key=True, index=True),
        mysql_engine='InnoDB',
)

recipe_set_table = Table('recipe_set',metadata,
        Column('id', Integer, primary_key=True),
        Column('job_id', Integer,
                ForeignKey('job.id'), nullable=False),
        Column('priority', TaskPriority.db_type(), nullable=False,
                default=TaskPriority.default_priority(), index=True),
        Column('queue_time',DateTime, nullable=False, default=datetime.utcnow),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new, index=True),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new, index=True),
        Column('lab_controller_id', Integer,
                ForeignKey('lab_controller.id')),
        # Total tasks
	Column('ttasks', Integer, default=0),
        # Total Passing tasks
        Column('ptasks', Integer, default=0),
        # Total Warning tasks
        Column('wtasks', Integer, default=0),
        # Total Failing tasks
        Column('ftasks', Integer, default=0),
        # Total Panic tasks
        Column('ktasks', Integer, default=0),
        mysql_engine='InnoDB',
)

# Log tables all have the following fields:
#   path
#       Subdirectory of this log, relative to the root of the recipe/RT/RTR. 
#       Probably won't have an initial or trailing slash, but I wouldn't bet on 
#       it. ;-) Notably, the value '/' is used (rather than the empty string) 
#       to represent no subdirectory.
#   filename
#       Filename of this log.
#   server
#       Absolute URL to the directory where the log is stored. Path and 
#       filename are relative to this.
#       Always NULL if log transferring is not enabled (CACHE=False).
#   basepath
#       Absolute filesystem path to the directory where the log is stored on 
#       the remote system. XXX we shouldn't need to store this!
#       Always NULL if log transferring is not enabled (CACHE=False).

log_recipe_table = Table('log_recipe', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer, ForeignKey('recipe.id'),
            nullable=False),
        Column('path', UnicodeText()),
        Column('filename', UnicodeText(), nullable=False),
        Column('start_time',DateTime, default=datetime.utcnow),
	Column('server', UnicodeText()),
	Column('basepath', UnicodeText()),
        mysql_engine='InnoDB',
)

log_recipe_task_table = Table('log_recipe_task', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer, ForeignKey('recipe_task.id'),
            nullable=False),
        Column('path', UnicodeText()),
        Column('filename', UnicodeText(), nullable=False),
        Column('start_time',DateTime, default=datetime.utcnow),
	Column('server', UnicodeText()),
	Column('basepath', UnicodeText()),
        mysql_engine='InnoDB',
)

log_recipe_task_result_table = Table('log_recipe_task_result', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_result_id', Integer,
                ForeignKey('recipe_task_result.id'), nullable=False),
        Column('path', UnicodeText()),
        Column('filename', UnicodeText(), nullable=False),
        Column('start_time',DateTime, default=datetime.utcnow),
	Column('server', UnicodeText()),
	Column('basepath', UnicodeText()),
        mysql_engine='InnoDB',
)

recipe_table = Table('recipe',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_set_id', Integer,
                ForeignKey('recipe_set.id'), nullable=False),
        Column('distro_tree_id', Integer,
                ForeignKey('distro_tree.id')),
        Column('rendered_kickstart_id', Integer, ForeignKey('rendered_kickstart.id',
                name='recipe_rendered_kickstart_id_fk', ondelete='SET NULL')),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new, index=True),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new, index=True),
        Column('start_time',DateTime),
        Column('finish_time',DateTime),
        Column('_host_requires',UnicodeText()),
        Column('_distro_requires',UnicodeText()),
        # This column is actually a custom user-supplied kickstart *template*
        # (if not NULL), the generated kickstart for the recipe is defined above
        Column('kickstart',UnicodeText()),
        # type = recipe, machine_recipe or guest_recipe
        Column('type', String(30), nullable=False),
        # Total tasks
	Column('ttasks', Integer, default=0),
        # Total Passing tasks
        Column('ptasks', Integer, default=0),
        # Total Warning tasks
        Column('wtasks', Integer, default=0),
        # Total Failing tasks
        Column('ftasks', Integer, default=0),
        # Total Panic tasks
        Column('ktasks', Integer, default=0),
        Column('whiteboard',Unicode(2000)),
        Column('ks_meta', String(1024)),
        Column('kernel_options', String(1024)),
        Column('kernel_options_post', String(1024)),
        Column('role', Unicode(255)),
        Column('panic', Unicode(20)),
        Column('_partitions',UnicodeText()),
        Column('autopick_random', Boolean, default=False),
        Column('log_server', Unicode(255), index=True),
        Column('virt_status', RecipeVirtStatus.db_type(), index=True,
                nullable=False, default=RecipeVirtStatus.possible),
        mysql_engine='InnoDB',
)

machine_recipe_table = Table('machine_recipe', metadata,
        Column('id', Integer, ForeignKey('recipe.id'), primary_key=True),
        mysql_engine='InnoDB',
)

guest_recipe_table = Table('guest_recipe', metadata,
        Column('id', Integer, ForeignKey('recipe.id'), primary_key=True),
        Column('guestname', UnicodeText()),
        Column('guestargs', UnicodeText()),
        mysql_engine='InnoDB',
)

machine_guest_map =Table('machine_guest_map',metadata,
        Column('machine_recipe_id', Integer,
                ForeignKey('machine_recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('guest_recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        mysql_engine='InnoDB',
)

system_recipe_map = Table('system_recipe_map', metadata,
        Column('system_id', Integer,
                ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        mysql_engine='InnoDB',
)

recipe_resource_table = Table('recipe_resource', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('recipe_id', Integer, ForeignKey('recipe.id',
        name='recipe_resource_recipe_id_fk',
        onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False, unique=True),
    Column('type', ResourceType.db_type(), nullable=False),
    Column('fqdn', Unicode(255), default=None),
    Column('rebooted', DateTime, nullable=True, default=None),
    Column('install_started', DateTime, nullable=True, default=None),
    Column('install_finished', DateTime, nullable=True, default=None),
    Column('postinstall_finished', DateTime, nullable=True, default=None),
    mysql_engine='InnoDB',
)

system_resource_table = Table('system_resource', metadata,
    Column('id', Integer, ForeignKey('recipe_resource.id',
            name='system_resource_id_fk'), primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
            name='system_resource_system_id_fk'), nullable=False),
    Column('reservation_id', Integer, ForeignKey('reservation.id',
            name='system_resource_reservation_id_fk')),
    mysql_engine='InnoDB',
)

virt_resource_table = Table('virt_resource', metadata,
    Column('id', Integer, ForeignKey('recipe_resource.id',
            name='virt_resource_id_fk'), primary_key=True),
    Column('system_name', Unicode(2048), nullable=False),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id',
            name='virt_resource_lab_controller_id_fk')),
    Column('mac_address', MACAddress(), index=True, default=None),
    mysql_engine='InnoDB',
)

guest_resource_table = Table('guest_resource', metadata,
    Column('id', Integer, ForeignKey('recipe_resource.id',
            name='guest_resource_id_fk'), primary_key=True),
    Column('mac_address', MACAddress(), index=True, default=None),
    mysql_engine='InnoDB',
)

recipe_tag_table = Table('recipe_tag',metadata,
        Column('id', Integer, primary_key=True),
        Column('tag', Unicode(255)),
        mysql_engine='InnoDB',
)

recipe_tag_map = Table('recipe_tag_map', metadata,
        Column('tag_id', Integer,
               ForeignKey('recipe_tag.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('recipe_id', Integer,
               ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        mysql_engine='InnoDB',
)

recipe_rpm_table =Table('recipe_rpm',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id'), nullable=False),
        Column('package',Unicode(255)),
        Column('version',Unicode(255)),
        Column('release',Unicode(255)),
        Column('epoch',Integer),
        Column('arch',Unicode(255)),
        Column('running_kernel', Boolean),
        mysql_engine='InnoDB',
)

recipe_repo_table =Table('recipe_repo',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id'), nullable=False),
        Column('name',Unicode(255)),
        Column('url',Unicode(1024)),
        mysql_engine='InnoDB',
)

recipe_ksappend_table = Table('recipe_ksappend', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id'), nullable=False),
        Column('ks_append',UnicodeText()),
        mysql_engine='InnoDB',
)

recipe_task_table =Table('recipe_task',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer, ForeignKey('recipe.id'), nullable=False),
        Column('task_id', Integer, ForeignKey('task.id'), nullable=False),
        Column('start_time',DateTime),
        Column('finish_time',DateTime),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new),
        Column('role', Unicode(255)),
        mysql_engine='InnoDB',
)

recipe_task_param_table = Table('recipe_task_param', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('name',Unicode(255)),
        Column('value',UnicodeText()),
        mysql_engine='InnoDB',
)

recipe_task_comment_table = Table('recipe_task_comment',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('comment', UnicodeText()),
        Column('created', DateTime),
        Column('user_id', Integer,
                ForeignKey('tg_user.user_id'), index=True),
        mysql_engine='InnoDB',
)

recipe_task_bugzilla_table = Table('recipe_task_bugzilla',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('bugzilla_id', Integer),
        mysql_engine='InnoDB',
)

recipe_task_rpm_table =Table('recipe_task_rpm',metadata,
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id'), primary_key=True),
        Column('package',Unicode(255)),
        Column('version',Unicode(255)),
        Column('release',Unicode(255)),
        Column('epoch',Integer),
        Column('arch',Unicode(255)),
        Column('running_kernel', Boolean),
        mysql_engine='InnoDB',
)

recipe_task_result_table = Table('recipe_task_result',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('path', Unicode(2048)),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new),
        Column('score', Numeric(10)),
        Column('log', UnicodeText()),
        Column('start_time',DateTime, default=datetime.utcnow),
        mysql_engine='InnoDB',
)

# This is for storing final generated kickstarts to be provisioned,
# not user-supplied kickstart templates or anything else like that.
rendered_kickstart_table = Table('rendered_kickstart', metadata,
    Column('id', Integer, primary_key=True),
    # Either kickstart or url should be populated -- if url is present,
    # it means fetch the kickstart from there instead
    Column('kickstart', UnicodeText),
    Column('url', UnicodeText),
    mysql_engine='InnoDB',
)

task_packages_custom_map = Table('task_packages_custom_map', metadata,
    Column('recipe_id', Integer, ForeignKey('recipe.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)


class Watchdog(MappedObject):
    """ Every running task has a corresponding watchdog which will
        Return the system if it runs too long
    """

    @classmethod
    def by_system(cls, system):
        """ Find a watchdog based on the system name
        """
        return cls.query.filter_by(system=system).one()

    @classmethod
    def by_status(cls, labcontroller=None, status="active"):
        """
        Returns a list of all watchdog entries that are either active
        or expired for this lab controller.

        A recipe is only returned as "expired" if all the recipes in the recipe 
        set have expired. Similarly, a recipe is returned as "active" so long 
        as any recipe in the recipe set is still active. Some tasks rely on 
        this behaviour. In particular, the host recipe in virt testing will 
        finish while its guests are still running, but we want to keep 
        monitoring the host's console log in case of a panic.
        """
        select_recipe_set_id = session.query(RecipeSet.id). \
            join(Recipe).join(Watchdog).group_by(RecipeSet.id)
        if status == 'active':
            watchdog_clause = func.max(Watchdog.kill_time) > datetime.utcnow()
        elif status =='expired':
            watchdog_clause = func.max(Watchdog.kill_time) < datetime.utcnow()
        else:
            return None

        recipe_set_in_watchdog = RecipeSet.id.in_(
            select_recipe_set_id.having(watchdog_clause))

        if labcontroller is None:
            my_filter = and_(Watchdog.kill_time != None, recipe_set_in_watchdog)
        else:
            my_filter = and_(RecipeSet.lab_controller==labcontroller,
                Watchdog.kill_time != None, recipe_set_in_watchdog)
        return cls.query.join(Watchdog.recipe, Recipe.recipeset).filter(my_filter)

class RecipeSetActivity(Activity):
    def object_name(self):
        return "RecipeSet: %s" % self.object.id


class Log(MappedObject):

    MAX_ENTRIES_PER_DIRECTORY = 100

    @staticmethod
    def _normalized_path(path):
        """
        We need to normalize the `path` attribute *before* storing it, so that 
        we don't end up with duplicate rows that point to equivalent filesystem 
        paths (bug 865265).
        Also by convention we use '/' rather than empty string to mean "no 
        subdirectory". It's all a bit weird...
        """
        return re.sub(r'/+', '/', path or u'') or u'/'

    @classmethod
    def lazy_create(cls, path=None, **kwargs):
        return super(Log, cls).lazy_create(path=cls._normalized_path(path), **kwargs)

    def __init__(self, path=None, filename=None,
                 server=None, basepath=None, parent=None):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.parent = parent
        self.path = self._normalized_path(path)
        self.filename = filename
        self.server = server
        self.basepath = basepath

    def __repr__(self):
        return '%s(path=%r, filename=%r, server=%r, basepath=%r)' % (
                self.__class__.__name__, self.path, self.filename,
                self.server, self.basepath)

    def result(self):
        return self.parent.result

    result = property(result)

    def _combined_path(self):
        """Combines path (which is really the "subdir" of sorts) with filename:
                      , log.txt => log.txt
                /     , log.txt => log.txt
                /debug, log.txt => debug/log.txt
                debug , log.txt => debug/log.txt
        """
        return os.path.join((self.path or '').lstrip('/'), self.filename)

    @property
    def full_path(self):
        """ Like .href, but returns an absolute filesystem path if the log is local. """
        if self.server:
            return self.href
        else:
            return os.path.join(self.parent.logspath, self.parent.filepath,
                self._combined_path())

    @property
    def href(self):
        if self.server:
            # self.server points at a directory so it should end in 
            # a trailing slash, but older versions of the code didn't do that
            url = self.server
            if not url.endswith('/'):
                url += '/'
            return '%s%s' % (url, self._combined_path())
        else:
            return os.path.join('/logs', self.parent.filepath, self._combined_path())

    @property
    def link(self):
        """ Return a link to this Log
        """
        return make_link(url=self.href, text=self._combined_path())

    @property
    def dict(self):
        """ Return a dict describing this log
        """
        return dict( server  = self.server,
                    path     = self.path,
                    filename = self.filename,
                    tid      = '%s:%s' % (self.type, self.id),
                    filepath = self.parent.filepath,
                    basepath = self.basepath,
                    url      = urlparse.urljoin(absolute_url('/'), self.href),
                   )

    @classmethod
    def by_id(cls,id):
        return cls.query.filter_by(id=id).one()

    def __cmp__(self, other):
        """ Used to compare logs that are already stored. Log(path,filename) in Recipe.logs  == True
        """
        if hasattr(other,'path'):
            path = other.path
        if hasattr(other,'filename'):
            filename = other.filename
        if "%s/%s" % (self.path,self.filename) == "%s/%s" % (path,filename):
            return 0
        else:
            return 1

class LogRecipe(Log):
    type = 'R'

class LogRecipeTask(Log):
    type = 'T'

class LogRecipeTaskResult(Log):
    type = 'E'

class TaskBase(MappedObject):
    t_id_types = dict(T = 'RecipeTask',
                      TR = 'RecipeTaskResult',
                      R = 'Recipe',
                      RS = 'RecipeSet',
                      J = 'Job')

    @property
    def logspath(self):
        return get('basepath.logs', '/var/www/beaker/logs')

    @classmethod
    def get_by_t_id(cls, t_id, *args, **kw):
        """
        Return an TaskBase object by it's shorthand i.e 'J:xx, RS:xx'
        """
        # Keep Client/doc/bkr.rst in sync with this
        task_type,id = t_id.split(":")
        try:
            class_str = cls.t_id_types[task_type]
        except KeyError:
            raise BeakerException(_('You have have specified an invalid task type:%s' % task_type))

        class_ref = globals()[class_str]
        try:
            obj_ref = class_ref.by_id(id)
        except InvalidRequestError, e:
            raise BeakerException(_('%s is not a valid %s id' % (id, class_str)))

        return obj_ref

    def _change_status(self, new_status, **kw):
        """
        _change_status will update the status if needed
        Returns True when status is changed
        """
        current_status = self.status
        if current_status != new_status:
            # Sanity check to make sure the status never goes backwards.
            if isinstance(self, (Recipe, RecipeTask)) and \
                    ((new_status.queued and not current_status.queued) or \
                     (not new_status.finished and current_status.finished)):
                raise ValueError('Invalid state transition for %s: %s -> %s'
                        % (self.t_id, current_status, new_status))
            # Use a conditional UPDATE to make sure we are really working from 
            # the latest database state.
            # The .base_mapper bit here is so we can get from MachineRecipe to 
            # Recipe, which is needed due to the limitations of .update() 
            if session.query(object_mapper(self).base_mapper)\
                    .filter_by(id=self.id, status=current_status)\
                    .update({'status': new_status}, synchronize_session=False) \
                    != 1:
                raise StaleTaskStatusException(
                        'Status for %s updated in another transaction'
                        % self.t_id)
            # update the ORM session state as well
            self.status = new_status
            return True
        else:
            return False

    def is_finished(self):
        """
        Simply state if the task is finished or not
        """
        return self.status.finished

    def is_queued(self):
        """
        State if the task is queued
        """
        return self.status.queued

    @hybrid_method
    def is_failed(self):
        """
        Return True if the task has failed
        """
        return (self.result in [TaskResult.warn,
                                TaskResult.fail,
                                TaskResult.panic])
    @is_failed.expression
    def is_failed(cls):
        """
        Return SQL expression that is true if the task has failed
        """
        return cls.result.in_([TaskResult.warn,
                               TaskResult.fail,
                               TaskResult.panic])

    # TODO: it would be good to split the bar definition out to a utility
    # module accepting a mapping of div classes to percentages and then
    # unit test it without needing to create dummy recipes
    @property
    def progress_bar(self):
        """Return proportional progress bar as a HTML div

        Returns None if there are no tasks at all
        """
        if not getattr(self, 'ttasks', None):
            return None
        # Get the width for individual items, using 3 decimal places
        # Even on large screens, this should be a fine enough resolution
        # to fill the bar reliably when all tasks are complete without needing
        # to fiddle directly with the width of any of the subelements
        fmt_style = 'width:%.3f%%'
        pstyle = wstyle = fstyle = kstyle = fmt_style % 0
        completed = 0
        if getattr(self, 'ptasks', None):
            completed += self.ptasks
            pstyle = fmt_style % (100.0 * self.ptasks / self.ttasks)
        if getattr(self, 'wtasks', None):
            completed += self.wtasks
            wstyle = fmt_style % (100.0 * self.wtasks / self.ttasks)
        if getattr(self, 'ftasks', None):
            completed += self.ftasks
            fstyle = fmt_style % (100.0 * self.ftasks / self.ttasks)
        if getattr(self, 'ktasks', None):
            completed += self.ktasks
            kstyle = fmt_style % (100.0 * self.ktasks / self.ttasks)
        # Truncate the overall percentage to ensure it nevers hits 100%
        # before we finish (even if only one task remains in a large recipe)
        percentCompleted = "%d%%" % int(100.0 * completed / self.ttasks)
        # Build the HTML
        div = Element('div', {'class': 'progress'})
        div.append(Element('div', {'class': 'bar bar-success', 'style': pstyle}))
        div.append(Element('div', {'class': 'bar bar-warning', 'style': wstyle}))
        div.append(Element('div', {'class': 'bar bar-danger', 'style': fstyle}))
        div.append(Element('div', {'class': 'bar bar-info', 'style': kstyle}))
        container = Element('div')
        container.text = percentCompleted
        container.append(div)
        return container


    def t_id(self):
        for t, class_ in self.t_id_types.iteritems():
            if self.__class__.__name__ == class_:
                return '%s:%s' % (t, self.id)
    t_id = property(t_id)

    def _get_log_dirs(self):
        """
        Returns the directory names of all a task's logs,
        with a trailing slash.

        URLs are also returned with a trailing slash.
        """
        logs_to_return = []
        for log in self.logs:
            full_path = os.path.dirname(log.full_path)
            if not full_path.endswith('/'):
                full_path += '/'
            logs_to_return.append(full_path)
        return logs_to_return


class Job(TaskBase):
    """
    Container to hold like recipe sets.
    """

    def __init__(self, ttasks=0, owner=None, whiteboard=None,
            retention_tag=None, product=None, group=None, submitter=None):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.ttasks = ttasks
        self.owner = owner
        if submitter is None:
            self.submitter = owner
        else:
            self.submitter = submitter
        self.group = group
        self.whiteboard = whiteboard
        self.retention_tag = retention_tag
        self.product = product
        self.dirty_version = uuid.uuid4()
        self.clean_version = self.dirty_version

    stop_types = ['abort','cancel']
    max_by_whiteboard = 20

    @classmethod
    def mine(cls, owner):
        """
        Returns a query of all jobs which are owned by the given user.
        """
        return cls.query.filter(or_(Job.owner==owner, Job.submitter==owner))

    @classmethod
    def my_groups(cls, owner):
        """
        ... as in, "my groups' jobs". Returns a query of all jobs which were 
        submitted for any of the given user's groups.
        """
        if owner.groups:
            return cls.query.outerjoin(Job.group)\
                    .filter(Group.group_id.in_([g.group_id for g in owner.groups]))
        else:
            return cls.query.filter(literal(False))

    @classmethod
    def get_nacks(self,jobs):
        queri = select([recipe_set_table.c.id], from_obj=job_table.join(recipe_set_table), whereclause=job_table.c.id.in_(jobs),distinct=True)
        results = queri.execute()
        current_nacks = []
        for r in results:
            rs_id = r[0]
            rs = RecipeSet.by_id(rs_id)
            response = getattr(rs.nacked,'response',None)
            if response == Response.by_response('nak'):
                current_nacks.append(rs_id)
        return current_nacks

    @classmethod
    def update_nacks(cls,job_ids,rs_nacks):
        """
        update_nacks() takes a list of job_ids and updates the job's recipesets with the correct nacks
        """
        queri = select([recipe_set_table.c.id], from_obj=job_table.join(recipe_set_table), whereclause=job_table.c.id.in_(job_ids),distinct=True)
        results = queri.execute()
        current_nacks = []
        if len(rs_nacks) > 0:
            rs_nacks = map(lambda x: int(x), rs_nacks) # they come in as unicode objs
        for res in results:
            rs_id = res[0]
            rs = RecipeSet.by_id(rs_id)
            if rs_id not in rs_nacks and rs.nacked: #looks like we're deleting it then
                rs.nacked = []
            else:
                if not rs.nacked and rs_id in rs_nacks: #looks like we're adding it then
                    rs.nacked = [RecipeSetResponse()]
                    current_nacks.append(rs_id)
                elif rs.nacked:
                    current_nacks.append(rs_id)

        return current_nacks

    @classmethod
    def complete_delta(cls, delta, query):
        delta = timedelta(**delta)
        if not query:
            query = cls.query
        query = query.join(cls.recipesets, RecipeSet.recipes).filter(and_(Recipe.finish_time < datetime.utcnow() - delta,
            cls.status.in_([status for status in TaskStatus if status.finished])))
        return query

    @classmethod
    def _remove_descendants(cls, list_of_logs):
        """Return a list of paths with common descendants removed
        """
        set_of_logs = set(list_of_logs)
        logs_A = copy(set_of_logs)
        logs_to_return = copy(set_of_logs)

        # This is a simple way to remove descendants,
        # as long as our list of logs doesn't get too large
        for log_A in logs_A:
            for log_B in set_of_logs:
                if log_B.startswith(log_A) and log_A != log_B:
                    try:
                        logs_to_return.remove(log_B)
                    except KeyError:
                        pass # Possibly already removed
        return logs_to_return

    @classmethod
    def expired_logs(cls, limit=None):
        """Iterate over log files for expired recipes

        Will not yield recipes that have already been deleted. Does
        yield recipes that are marked to be deleted though.
        """
        job_ids = [job_id for job_id, in cls.marked_for_deletion().values(Job.id)]
        for tag in RetentionTag.get_transient():
            expire_in = tag.expire_in_days
            tag_name = tag.tag
            job_ids.extend(job_id for job_id, in cls.find_jobs(tag=tag_name,
                complete_days=expire_in, include_to_delete=True).values(Job.id))
        job_ids = list(set(job_ids))
        if limit is not None:
            job_ids = job_ids[:limit]
        for job_id in job_ids:
            job = Job.by_id(job_id)
            logs = job.get_log_dirs()
            if logs:
                logs = cls._remove_descendants(logs)
            yield (job, logs)
        return

    @classmethod
    def has_family(cls, family, query=None, **kw):
        if query is None:
            query = cls.query
        query = query.join(cls.recipesets, RecipeSet.recipes, Recipe.distro_tree, DistroTree.distro, Distro.osversion, OSVersion.osmajor).filter(OSMajor.osmajor == family).reset_joinpoint()
        return query

    @classmethod
    def by_tag(cls, tag, query=None):
        if query is None:
            query = cls.query
        if type(tag) is list:
            tag_query = cls.retention_tag_id.in_([RetentionTag.by_tag(unicode(t)).id for t in tag])
        else:
            tag_query = cls.retention_tag==RetentionTag.by_tag(unicode(tag))

        return query.filter(tag_query)

    @classmethod
    def by_product(cls, product, query=None):
        if query is None:
            query=cls.query
        if type(product) is list:
            product_query = cls.product.in_(*[Product.by_name(p) for p in product])
        else:
            product_query = cls.product == Product.by_name(product)
        return query.join('product').filter(product_query)

    @classmethod
    def by_owner(cls, owner, query=None):
        if query is None:
            query=cls.query
        if type(owner) is list:
            owner_query = cls.owner.in_(*[User.by_user_name(p) for p in owner])
        else:
            owner_query = cls.owner == User.by_user_name(owner)
        return query.join('owner').filter(owner_query)

    @classmethod
    def sanitise_job_ids(cls, job_ids):
        """
            sanitise_job_ids takes a list of job ids and returns the list
            sans ids that are not 'valid' (i.e deleted jobs)
        """
        invalid_job_ids = [j[0] for j in cls.marked_for_deletion().values(Job.id)]
        valid_job_ids = []
        for job_id in job_ids:
            if job_id not in invalid_job_ids:
                valid_job_ids.append(job_id)
        return valid_job_ids

    @classmethod
    def sanitise_jobs(cls, query):
        """
            This method will remove any jobs from a query that are
            deemed to not be a 'valid' job
        """
        query = query.filter(and_(cls.to_delete==None, cls.deleted==None))
        return query

    @classmethod
    def by_whiteboard(cls, desc, like=False, only_valid=False):
        if type(desc) is list and len(desc) <= 1:
            desc = desc.pop()
        if type(desc) is list:
            if like:
                if len(desc) > 1:
                    raise ValueError('Cannot perform a like operation with multiple values')
                else:
                    query = Job.query.filter(Job.whiteboard.like('%%%s%%' % desc.pop()))
            else:
                query = Job.query.filter(Job.whiteboard.in_(desc))
        else:
            if like:
                query = Job.query.filter(Job.whiteboard.like('%%%s%%' % desc))
            else:
                query = Job.query.filter_by(whiteboard=desc)
        if only_valid:
            query = cls.sanitise_jobs(query)
        return query

    @classmethod
    def provision_system_job(cls, distro_tree_id, **kw):
        """ Create a new reserve job, if system_id is defined schedule it too """
        job = Job(ttasks=0, owner=identity.current.user, retention_tag=RetentionTag.get_default())
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard')
        if not isinstance(distro_tree_id, list):
            distro_tree_id = [distro_tree_id]

        if job.owner.rootpw_expired:
            raise BX(_(u"Your root password has expired, please change or clear it in order to submit jobs."))

        for id in distro_tree_id:
            try:
                distro_tree = DistroTree.by_id(id)
            except InvalidRequestError:
                raise BX(u'Invalid distro tree ID %s' % id)
            recipeSet = RecipeSet(ttasks=2)
            recipe = MachineRecipe(ttasks=2)
            # Inlcude the XML definition so that cloning this job will act as expected.
            recipe.distro_requires = distro_tree.to_xml().toxml()
            recipe.distro_tree = distro_tree
            # Don't report panic's for reserve workflow.
            recipe.panic = 'ignore'
            system_id = kw.get('system_id')
            if system_id:
                try:
                    system = System.by_id(kw.get('system_id'), identity.current.user)
                except InvalidRequestError:
                    raise BX(u'Invalid System ID %s' % system_id)
                # Inlcude the XML definition so that cloning this job will act as expected.
                recipe.host_requires = system.to_xml().toxml()
                recipe.systems.append(system)
            if kw.get('ks_meta'):
                recipe.ks_meta = kw.get('ks_meta')
            if kw.get('koptions'):
                recipe.kernel_options = kw.get('koptions')
            if kw.get('koptions_post'):
                recipe.kernel_options_post = kw.get('koptions_post')
            # Eventually we will want the option to add more tasks.
            # Add Install task
            recipe.tasks.append(RecipeTask(task = Task.by_name(u'/distribution/install')))
            # Add Reserve task
            reserveTask = RecipeTask(task = Task.by_name(u'/distribution/reservesys'))
            if kw.get('reservetime'):
                #FIXME add DateTimePicker to ReserveSystem Form
                reserveTask.params.append(RecipeTaskParam( name = 'RESERVETIME',
                                                                value = kw.get('reservetime')
                                                            )
                                        )
            recipe.tasks.append(reserveTask)
            recipeSet.recipes.append(recipe)
            job.recipesets.append(recipeSet)
            job.ttasks += recipeSet.ttasks
        session.add(job)
        session.flush()
        return job

    @classmethod
    def marked_for_deletion(cls):
        return cls.query.filter(and_(cls.to_delete!=None, cls.deleted==None))

    @classmethod
    def find_jobs(cls, query=None, tag=None, complete_days=None, family=None,
        product=None, include_deleted=False, include_to_delete=False,
        owner=None, **kw):
        """Return a filtered job query

        Does what it says. Also helps searching for expired jobs
        easier.
        """
        if not query:
            query = cls.query
        if not include_deleted:
            query = query.filter(Job.deleted == None)
        if not include_to_delete:
            query = query.filter(Job.to_delete == None)
        if complete_days:
            #This takes the same kw names as timedelta
            query = cls.complete_delta({'days':int(complete_days)}, query)
        if family:
            try:
                OSMajor.by_name(family)
            except NoResultFound:
                err_msg = _(u'Family is invalid: %s') % family
                log.exception(err_msg)
                raise BX(err_msg)

            query =cls.has_family(family, query)
        if tag:
            if len(tag) == 1:
                tag = tag[0]
            try:
                query = cls.by_tag(tag, query)
            except NoResultFound:
                err_msg = _('Tag is invalid: %s') % tag
                log.exception(err_msg)
                raise BX(err_msg)

        if product:
            if len(product) == 1:
                product = product[0]
            try:
                query = cls.by_product(product,query)
            except NoResultFound:
                err_msg = _('Product is invalid: %s') % product
                log.exception(err_msg)
                raise BX(err_msg)
        if owner:
            try:
                query = cls.by_owner(owner, query)
            except NoResultFound:
                err_msg = _('Owner is invalid: %s') % owner
                log.exception(err_msg)
                raise BX(err_msg)
        return query

    @classmethod
    def cancel_jobs_by_user(cls, user, msg = None):
        jobs = Job.query.filter(and_(Job.owner == user,
                                     Job.status.in_([s for s in TaskStatus if not s.finished])))
        for job in jobs:
            job.cancel(msg=msg)

    @classmethod
    def delete_jobs(cls, jobs=None, query=None):
        jobs_to_delete  = cls._delete_criteria(jobs,query)

        for job in jobs_to_delete:
            job.soft_delete()

        return jobs_to_delete

    @classmethod
    def _delete_criteria(cls, jobs=None, query=None):
        """Returns valid jobs for deletetion


           takes either a list of Job objects or a query object, and returns
           those that are valid for deletion


        """
        if not jobs and not query:
            raise BeakerException('Need to pass either list of jobs or a query to _delete_criteria')
        valid_jobs = []
        if jobs:
            for j in jobs:
                if j.is_finished() and not j.counts_as_deleted():
                    valid_jobs.append(j)
            return valid_jobs
        elif query:
            query = query.filter(cls.status.in_([status for status in TaskStatus if status.finished]))
            query = query.filter(and_(Job.to_delete == None, Job.deleted == None))
            query = query.filter(Job.owner==identity.current.user)
            return query

    def delete(self):
        """Deletes entries relating to a Job and it's children

            currently only removes log entries of a job and child tasks and marks
            the job as deleted.
            It does not delete other mapped relations or the job row itself.
            it does not remove log FS entries


        """
        for rs in self.recipesets:
            rs.delete()
        self.deleted = datetime.utcnow()

    def counts_as_deleted(self):
        return self.deleted or self.to_delete

    def build_ancestors(self, *args, **kw):
        """
        I have no ancestors
        """
        return ()

    def set_response(self, response):
        for rs in self.recipesets:
            rs.set_response(response)

    def requires_product(self):
        return self.retention_tag.requires_product()

    def soft_delete(self, *args, **kw):
        if self.deleted:
            raise BeakerException(u'%s has already been deleted, cannot delete it again' % self.t_id)
        if self.to_delete:
            raise BeakerException(u'%s is already marked to delete' % self.t_id)
        self.to_delete = datetime.utcnow()

    def get_log_dirs(self):
        logs = []
        for rs in self.recipesets:
            rs_logs = rs.get_log_dirs()
            if rs_logs:
                logs.extend(rs_logs)
        return logs

    @property
    def all_logs(self):
        return sum([rs.all_logs for rs in self.recipesets], [])

    def clone_link(self):
        """ return link to clone this job
        """
        return url("/jobs/clone?job_id=%s" % self.id)

    def cancel_link(self):
        """ return link to cancel this job
        """
        return url("/jobs/cancel?id=%s" % self.id)

    def is_owner(self,user):
        if self.owner == user:
            return True
        return False

    def priority_settings(self, prefix, colspan='1'):
        span = Element('span')
        title = Element('td')
        title.attrib['class']='title'
        title.text = "Set all RecipeSet priorities"
        content = Element('td')
        content.attrib['colspan'] = colspan
        for p in TaskPriority:
            id = '%s%s' % (prefix, self.id)
            a_href = make_fake_link(p.value, id, p.value)
            content.append(a_href)

        span.append(title)
        span.append(content)
        return span

    def retention_settings(self,prefix,colspan='1'):
        span = Element('span')
        title = Element('td')
        title.attrib['class']='title'
        title.text = "Set all RecipeSet tags"
        content = Element('td')
        content.attrib['colspan'] = colspan
        tags = RetentionTag.query.all()
        for t in tags:
            id = '%s%s' % (u'retentiontag_job_', self.id)
            a_href = make_fake_link(unicode(t.id), id, t.tag)
            content.append(a_href)
        span.append(title)
        span.append(content)
        return span

    def _create_job_elem(self,clone=False, *args, **kw):
        job = xmldoc.createElement("job")
        if not clone:
            job.setAttribute("id", "%s" % self.id)
            job.setAttribute("owner", "%s" % self.owner.email_address)
            job.setAttribute("result", "%s" % self.result)
            job.setAttribute("status", "%s" % self.status)
        if self.cc:
            notify = xmldoc.createElement('notify')
            for email_address in self.cc:
                notify.appendChild(node('cc', email_address))
            job.appendChild(notify)
        job.setAttribute("retention_tag", "%s" % self.retention_tag.tag)
        if self.group:
            job.setAttribute("group", "%s" % self.group.group_name)
        if self.product:
            job.setAttribute("product", "%s" % self.product.name)
        job.appendChild(node("whiteboard", self.whiteboard or ''))
        return job

    def to_xml(self, clone=False, *args, **kw):
        job = self._create_job_elem(clone)
        for rs in self.recipesets:
            job.appendChild(rs.to_xml(clone))
        return job

    def cancel(self, msg=None):
        """
        Method to cancel all unfinished tasks in this job.
        """
        for recipeset in self.recipesets:
            for recipe in recipeset.recipes:
                for task in recipe.tasks:
                    if not task.is_finished():
                        task._abort_cancel(TaskStatus.cancelled, msg)
        self._mark_dirty()

    def abort(self, msg=None):
        """
        Method to abort all unfinished tasks in this job.
        """
        for recipeset in self.recipesets:
            for recipe in recipeset.recipes:
                for task in recipe.tasks:
                    if not task.is_finished():
                        task._abort_cancel(TaskStatus.aborted, msg)
        self._mark_dirty()

    def task_info(self):
        """
        Method for exporting job status for TaskWatcher
        """
        return dict(
                    id              = "J:%s" % self.id,
                    worker          = None,
                    state_label     = "%s" % self.status,
                    state           = self.status.value,
                    method          = "%s" % self.whiteboard,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
                    #subtask_id_list = ["R:%s" % r.id for r in self.all_recipes]
                   )

    def all_recipes(self):
        """
        Return all recipes
        """
        for recipeset in self.recipesets:
            for recipe in recipeset.recipes:
                yield recipe
    all_recipes = property(all_recipes)

    def update_status(self):
        self._update_status()
        self._mark_clean()

    def _mark_dirty(self):
        self.dirty_version = uuid.uuid4()

    def _mark_clean(self):
        self.clean_version = self.dirty_version

    @property
    def is_dirty(self):
        return (self.dirty_version != self.clean_version)

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = TaskResult.min()
        min_status = TaskStatus.max()
        for recipeset in self.recipesets:
            recipeset._update_status()
            self.ptasks += recipeset.ptasks
            self.wtasks += recipeset.wtasks
            self.ftasks += recipeset.ftasks
            self.ktasks += recipeset.ktasks
            if recipeset.status.severity < min_status.severity:
                min_status = recipeset.status
            if recipeset.result.severity > max_result.severity:
                max_result = recipeset.result
        status_changed = self._change_status(min_status)
        self.result = max_result
        if status_changed and self.is_finished():
            # Send email notification
            mail.job_notify(self)

    #def t_id(self):
    #    return "J:%s" % self.id
    #t_id = property(t_id)

    @property
    def link(self):
        return make_link(url='/jobs/%s' % self.id, text=self.t_id)

    def can_stop(self, user=None):
        """Return True iff the given user can stop the job"""
        can_stop = self._can_administer(user)
        if not can_stop and user:
            can_stop = user.has_permission('stop_task')
        return can_stop

    def can_change_priority(self, user=None):
        """Return True iff the given user can change the priority"""
        can_change = self._can_administer(user) or self._can_administer_old(user)
        if not can_change and user:
            can_change = user.in_group(['admin','queue_admin'])
        return can_change

    def can_change_whiteboard(self, user=None):
        """Returns True iff the given user can change the whiteboard"""
        return self._can_administer(user) or self._can_administer_old(user)

    def can_change_product(self, user=None):
        """Returns True iff the given user can change the product"""
        return self._can_administer(user) or self._can_administer_old(user)

    def can_change_retention_tag(self, user=None):
        """Returns True iff the given user can change the retention tag"""
        return self._can_administer(user) or self._can_administer_old(user)

    def can_delete(self, user=None):
        """Returns True iff the given user can delete the job"""
        return self._can_administer(user) or self._can_administer_old(user)

    def can_cancel(self, user=None):
        """Returns True iff the given user can cancel the job"""
        return self._can_administer(user)

    def can_set_response(self, user=None):
        """Returns True iff the given user can set the response to this job"""
        return self._can_administer(user) or self._can_administer_old(user)

    def _can_administer(self, user=None):
        """Returns True iff the given user can administer the Job.

        Admins, group job members, job owners, and submitters
        can administer a job.
        """
        if user is None:
            return False
        if self.group:
            if self.group in user.groups:
                return True
        return self.is_owner(user) or user.is_admin() or \
            self.submitter == user

    def _can_administer_old(self, user):
        """
        This fills the gap between the new permissions system with group
        jobs and the old permission model without it.

        XXX Using a config option to enable this deprecated function.
        This code will be removed. Eventually. See BZ#1000861
        """
        if not get('beaker.deprecated_job_group_permissions.on', True):
            return False
        if not user:
            return False
        return bool(set(user.groups).intersection(set(self.owner.groups)))

    cc = association_proxy('_job_ccs', 'email_address')

class JobCc(MappedObject):

    def __init__(self, email_address):
        super(JobCc, self).__init__()
        self.email_address = email_address


class Product(MappedObject):

    def __init__(self, name):
        super(Product, self).__init__()
        self.name = name

    @classmethod
    def by_id(cls, id):
        return cls.query.filter(cls.id == id).one()

    @classmethod
    def by_name(cls, name):
        try:
            return cls.query.filter(cls.name == name).one()
        except NoResultFound:
            raise ValueError('No such product %r' % name)

class BeakerTag(MappedObject):


    def __init__(self, tag, *args, **kw):
        super(BeakerTag, self).__init__()
        self.tag = tag

    def can_delete(self):
        raise NotImplementedError("Please implement 'can_delete'  on %s" % self.__class__.__name__)

    @classmethod
    def by_id(cls, id, *args, **kw):
        return cls.query.filter(cls.id==id).one()

    @classmethod
    def by_tag(cls, tag, *args, **kw):
        return cls.query.filter(cls.tag==tag).one()

    @classmethod
    def get_all(cls, *args, **kw):
        return cls.query


class RetentionTag(BeakerTag):

    def __init__(self, tag, is_default=False, needs_product=False, expire_in_days=None, *args, **kw):
        self.needs_product = needs_product
        self.expire_in_days = expire_in_days
        self.set_default_val(is_default)
        self.needs_product = needs_product
        super(RetentionTag, self).__init__(tag, **kw)

    @classmethod
    def by_name(cls,tag):
        try:
            return cls.query.filter_by(tag=tag).one()
        except NoResultFound:
            raise ValueError('No such retention tag %r' % tag)

    def can_delete(self):
        if self.is_default:
            return False
        # At the moment only jobs use this tag, update this if that ever changes
        # Only remove tags that haven't been used
        return not bool(Job.query.filter(Job.retention_tag == self).count())

    def requires_product(self):
        return self.needs_product

    def get_default_val(self):
        return self.is_default

    def set_default_val(self, is_default):
        if is_default:
            try:
                current_default = self.get_default()
                current_default.is_default = False
            except InvalidRequestError, e: pass
        self.is_default = is_default
    default = property(get_default_val,set_default_val)

    @classmethod
    def get_default(cls, *args, **kw):
        return cls.query.filter(cls.is_default==True).one()

    @classmethod
    def list_by_requires_product(cls, requires=True, *args, **kw):
        return cls.query.filter(cls.needs_product == requires).all()

    @classmethod
    def list_by_tag(cls, tag, anywhere=True, *args, **kw):
        if anywhere is True:
            q = cls.query.filter(cls.tag.like('%%%s%%' % tag))
        else:
            q = cls.query.filter(cls.tag.like('%s%%' % tag))
        return q

    @classmethod
    def get_transient(cls):
        return cls.query.filter(cls.expire_in_days != 0).all()

    def __repr__(self, *args, **kw):
        return self.tag

class Response(MappedObject):

    @classmethod
    def get_all(cls,*args,**kw):
        return cls.query

    @classmethod
    def by_response(cls,response,*args,**kw):
        return cls.query.filter_by(response = response).one()

    def __repr__(self):
        return self.response

    def __str__(self):
        return self.response

class RecipeSetResponse(MappedObject):
    """
    An acknowledgment of a RecipeSet's results. Can be used for filtering reports
    """

    def __init__(self,type=None,response_id=None,comment=None):
        super(RecipeSetResponse, self).__init__()
        if response_id is not None:
            res = Response.by_id(response_id)
        elif type is not None:
            res = Response.by_response(type)
        self.response = res
        self.comment = comment

    @classmethod
    def by_id(cls,id):
        return cls.query.filter_by(recipe_set_id=id).one()

    @classmethod
    def by_jobs(cls,job_ids):
        if isinstance(job_ids, list):
            clause = Job.id.in_(job_ids)
        elif isinstance(job_ids, int):
            clause = Job.id == job_ids
        else:
            raise BeakerException('job_ids needs to be either type \'int\' or \'list\'. Found %s' % type(job_ids))
        queri = cls.query.outerjoin('recipesets','job').filter(clause)
        results = {}
        for elem in queri:
            results[elem.recipe_set_id] = elem.comment
        return results

class RecipeSet(TaskBase):
    """
    A Collection of Recipes that must be executed at the same time.
    """
    stop_types = ['abort','cancel']

    def __init__(self, ttasks=0, priority=None):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.ttasks = ttasks
        self.priority = priority

    def get_log_dirs(self):
        logs = []
        for recipe in self.recipes:
            r_logs = recipe.get_log_dirs()
            if r_logs:
                logs.extend(r_logs)
        return logs

    @property
    def all_logs(self):
        return sum([recipe.all_logs for recipe in self.recipes], [])

    def set_response(self, response):
        if self.nacked is None:
            self.nacked = RecipeSetResponse(type=response)
        else:
            self.nacked.response = Response.by_response(response)

    def is_owner(self,user):
        if self.owner == user:
            return True
        return False

    def can_set_response(self, user=None):
        """Return True iff the given user can change the response to this recipeset"""
        return self.job.can_set_response(user)

    def can_stop(self, user=None):
        """Returns True iff the given user can stop this recipeset"""
        return self.job.can_stop(user)

    def can_cancel(self, user=None):
        """Returns True iff the given user can cancel this recipeset"""
        return self.job.can_cancel(user)

    def build_ancestors(self, *args, **kw):
        """
        return a tuple of strings containing the Recipes RS and J
        """
        return (self.job.t_id,)

    def owner(self):
        return self.job.owner
    owner = property(owner)

    def to_xml(self, clone=False, from_job=True, *args, **kw):
        recipeSet = xmldoc.createElement("recipeSet")
        recipeSet.setAttribute('priority', unicode(self.priority))
        return_node = recipeSet

        if not clone:
            response = self.get_response()
            if response:
                recipeSet.setAttribute('response','%s' % str(response))

        if not clone:
            recipeSet.setAttribute("id", "%s" % self.id)

        for r in self.machine_recipes:
            recipeSet.appendChild(r.to_xml(clone, from_recipeset=True))
        if not from_job:
            job = self.job._create_job_elem(clone)
            job.appendChild(recipeSet)
            return_node = job
        return return_node

    @property
    def machine_recipes(self):
        for recipe in self.recipes:
            if not isinstance(recipe, GuestRecipe):
                yield recipe

    def delete(self):
        for r in self.recipes:
            r.delete()

    @classmethod
    def allowed_priorities_initial(cls,user):
        if not user:
            return
        if user.in_group(['admin','queue_admin']):
            return [pri for pri in TaskPriority]
        default = TaskPriority.default_priority()
        return [pri for pri in TaskPriority
                if TaskPriority.index(pri) < TaskPriority.index(default)]

    @classmethod
    def by_tag(cls, tag, query=None):
        if query is None:
            query = cls.query
        if type(tag) is list:
            tag_query = cls.retention_tag_id.in_([RetentionTag.by_tag(unicode(t)).id for t in tag])
        else:
            tag_query = cls.retention_tag==RetentionTag.by_tag(unicode(tag))

        return query.filter(tag_query)

    @classmethod
    def by_datestamp(cls, datestamp, query=None):
        if not query:
            query=cls.query
        return query.filter(RecipeSet.queue_time <= datestamp)

    @classmethod
    def by_id(cls,id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_job_id(cls,job_id):
        queri = RecipeSet.query.outerjoin('job').filter(Job.id == job_id)
        return queri

    def cancel(self, msg=None):
        """
        Method to cancel all unfinished tasks in this recipe set.
        """
        for recipe in self.recipes:
            for task in recipe.tasks:
                if not task.is_finished():
                    task._abort_cancel(TaskStatus.cancelled, msg)
        self.job._mark_dirty()

    def abort(self, msg=None):
        """
        Method to abort all unfinished tasks in this recipe set.
        """
        for recipe in self.recipes:
            for task in recipe.tasks:
                if not task.is_finished():
                    task._abort_cancel(TaskStatus.aborted, msg)
        self.job._mark_dirty()

    @property
    def is_dirty(self):
        return self.job.is_dirty

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = TaskResult.min()
        min_status = TaskStatus.max()
        for recipe in self.recipes:
            recipe._update_status()
            self.ptasks += recipe.ptasks
            self.wtasks += recipe.wtasks
            self.ftasks += recipe.ftasks
            self.ktasks += recipe.ktasks
            if recipe.status.severity < min_status.severity:
                min_status = recipe.status
            if recipe.result.severity > max_result.severity:
                max_result = recipe.result
        self._change_status(min_status)
        self.result = max_result

        # Return systems if recipeSet finished
        if self.is_finished():
            for recipe in self.recipes:
                recipe.cleanup()

    def machine_recipes_orderby(self, labcontroller):
        query = select([recipe_table.c.id,
                        func.count(System.id).label('count')],
                        from_obj=[recipe_table,
                                  system_recipe_map,
                                  system_table,
                                  recipe_set_table,
                                  lab_controller_table],
                        whereclause="recipe.id = system_recipe_map.recipe_id \
                             AND  system.id = system_recipe_map.system_id \
                             AND  system.lab_controller_id = lab_controller.id \
                             AND  recipe_set.id = recipe.recipe_set_id \
                             AND  recipe_set.id = %s \
                             AND  lab_controller.id = %s" % (self.id,
                                                            labcontroller.id),
                        group_by=[Recipe.id],
                        order_by='count')
        return map(lambda x: MachineRecipe.query.filter_by(id=x[0]).first(), session.connection(RecipeSet).execute(query).fetchall())

    def get_response(self):
        response = getattr(self.nacked,'response',None)
        return response

    def task_info(self):
        """
        Method for exporting RecipeSet status for TaskWatcher
        """
        return dict(
                    id              = "RS:%s" % self.id,
                    worker          = None,
                    state_label     = "%s" % self.status,
                    state           = self.status.value,
                    method          = None,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
                    #subtask_id_list = ["R:%s" % r.id for r in self.recipes]
                   )

    def allowed_priorities(self,user):
        if not user:
            return []
        if user.in_group(['admin','queue_admin']):
            return [pri for pri in TaskPriority]
        elif user == self.job.owner:
            return [pri for pri in TaskPriority
                    if TaskPriority.index(pri) <= TaskPriority.index(self.priority)]

    def cancel_link(self):
        """ return link to cancel this recipe
        """
        return url("/recipesets/cancel?id=%s" % self.id)

    def clone_link(self):
        """ return link to clone this recipe
        """
        return url("/jobs/clone?recipeset_id=%s" % self.id)


class Recipe(TaskBase):
    """
    Contains requires for host selection and distro selection.
    Also contains what tasks will be executed.
    """
    stop_types = ['abort','cancel']

    def __init__(self, ttasks=0):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.ttasks = ttasks

    def crypt_root_password(self):
        if self.recipeset.job.group:
            group_pw = self.recipeset.job.group.root_password
            if group_pw:
                if len(group_pw.split('$')) != 4:
                    salt = ''.join(random.choice(string.digits + string.ascii_letters)
                                   for i in range(8))
                    return crypt.crypt(group_pw, "$1$%s$" % salt)
                else:
                    return group_pw
        # if it is not a group job or the group password is not set
        return self.owner.root_password

    @property
    def harnesspath(self):
        return get('basepath.harness', '/var/www/beaker/harness')

    @property
    def repopath(self):
        return get('basepath.repos', '/var/www/beaker/repos')

    def is_owner(self,user):
        return self.recipeset.job.owner == user

    def is_deleted(self):
        if self.recipeset.job.deleted or self.recipeset.job.to_delete:
            return True
        return False

    def build_ancestors(self, *args, **kw):
        """
        return a tuple of strings containing the Recipes RS and J
        """
        return (self.recipeset.job.t_id, self.recipeset.t_id)

    def clone_link(self):
        """ return link to clone this recipe
        """
        return url("/jobs/clone?recipeset_id=%s" % self.recipeset.id)

    @property
    def link(self):
        """ Return a link to this recipe. """
        return make_link(url='/recipes/%s' % self.id, text=self.t_id,
                elem_class='recipe-id')

    def filepath(self):
        """
        Return file path for this recipe
        """
        job    = self.recipeset.job
        return "%s/%02d/%s/%s/%s" % (self.recipeset.queue_time.year,
                self.recipeset.queue_time.month,
                job.id // Log.MAX_ENTRIES_PER_DIRECTORY, job.id, self.id)
    filepath = property(filepath)

    def get_log_dirs(self):
        recipe_logs = self._get_log_dirs()
        for task in self.tasks:
            rt_log = task.get_log_dirs()
            if rt_log:
                recipe_logs.extend(rt_log)
        return recipe_logs

    def owner(self):
        return self.recipeset.job.owner
    owner = property(owner)

    def delete(self):
        """
        How we delete a Recipe.
        """
        self.logs = []
        if self.rendered_kickstart:
            session.delete(self.rendered_kickstart)
            self.rendered_kickstart = None
        for task in self.tasks:
            task.delete()

    def task_repo(self):
        return ('beaker-tasks',absolute_url('/repos/%s' % self.id,
                                            scheme='http',
                                            labdomain=True,
                                            webpath=False,
                                           )
               )

    def harness_repo(self):
        """
        return repos needed for harness and task install
        """
        if self.distro_tree:
            if os.path.exists("%s/%s" % (self.harnesspath,
                                            self.distro_tree.distro.osversion.osmajor)):
                return ('beaker-harness',
                    absolute_url('/harness/%s/' %
                                 self.distro_tree.distro.osversion.osmajor,
                                 scheme='http',
                                 labdomain=True,
                                 webpath=False,
                                )
                       )

    def generated_install_options(self):
        ks_meta = {
            'packages': ':'.join(p.package for p in self.packages),
            'customrepos': [dict(repo_id=r.name, path=r.url) for r in self.repos],
            'harnessrepo': '%s,%s' % self.harness_repo(),
            'taskrepo': '%s,%s' % self.task_repo(),
            'partitions': self.partitionsKSMeta,
        }
        return InstallOptions(ks_meta, {}, {})

    def to_xml(self, recipe, clone=False, from_recipeset=False, from_machine=False):
        if not clone:
            recipe.setAttribute("id", "%s" % self.id)
            recipe.setAttribute("job_id", "%s" % self.recipeset.job_id)
            recipe.setAttribute("recipe_set_id", "%s" % self.recipe_set_id)
        autopick = xmldoc.createElement("autopick")
        autopick.setAttribute("random", "%s" % unicode(self.autopick_random).lower())
        recipe.appendChild(autopick)
        recipe.setAttribute("whiteboard", "%s" % self.whiteboard and self.whiteboard or '')
        recipe.setAttribute("role", "%s" % self.role and self.role or 'RECIPE_MEMBERS')
        if self.kickstart:
            kickstart = xmldoc.createElement("kickstart")
            text = xmldoc.createCDATASection('%s' % self.kickstart)
            kickstart.appendChild(text)
            recipe.appendChild(kickstart)
        if self.rendered_kickstart and not clone:
            recipe.setAttribute('kickstart_url', self.rendered_kickstart.link)
        recipe.setAttribute("ks_meta", "%s" % self.ks_meta and self.ks_meta or '')
        recipe.setAttribute("kernel_options", "%s" % self.kernel_options and self.kernel_options or '')
        recipe.setAttribute("kernel_options_post", "%s" % self.kernel_options_post and self.kernel_options_post or '')
        if self.duration and not clone:
            recipe.setAttribute("duration", "%s" % self.duration)
        if self.result and not clone:
            recipe.setAttribute("result", "%s" % self.result)
        if self.status and not clone:
            recipe.setAttribute("status", "%s" % self.status)
        if self.distro_tree and not clone:
            recipe.setAttribute("distro", "%s" % self.distro_tree.distro.name)
            recipe.setAttribute("arch", "%s" % self.distro_tree.arch)
            recipe.setAttribute("family", "%s" % self.distro_tree.distro.osversion.osmajor)
            recipe.setAttribute("variant", "%s" % self.distro_tree.variant)
        watchdog = xmldoc.createElement("watchdog")
        if self.panic:
            watchdog.setAttribute("panic", "%s" % self.panic)
        recipe.appendChild(watchdog)
        if self.resource and self.resource.fqdn and not clone:
            recipe.setAttribute("system", "%s" % self.resource.fqdn)
        packages = xmldoc.createElement("packages")
        if self.custom_packages:
            for package in self.custom_packages:
                packages.appendChild(package.to_xml())
        recipe.appendChild(packages)

        ks_appends = xmldoc.createElement("ks_appends")
        if self.ks_appends:
            for ks_append in self.ks_appends:
                ks_appends.appendChild(ks_append.to_xml())
        recipe.appendChild(ks_appends)

        if not self.is_queued() and not clone:
            roles = xmldoc.createElement("roles")
            for role in self.roles_to_xml():
                roles.appendChild(role)
            recipe.appendChild(roles)
        repos = xmldoc.createElement("repos")
        for repo in self.repos:
            repos.appendChild(repo.to_xml())
        recipe.appendChild(repos)
        drs = xml.dom.minidom.parseString(self.distro_requires)
        hrs = xml.dom.minidom.parseString(self.host_requires)
        for dr in drs.getElementsByTagName("distroRequires"):
            recipe.appendChild(dr)
        hostRequires = xmldoc.createElement("hostRequires")
        for hr in hrs.getElementsByTagName("hostRequires"):
            for child in hr.childNodes[:]:
                hostRequires.appendChild(child)
        recipe.appendChild(hostRequires)
        prs = xml.dom.minidom.parseString(self.partitions)
        partitions = xmldoc.createElement("partitions")
        for pr in prs.getElementsByTagName("partitions"):
            for child in pr.childNodes[:]:
                partitions.appendChild(child)
        recipe.appendChild(partitions)
        for t in self.tasks:
            recipe.appendChild(t.to_xml(clone))
        if not from_recipeset and not from_machine:
            recipe = self._add_to_job_element(recipe, clone)
        return recipe

    def _add_to_job_element(self, recipe, clone):
        recipeSet = xmldoc.createElement("recipeSet")
        recipeSet.appendChild(recipe)
        job = xmldoc.createElement("job")
        if not clone:
            job.setAttribute("owner", "%s" % self.recipeset.job.owner.email_address)
        job.appendChild(node("whiteboard", self.recipeset.job.whiteboard or ''))
        job.appendChild(recipeSet)
        return job

    def _get_duration(self):
        try:
            return self.finish_time - self.start_time
        except TypeError:
            return None
    duration = property(_get_duration)

    def _get_packages(self):
        """ return all packages for all tests
        """
        packages = []
        packages.extend(TaskPackage.query
                .select_from(RecipeTask).join(Task).join(Task.required)
                .filter(RecipeTask.recipe == self)
                .order_by(TaskPackage.package).distinct())
        packages.extend(self.custom_packages)
        return packages

    packages = property(_get_packages)

    def _get_arch(self):
        if self.distro_tree:
            return self.distro_tree.arch

    arch = property(_get_arch)

    def _get_host_requires(self):
        # If no system_type is specified then add defaults
        try:
            hrs = xml.dom.minidom.parseString(self._host_requires)
        except TypeError:
            hrs = xmldoc.createElement("hostRequires")
        except xml.parsers.expat.ExpatError:
            hrs = xmldoc.createElement("hostRequires")
        if not hrs.getElementsByTagName("system_type"):
            hostRequires = xmldoc.createElement("hostRequires")
            for hr in hrs.getElementsByTagName("hostRequires"):
                for child in hr.childNodes[:]:
                    hostRequires.appendChild(child)
            system_type = xmldoc.createElement("system_type")
            system_type.setAttribute("value", "%s" % self.systemtype)
            hostRequires.appendChild(system_type)
            return hostRequires.toxml()
        else:
            return hrs.toxml()

    def _set_host_requires(self, value):
        self._host_requires = value

    host_requires = property(_get_host_requires, _set_host_requires)

    def _get_partitions(self):
        """ get _partitions """
        try:
            prs = xml.dom.minidom.parseString(self._partitions)
        except TypeError:
            prs = xmldoc.createElement("partitions")
        except xml.parsers.expat.ExpatError:
            prs = xmldoc.createElement("partitions")
        return prs.toxml()

    def _set_partitions(self, value):
        """ set _partitions """
        self._partitions = value

    partitions = property(_get_partitions, _set_partitions)

    def _partitionsKSMeta(self):
        """ Parse partitions xml into ks_meta variable which cobbler will understand """
        partitions = []
        try:
            prs = xml.dom.minidom.parseString(self.partitions)
        except TypeError:
            prs = xmldoc.createElement("partitions")
        except xml.parsers.expat.ExpatError:
            prs = xmldoc.createElement("partitions")
        for partition in prs.getElementsByTagName("partition"):
            fs = partition.getAttribute('fs')
            name = partition.getAttribute('name')
            type = partition.getAttribute('type') or 'part'
            size = partition.getAttribute('size') or '5'
            if fs:
                partitions.append('%s:%s:%s:%s' % (name, type, size, fs))
            else:
                partitions.append('%s:%s:%s' % (name, type, size))
        return ';'.join(partitions)
    partitionsKSMeta = property(_partitionsKSMeta)

    def queue(self):
        """
        Move from Processed -> Queued
        """
        for task in self.tasks:
            task._change_status(TaskStatus.queued)
        self.recipeset.job._mark_dirty()
        # purely as an optimisation
        self._change_status(TaskStatus.queued)

    def process(self):
        """
        Move from New -> Processed
        """
        for task in self.tasks:
            task._change_status(TaskStatus.processed)
        self.recipeset.job._mark_dirty()
        # purely as an optimisation
        self._change_status(TaskStatus.processed)

    def createRepo(self):
        """
        Create Recipe specific task repo based on the tasks requested.
        """
        snapshot_repo = os.path.join(self.repopath, str(self.id))
        # The repo may already exist if beakerd.virt_recipes() creates a
        # repo but the subsequent virt provisioning fails and the recipe
        # falls back to being queued on a regular system
        makedirs_ignore(snapshot_repo, 0755)
        Task.make_snapshot_repo(snapshot_repo)
        return True

    def destroyRepo(self):
        """
        Done with Repo, destroy it.
        """
        directory = '%s/%s' % (self.repopath, self.id)
        if os.path.isdir(directory):
            try:
                shutil.rmtree(directory)
            except OSError:
                if os.path.isdir(directory):
                    #something else must have gone wrong
                    raise

    def schedule(self):
        """
        Move from Queued -> Scheduled
        """
        for task in self.tasks:
            task._change_status(TaskStatus.scheduled)
        self.recipeset.job._mark_dirty()
        # purely as an optimisation
        self._change_status(TaskStatus.scheduled)

    def waiting(self):
        """
        Move from Scheduled to Waiting
        """
        for task in self.tasks:
            task._change_status(TaskStatus.waiting)
        self.recipeset.job._mark_dirty()
        # purely as an optimisation
        self._change_status(TaskStatus.waiting)

    def cancel(self, msg=None):
        """
        Method to cancel all unfinished tasks in this recipe.
        """
        for task in self.tasks:
            if not task.is_finished():
                task._abort_cancel(TaskStatus.cancelled, msg)
        self.recipeset.job._mark_dirty()

    def abort(self, msg=None):
        """
        Method to abort all unfinished tasks in this recipe.
        """
        for task in self.tasks:
            if not task.is_finished():
                task._abort_cancel(TaskStatus.aborted, msg)
        self.recipeset.job._mark_dirty()

    @property
    def is_dirty(self):
        return self.recipeset.job.is_dirty

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0

        max_result = TaskResult.min()
        min_status = TaskStatus.max()
        # I think this loop could be replaced with some sql which would be more efficient.
        for task in self.tasks:
            task._update_status()
            if task.is_finished():
                if task.result == TaskResult.pass_:
                    self.ptasks += 1
                if task.result == TaskResult.warn:
                    self.wtasks += 1
                if task.result == TaskResult.fail:
                    self.ftasks += 1
                if task.result == TaskResult.panic:
                    self.ktasks += 1
            if task.status.severity < min_status.severity:
                min_status = task.status
            if task.result.severity > max_result.severity:
                max_result = task.result
        if self.status.finished and not min_status.finished:
            min_status = self._fix_zombie_tasks()
        status_changed = self._change_status(min_status)
        self.result = max_result

        # Record the start of this Recipe.
        if not self.start_time \
           and self.status == TaskStatus.running:
            self.start_time = datetime.utcnow()

        if self.start_time and not self.finish_time and self.is_finished():
            # Record the completion of this Recipe.
            self.finish_time = datetime.utcnow()

        if status_changed and self.is_finished():
            metrics.increment('counters.recipes_%s' % self.status.name)
            if self.status == TaskStatus.aborted and \
                    getattr(self.resource, 'system', None) and \
                    get('beaker.reliable_distro_tag', None) in self.distro_tree.distro.tags:
                self.resource.system.suspicious_abort()

        if self.is_finished():
            # If we have any guests which haven't started, kill them now 
            # because there is no way they can ever start.
            for guest in getattr(self, 'guests', []):
                if (not guest.is_finished() and
                        guest.watchdog and not guest.watchdog.kill_time):
                    guest.abort(msg='Aborted: host %s finished but guest never started'
                            % self.t_id)

    def _fix_zombie_tasks(self):
        # It's not possible to get into this state in recent version of Beaker, 
        # but very old recipes may be finished while still having tasks that 
        # are running. We don't want to restart the recipe though, so we need 
        # to kill the zombie tasks.
        log.debug('Fixing zombie tasks in %s', self.t_id)
        assert self.is_finished()
        assert not self.watchdog
        for task in self.tasks:
            if task.status.severity < self.status.severity:
                task._change_status(self.status)
        return self.status

    def provision(self):
        if not self.harness_repo():
            raise ValueError('Failed to find repo for harness')
        from bkr.server.kickstart import generate_kickstart
        install_options = self.resource.install_options(self.distro_tree)\
                .combined_with(self.generated_install_options())\
                .combined_with(InstallOptions.from_strings(self.ks_meta,
                    self.kernel_options, self.kernel_options_post))
        if 'ks' in install_options.kernel_options:
            # Use it as is
            pass
        elif self.kickstart:
            # add in cobbler packages snippet...
            packages_slot = 0
            nopackages = True
            for line in self.kickstart.split('\n'):
                # Add the length of line + newline
                packages_slot += len(line) + 1
                if line.find('%packages') == 0:
                    nopackages = False
                    break
            beforepackages = self.kickstart[:packages_slot-1]
            afterpackages = self.kickstart[packages_slot:]
            # if no %packages section then add it
            if nopackages:
                beforepackages = "%s\n%%packages --ignoremissing" % beforepackages
                afterpackages = "{{ end }}\n%s" % afterpackages
            # Fill in basic requirements for RHTS
            if self.distro_tree.distro.osversion.osmajor.osmajor == u'RedHatEnterpriseLinux3':
                kicktemplate = """
%(beforepackages)s
{%% snippet 'rhts_packages' %%}
%(afterpackages)s

%%pre
(
{%% snippet 'rhts_pre' %%}
) 2>&1 | /usr/bin/tee /dev/console

%%post
(
{%% snippet 'rhts_post' %%}
) 2>&1 | /usr/bin/tee /dev/console
                """
            else:
                kicktemplate = """
%(beforepackages)s
{%% snippet 'rhts_packages' %%}
%(afterpackages)s

%%pre --log=/dev/console
{%% snippet 'rhts_pre' %%}
{{ end }}

%%post --log=/dev/console
{%% snippet 'rhts_post' %%}
{{ end }}
                """
            kickstart = kicktemplate % dict(
                                        beforepackages = beforepackages,
                                        afterpackages = afterpackages)
            self.rendered_kickstart = generate_kickstart(install_options,
                    distro_tree=self.distro_tree,
                    system=getattr(self.resource, 'system', None),
                    user=self.recipeset.job.owner,
                    recipe=self, kickstart=kickstart)
            install_options.kernel_options['ks'] = self.rendered_kickstart.link
        else:
            ks_appends = [ks_append.ks_append for ks_append in self.ks_appends]
            self.rendered_kickstart = generate_kickstart(install_options,
                    distro_tree=self.distro_tree,
                    system=getattr(self.resource, 'system', None),
                    user=self.recipeset.job.owner,
                    recipe=self, ks_appends=ks_appends)
            install_options.kernel_options['ks'] = self.rendered_kickstart.link

        if isinstance(self.resource, SystemResource):
            self.resource.system.configure_netboot(self.distro_tree,
                    install_options.kernel_options_str,
                    service=u'Scheduler',
                    callback=u'bkr.server.model.auto_cmd_handler')
            self.resource.system.action_power(action=u'reboot',
                                     callback=u'bkr.server.model.auto_cmd_handler')
            self.resource.system.activity.append(SystemActivity(
                    user=self.recipeset.job.owner,
                    service=u'Scheduler', action=u'Provision',
                    field_name=u'Distro Tree', old_value=u'',
                    new_value=unicode(self.distro_tree)))
        elif isinstance(self.resource, VirtResource):
            with dynamic_virt.VirtManager() as manager:
                manager.start_install(self.resource.system_name,
                        self.distro_tree, install_options.kernel_options_str,
                        self.resource.lab_controller)
            self.tasks[0].start()

    def cleanup(self):
        # Note that this may be called *many* times for a recipe, even when it 
        # has already been cleaned up, so we have to handle that gracefully 
        # (and cheaply!)
        self.destroyRepo()
        if self.resource:
            self.resource.release()
        if self.watchdog:
            session.delete(self.watchdog)
            self.watchdog = None

    def task_info(self):
        """
        Method for exporting Recipe status for TaskWatcher
        """
        worker = {}
        if self.resource:
            worker['name'] = self.resource.fqdn
        return dict(
                    id              = "R:%s" % self.id,
                    worker          = worker,
                    state_label     = "%s" % self.status,
                    state           = self.status.value,
                    method          = "%s" % self.whiteboard,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
# Disable tasks status, TaskWatcher needs to do this differently.  its very resource intesive to make
# so many xmlrpc calls.
#                    subtask_id_list = ["T:%s" % t.id for t in self.tasks],
                   )

    def extend(self, kill_time):
        """
        Extend the watchdog by kill_time seconds
        """
        if not self.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.id))
        self.watchdog.kill_time = datetime.utcnow() + timedelta(
                                                              seconds=kill_time)
        return self.status_watchdog()

    def status_watchdog(self):
        """
        Return the number of seconds left on the current watchdog if it exists.
        """
        if self.watchdog:
            delta = self.watchdog.kill_time - datetime.utcnow()
            return delta.seconds + (86400 * delta.days)
        else:
            return False

    @property
    def all_tasks(self):
        """
        Return all tasks and task-results, along with associated logs
        """
        for task in self.tasks:
            yield task
            for task_result in task.results:
                yield task_result

    @property
    def all_logs(self):
        """
        Return all logs for this recipe
        """
        return [mylog.dict for mylog in self.logs] + \
               sum([task.all_logs for task in self.tasks], [])

    def is_task_applicable(self, task):
        """ Does the given task apply to this recipe?
            ie: not excluded for this distro family or arch.
        """
        if self.distro_tree.arch in [arch.arch for arch in task.excluded_arch]:
            return False
        if self.distro_tree.distro.osversion.osmajor in [osmajor.osmajor for osmajor in task.excluded_osmajor]:
            return False
        return True

    @classmethod
    def mine(cls, owner):
        """
        A class method that can be used to search for Jobs that belong to a user
        """
        return cls.query.filter(Recipe.recipeset.has(
                RecipeSet.job.has(Job.owner == owner)))

    def peer_roles(self):
        """
        Returns dict of (role -> recipes) for all "peer" recipes (recipes in 
        the same recipe set as this recipe, *including this recipe*).
        """
        result = {}
        for peer in self.recipeset.recipes:
            result.setdefault(peer.role, []).append(peer)
        return result

    def roles_to_xml(self):
        for key, recipes in sorted(self.peer_roles().iteritems()):
            role = xmldoc.createElement("role")
            role.setAttribute("value", "%s" % key)
            for recipe in recipes:
                if recipe.resource:
                    system = xmldoc.createElement("system")
                    system.setAttribute("value", "%s" % recipe.resource.fqdn)
                    role.appendChild(system)
            yield(role)

    @property
    def first_task(self):
        return self.dyn_tasks.order_by(RecipeTask.id).first()


class GuestRecipe(Recipe):
    systemtype = 'Virtual'

    def to_xml(self, clone=False, from_recipeset=False, from_machine=False):
        recipe = xmldoc.createElement("guestrecipe")
        recipe.setAttribute("guestname", "%s" % (self.guestname or ""))
        recipe.setAttribute("guestargs", "%s" % self.guestargs)
        if self.resource and self.resource.mac_address and not clone:
            recipe.setAttribute("mac_address", "%s" % self.resource.mac_address)
        if self.distro_tree and self.recipeset.lab_controller and not clone:
            location = self.distro_tree.url_in_lab(self.recipeset.lab_controller)
            if location:
                recipe.setAttribute("location", location)
            for lca in self.distro_tree.lab_controller_assocs:
                if lca.lab_controller == self.recipeset.lab_controller:
                    scheme = urlparse.urlparse(lca.url).scheme
                    attr = '%s_location' % re.sub(r'[^a-z0-9]+', '_', scheme.lower())
                    recipe.setAttribute(attr, lca.url)

        return Recipe.to_xml(self, recipe, clone, from_recipeset, from_machine)

    def _add_to_job_element(self, guestrecipe, clone):
        recipe = xmldoc.createElement('recipe')
        if self.resource and not clone:
            recipe.setAttribute('system', '%s' % self.hostrecipe.resource.fqdn)
        recipe.appendChild(guestrecipe)
        job = super(GuestRecipe, self)._add_to_job_element(recipe, clone)
        return job

    def _get_distro_requires(self):
        try:
            drs = xml.dom.minidom.parseString(self._distro_requires)
        except TypeError:
            drs = xmldoc.createElement("distroRequires")
        except xml.parsers.expat.ExpatError:
            drs = xmldoc.createElement("distroRequires")
        return drs.toxml()

    def _set_distro_requires(self, value):
        self._distro_requires = value

    def t_id(self):
        return 'R:%s' % self.id
    t_id = property(t_id)

    distro_requires = property(_get_distro_requires, _set_distro_requires)

class MachineRecipe(Recipe):
    """
    Optionally can contain guest recipes which are just other recipes
      which will be executed on this system.
    """
    systemtype = 'Machine'
    def to_xml(self, clone=False, from_recipeset=False):
        recipe = xmldoc.createElement("recipe")
        for guest in self.guests:
            recipe.appendChild(guest.to_xml(clone, from_machine=True))
        return Recipe.to_xml(self, recipe, clone, from_recipeset)

    def check_virtualisability(self):
        """
        Decide whether this recipe can be run as a virt guest
        """
        # oVirt is i386/x86_64 only
        if self.distro_tree.arch.arch not in [u'i386', u'x86_64']:
            return RecipeVirtStatus.precluded
        # Can't run VMs in a VM
        if self.guests:
            return RecipeVirtStatus.precluded
        # Multihost testing won't work (for now!)
        if len(self.recipeset.recipes) > 1:
            return RecipeVirtStatus.precluded
        # Check we can translate any host requirements into VM params
        # Delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import vm_params, NotVirtualisable
        try:
            vm_params(self.host_requires)
        except NotVirtualisable:
            return RecipeVirtStatus.precluded
        # Checks all passed, so dynamic virt should be attempted
        return RecipeVirtStatus.possible

    @classmethod
    def get_queue_stats(cls, recipes=None):
        """Returns a dictionary of status:count pairs for active recipes"""
        if recipes is None:
            recipes = cls.query
        active_statuses = [s for s in TaskStatus if not s.finished]
        query = (recipes.group_by(cls.status)
                  .having(cls.status.in_(active_statuses))
                  .values(cls.status, func.count(cls.id)))
        result = dict((status.name, 0) for status in active_statuses)
        result.update((status.name, count) for status, count in query)
        return result

    @classmethod
    def get_queue_stats_by_group(cls, grouping, recipes=None):
        """Returns a mapping from named groups to dictionaries of status:count pairs for active recipes
        """
        if recipes is None:
            recipes = cls.query
        active_statuses = [s for s in TaskStatus if not s.finished]
        query = (recipes.with_entities(grouping,
                                       cls.status,
                                       func.count(cls.id))
                 .group_by(grouping, cls.status)
                 .having(cls.status.in_(active_statuses)))
        def init_group_stats():
            return dict((status.name, 0) for status in active_statuses)
        result = defaultdict(init_group_stats)
        for group, status, count in query:
            result[group][status.name] = count
        return result

    def _get_distro_requires(self):
        return self._distro_requires

    def _set_distro_requires(self, value):
        self._distro_requires = value

    def t_id(self):
        return 'R:%s' % self.id
    t_id = property(t_id)

    distro_requires = property(_get_distro_requires, _set_distro_requires)


class RecipeTag(MappedObject):
    """
    Each recipe can be tagged with information that identifies what is being
    executed.  This is helpful when generating reports.
    """
    pass


class RecipeTask(TaskBase):
    """
    This holds the results/status of the task being executed.
    """
    result_types = ['pass_','warn','fail','panic', 'result_none']
    stop_types = ['stop','abort','cancel']

    def __init__(self, task):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.task = task

    def delete(self):
        self.logs = []
        for r in self.results:
            r.delete()

    def filepath(self):
        """
        Return file path for this task
        """
        job    = self.recipe.recipeset.job
        recipe = self.recipe
        return "%s/%02d/%s/%s/%s/%s" % (recipe.recipeset.queue_time.year,
                recipe.recipeset.queue_time.month,
                job.id // Log.MAX_ENTRIES_PER_DIRECTORY, job.id,
                recipe.id, self.id)
    filepath = property(filepath)

    def build_ancestors(self, *args, **kw):
        return (self.recipe.recipeset.job.t_id, self.recipe.recipeset.t_id, self.recipe.t_id)

    def get_log_dirs(self):
        recipe_task_logs = self._get_log_dirs()
        for result in self.results:
            rtr_log = result.get_log_dirs()
            if rtr_log:
                recipe_task_logs.extend(rtr_log)
        return recipe_task_logs

    def to_xml(self, clone=False, *args, **kw):
        task = xmldoc.createElement("task")
        task.setAttribute("name", "%s" % self.task.name)
        task.setAttribute("role", "%s" % self.role and self.role or 'STANDALONE')
        if not clone:
            task.setAttribute("id", "%s" % self.id)
            task.setAttribute("avg_time", "%s" % self.task.avg_time)
            task.setAttribute("result", "%s" % self.result)
            task.setAttribute("status", "%s" % self.status)
            rpm = xmldoc.createElement("rpm")
            name = self.task.rpm[:self.task.rpm.find('-%s' % self.task.version)]
            rpm.setAttribute("name", name)
            rpm.setAttribute("path", "%s" % self.task.path)
            task.appendChild(rpm)
        if self.duration and not clone:
            task.setAttribute("duration", "%s" % self.duration)
        if not self.is_queued() and not clone:
            roles = xmldoc.createElement("roles")
            for role in self.roles_to_xml():
                roles.appendChild(role)
            task.appendChild(roles)
        params = xmldoc.createElement("params")
        for p in self.params:
            params.appendChild(p.to_xml())
        task.appendChild(params)
        if self.results and not clone:
            results = xmldoc.createElement("results")
            for result in self.results:
                results.appendChild(result.to_xml())
            task.appendChild(results)
        return task

    def _get_duration(self):
        duration = None
        if self.finish_time and self.start_time:
            duration =  self.finish_time - self.start_time
        elif self.watchdog and self.watchdog.kill_time:
            duration =  'Time Remaining %.7s' % (self.watchdog.kill_time - datetime.utcnow())
        return duration
    duration = property(_get_duration)

    def path(self):
        return self.task.name
    path = property(path)

    def link_id(self):
        """ Return a link to this Executed Recipe->Task
        """
        return make_link(url = '/recipes/%s#task%s' % (self.recipe.id, self.id),
                         text = 'T:%s' % self.id)

    link_id = property(link_id)

    def link(self):
        """ Return a link to this Task
        """
        return make_link(url = '/tasks/%s' % self.task.id,
                         text = self.task.name)

    link = property(link)

    @property
    def all_logs(self):
        return [mylog.dict for mylog in self.logs] + \
               sum([result.all_logs for result in self.results], [])

    @property
    def is_dirty(self):
        return False

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        # The self.result == TaskResult.new condition is just an optimisation 
        # to avoid constantly recomputing the result after the task is finished
        if self.is_finished() and self.result == TaskResult.new:
            max_result = TaskResult.min()
            for result in self.results:
                if result.result.severity > max_result.severity:
                    max_result = result.result
            self.result = max_result

    def start(self, watchdog_override=None):
        """
        Record the start of this task
         If watchdog_override is defined we will use that time instead
         of what the tasks default time is.  This should be defined in number
         of seconds
        """
        if self.is_finished():
            raise BX(_('Cannot restart finished task'))
        if not self.recipe.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.recipe.id))
        if not self.start_time:
            self.start_time = datetime.utcnow()
        self._change_status(TaskStatus.running)
        self.recipe.watchdog.recipetask = self
        if watchdog_override:
            self.recipe.watchdog.kill_time = watchdog_override
        else:
            # add in 30 minutes at a minimum
            self.recipe.watchdog.kill_time = datetime.utcnow() + timedelta(
                                                    seconds=self.task.avg_time + 1800)
        self.recipe.recipeset.job._mark_dirty()
        return True

    def extend(self, kill_time):
        """
        Extend the watchdog by kill_time seconds
        """
        return self.recipe.extend(kill_time)

    def status_watchdog(self):
        """
        Return the number of seconds left on the current watchdog if it exists.
        """
        return self.recipe.status_watchdog()

    def stop(self, *args, **kwargs):
        """
        Record the completion of this task
        """
        if not self.recipe.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.recipe.id))
        if not self.start_time:
            raise BX(_('recipe task %s was never started' % self.id))
        if self.start_time and not self.finish_time:
            self.finish_time = datetime.utcnow()
        self._change_status(TaskStatus.completed)
        self.recipe.recipeset.job._mark_dirty()
        return True

    def owner(self):
        return self.recipe.recipeset.job.owner
    owner = property(owner)

    def cancel(self, msg=None):
        """
        Cancel this task
        """
        self._abort_cancel(TaskStatus.cancelled, msg)
        self.recipe.recipeset.job._mark_dirty()

    def abort(self, msg=None):
        """
        Abort this task
        """
        self._abort_cancel(TaskStatus.aborted, msg)
        self.recipe.recipeset.job._mark_dirty()

    def _abort_cancel(self, status, msg=None):
        """
        cancel = User instigated
        abort  = Auto instigated
        """
        if self.start_time:
            self.finish_time = datetime.utcnow()
        self._change_status(status)
        self.results.append(RecipeTaskResult(recipetask=self,
                                   path=u'/',
                                   result=TaskResult.warn,
                                   score=0,
                                   log=msg))

    def pass_(self, path, score, summary):
        """
        Record a pass result
        """
        return self._result(TaskResult.pass_, path, score, summary)

    def fail(self, path, score, summary):
        """
        Record a fail result
        """
        return self._result(TaskResult.fail, path, score, summary)

    def warn(self, path, score, summary):
        """
        Record a warn result
        """
        return self._result(TaskResult.warn, path, score, summary)

    def panic(self, path, score, summary):
        """
        Record a panic result
        """
        return self._result(TaskResult.panic, path, score, summary)

    def result_none(self, path, score, summary):
        return self._result(TaskResult.none, path, score, summary)

    def _result(self, result, path, score, summary):
        """
        Record a result
        """
        if self.is_finished():
            raise ValueError('Cannot record result for finished task %s' % self.t_id)
        recipeTaskResult = RecipeTaskResult(recipetask=self,
                                   path=path,
                                   result=result,
                                   score=score,
                                   log=summary)
        self.results.append(recipeTaskResult)
        # Flush the result to the DB so we can return the id.
        session.add(recipeTaskResult)
        session.flush()
        return recipeTaskResult.id

    def task_info(self):
        """
        Method for exporting Task status for TaskWatcher
        """
        worker = {}
        if self.recipe.resource:
            worker['name'] = self.recipe.resource.fqdn
        return dict(
                    id              = "T:%s" % self.id,
                    worker          = worker,
                    state_label     = "%s" % self.status,
                    state           = self.status.value,
                    method          = "%s" % self.task.name,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
                    #subtask_id_list = ["TR:%s" % tr.id for tr in self.results]
                   )

    def no_value(self):
        return None
   
    score = property(no_value)

    def peer_roles(self):
        """
        Returns dict of (role -> recipetasks) for all "peer" RecipeTasks, 
        *including this RecipeTask*. A peer RecipeTask is one which appears at 
        the same position in another recipe from the same recipe set as this 
        recipe.
        """
        result = {}
        i = self.recipe.tasks.index(self)
        for peer in self.recipe.recipeset.recipes:
            # Roles are only shared amongst like recipe types
            if type(self.recipe) != type(peer):
                continue
            if i >= len(peer.tasks):
                # We have uneven tasks
                continue
            peertask = peer.tasks[i]
            result.setdefault(peertask.role, []).append(peertask)
        return result

    def roles_to_xml(self):
        for key, recipetasks in sorted(self.peer_roles().iteritems()):
            role = xmldoc.createElement("role")
            role.setAttribute("value", "%s" % key)
            for recipetask in recipetasks:
                if recipetask.recipe.resource:
                    system = xmldoc.createElement("system")
                    system.setAttribute("value", "%s" % recipetask.recipe.resource.fqdn)
                    role.appendChild(system)
            yield(role)

    def can_stop(self, user=None):
        """Returns True iff the given user can stop this recipe task"""
        return self.recipe.recipeset.job.can_stop(user)


class RecipeTaskParam(MappedObject):
    """
    Parameters for task execution.
    """

    def __init__(self, name, value):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.name = name
        self.value = value

    def to_xml(self):
        param = xmldoc.createElement("param")
        param.setAttribute("name", "%s" % self.name)
        param.setAttribute("value", "%s" % self.value)
        return param


class RecipeRepo(MappedObject):
    """
    Custom repos
    """

    def __init__(self, name, url):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.name = name
        self.url = url

    def to_xml(self):
        repo = xmldoc.createElement("repo")
        repo.setAttribute("name", "%s" % self.name)
        repo.setAttribute("url", "%s" % self.url)
        return repo


class RecipeKSAppend(MappedObject):
    """
    Kickstart appends
    """

    def __init__(self, ks_append):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.ks_append = ks_append

    def to_xml(self):
        ks_append = xmldoc.createElement("ks_append")
        text = xmldoc.createCDATASection('%s' % self.ks_append)
        ks_append.appendChild(text)
        return ks_append

    def __repr__(self):
        return self.ks_append

class RecipeTaskComment(MappedObject):
    """
    User comments about the task execution.
    """
    pass


class RecipeTaskBugzilla(MappedObject):
    """
    Any bugzillas filed/found due to this task execution.
    """
    pass


class RecipeRpm(MappedObject):
    """
    A list of rpms that were installed at the time.
    """
    pass


class RecipeTaskRpm(MappedObject):
    """
    the versions of the RPMS listed in the tasks runfor list.
    """
    pass


class RecipeTaskResult(TaskBase):
    """
    Each task can report multiple results
    """

    def __init__(self, recipetask=None, path=None, result=None,
            score=None, log=None):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.recipetask = recipetask
        self.path = path
        self.result = result
        self.score = score
        self.log = log

    def filepath(self):
        """
        Return file path for this result
        """
        job    = self.recipetask.recipe.recipeset.job
        recipe = self.recipetask.recipe
        task_id   = self.recipetask.id
        return "%s/%02d/%s/%s/%s/%s/%s" % (recipe.recipeset.queue_time.year,
                recipe.recipeset.queue_time.month,
                job.id // Log.MAX_ENTRIES_PER_DIRECTORY, job.id,
                recipe.id, task_id, self.id)
    filepath = property(filepath)

    def delete(self, *args, **kw):
        self.logs = []

    def to_xml(self, *args, **kw):
        """
        Return result in xml
        """
        result = xmldoc.createElement("result")
        result.setAttribute("id", "%s" % self.id)
        result.setAttribute("path", "%s" % self.path)
        result.setAttribute("result", "%s" % self.result)
        result.setAttribute("score", "%s" % self.score)
        result.appendChild(xmldoc.createTextNode("%s" % self.log))
        #FIXME Append any binary logs as URI's
        return result

    @property
    def all_logs(self):
        return [mylog.dict for mylog in self.logs]

    def get_log_dirs(self):
        return self._get_log_dirs()

    def task_info(self):
        """
        Method for exporting RecipeTaskResult status for TaskWatcher
        """
        return dict(
                    id              = "TR:%s" % self.id,
                    worker          = dict(name = "%s" % None),
                    state_label     = "%s" % self.result,
                    state           = self.result.value,
                    method          = "%s" % self.path,
                    result          = "%s" % self.result,
                    is_finished     = True,
                    is_failed       = False
                   )

    def t_id(self):
        return "TR:%s" % self.id
    t_id = property(t_id)

    @property
    def short_path(self):
        """
        Remove the parent from the begining of the path if present
        """
        if not self.path or self.path == '/':
            short_path = self.log or './'
        elif self.path.rstrip('/') == self.recipetask.task.name:
            short_path = './'
        elif self.path.startswith(self.recipetask.task.name + '/'):
            short_path = self.path.replace(self.recipetask.task.name + '/', '', 1)
        else:
            short_path = self.path
        return short_path

class RecipeResource(MappedObject):
    """
    Base class for things on which a recipe can be run.
    """

    def __str__(self):
        return unicode(self).encode('utf8')

    def __unicode__(self):
        return unicode(self.fqdn)

    @staticmethod
    def _lowest_free_mac():
        base_addr = netaddr.EUI(get('beaker.base_mac_addr', '52:54:00:00:00:00'))
        session.flush()
        # These subqueries gives all MAC addresses in use right now
        guest_mac_query = session.query(GuestResource.mac_address.label('mac_address'))\
                .filter(GuestResource.mac_address != None)\
                .join(RecipeResource.recipe).join(Recipe.recipeset)\
                .filter(not_(RecipeSet.status.in_([s for s in TaskStatus if s.finished])))
        virt_mac_query = session.query(VirtResource.mac_address.label('mac_address'))\
                .filter(VirtResource.mac_address != None)\
                .join(RecipeResource.recipe).join(Recipe.recipeset)\
                .filter(not_(RecipeSet.status.in_([s for s in TaskStatus if s.finished])))
        # This trickery finds "gaps" of unused MAC addresses by filtering for MAC
        # addresses where address + 1 is not in use.
        # We union with base address - 1 to find any gap at the start.
        # Note that this relies on the MACAddress type being represented as
        # BIGINT in the database, which lets us do arithmetic on it.
        left_side = union(guest_mac_query, virt_mac_query,
                select([int(base_addr) - 1])).alias('left_side')
        right_side = union(guest_mac_query, virt_mac_query).alias('right_side')
        free_addr = session.scalar(select([left_side.c.mac_address + 1],
                from_obj=left_side.outerjoin(right_side,
                    onclause=left_side.c.mac_address + 1 == right_side.c.mac_address))\
                .where(right_side.c.mac_address == None)\
                .where(left_side.c.mac_address + 1 >= int(base_addr))\
                .order_by(left_side.c.mac_address).limit(1))
        # The type of (left_side.c.mac_address + 1) comes out as Integer
        # instead of MACAddress, I think it's a sqlalchemy bug :-(
        return netaddr.EUI(free_addr, dialect=mac_unix_padded_dialect)

class SystemResource(RecipeResource):
    """
    For a recipe which is running on a Beaker system.
    """

    def __init__(self, system):
        super(SystemResource, self).__init__()
        self.system = system
        self.fqdn = system.fqdn

    def __repr__(self):
        return '%s(fqdn=%r, system=%r, reservation=%r)' % (
                self.__class__.__name__, self.fqdn, self.system,
                self.reservation)

    @property
    def mac_address(self):
        # XXX the type of system.mac_address should be changed to MACAddress,
        # but for now it's not
        return netaddr.EUI(self.system.mac_address, dialect=mac_unix_padded_dialect)

    @property
    def link(self):
        return make_link(url='/view/%s' % self.system.fqdn,
                         text=self.fqdn)

    def install_options(self, distro_tree):
        return self.system.install_options(distro_tree)

    def allocate(self):
        log.debug('Reserving system %s for recipe %s', self.system, self.recipe.id)
        self.reservation = self.system.reserve_for_recipe(
                                         service=u'Scheduler',
                                         user=self.recipe.recipeset.job.owner)

    def release(self):
        # system_resource rows for very old recipes may have no reservation
        if not self.reservation or self.reservation.finish_time:
            return
        log.debug('Releasing system %s for recipe %s',
            self.system, self.recipe.id)
        self.system.unreserve(service=u'Scheduler',
            reservation=self.reservation,
            user=self.recipe.recipeset.job.owner)


class VirtResource(RecipeResource):
    """
    For a MachineRecipe which is running on a virtual guest managed by 
    a hypervisor attached to Beaker.
    """

    def __init__(self, system_name):
        super(VirtResource, self).__init__()
        self.system_name = system_name

    @property
    def link(self):
        return self.fqdn # just text, not a link

    def install_options(self, distro_tree):
        # 'postreboot' is added as a hack for RHEV guests: they do not reboot
        # properly when the installation finishes, see RHBZ#751854
        return global_install_options()\
                .combined_with(distro_tree.install_options())\
                .combined_with(InstallOptions({'postreboot': None}, {}, {}))

    def allocate(self, manager, lab_controllers):
        self.mac_address = self._lowest_free_mac()
        log.debug('Creating vm with MAC address %s for recipe %s',
                self.mac_address, self.recipe.id)

        virtio_possible = True
        if self.recipe.distro_tree.distro.osversion.osmajor.osmajor == "RedHatEnterpriseLinux3":
            virtio_possible = False

        self.lab_controller = manager.create_vm(self.system_name,
                lab_controllers, self.mac_address, virtio_possible)

    def release(self):
        try:
            log.debug('Releasing vm %s for recipe %s',
                    self.system_name, self.recipe.id)
            with dynamic_virt.VirtManager() as manager:
                manager.destroy_vm(self.system_name)
        except Exception:
            log.exception('Failed to destroy vm %s, leaked!',
                    self.system_name)
            # suppress exception, nothing more we can do now


class GuestResource(RecipeResource):
    """
    For a GuestRecipe which is running on a guest associated with a parent 
    MachineRecipe.
    """

    def __repr__(self):
        return '%s(fqdn=%r, mac_address=%r)' % (self.__class__.__name__,
                self.fqdn, self.mac_address)

    @property
    def link(self):
        return self.fqdn # just text, not a link

    def install_options(self, distro_tree):
        return global_install_options().combined_with(
                distro_tree.install_options())

    def allocate(self):
        self.mac_address = self._lowest_free_mac()
        log.debug('Allocated MAC address %s for recipe %s', self.mac_address, self.recipe.id)

    def release(self):
        pass

class RenderedKickstart(MappedObject):

    def __repr__(self):
        return '%s(id=%r, kickstart=%s, url=%r)' % (self.__class__.__name__,
                self.id, '<%s chars>' % len(self.kickstart)
                if self.kickstart is not None else 'None', self.url)

    @property
    def link(self):
        if self.url:
            return self.url
        assert self.id is not None, 'not flushed?'
        url = absolute_url('/kickstart/%s' % self.id, scheme='http',
                           labdomain=True)
        return url

mapper(Watchdog, watchdog_table,
       properties = {'recipetask':relation(RecipeTask, uselist=False),
                     'recipe':relation(Recipe, uselist=False,
                                      )})

mapper(BeakerTag, beaker_tag_table,
        polymorphic_on=beaker_tag_table.c.type, polymorphic_identity=u'tag')

mapper(RetentionTag, retention_tag_table, inherits=BeakerTag,
        properties=dict(is_default=retention_tag_table.c.default_),
        polymorphic_identity=u'retention_tag')

mapper(RecipeSetActivity, recipeset_activity_table, inherits=Activity,
       polymorphic_identity=u'recipeset_activity')

mapper(Job, job_table,
        properties = {'recipesets':relation(RecipeSet, backref='job'),
                      'owner':relation(User, uselist=False,
                          backref=backref('jobs', cascade_backrefs=False),
                          primaryjoin=users_table.c.user_id ==  \
                          job_table.c.owner_id, foreign_keys=job_table.c.owner_id),
                      'submitter': relation(User, uselist=False,
                          primaryjoin=users_table.c.user_id == \
                          job_table.c.submitter_id),
                      'group': relation(Group, uselist=False,
                          backref=backref('jobs', cascade_backrefs=False)),
                      'retention_tag':relation(RetentionTag, uselist=False,
                          backref=backref('jobs', cascade_backrefs=False)),
                      'product':relation(Product, uselist=False,
                          backref=backref('jobs', cascade_backrefs=False)),
                      '_job_ccs': relation(JobCc, backref='job')})

mapper(JobCc, job_cc_table)

mapper(Product, product_table)

mapper(RecipeSetResponse,recipe_set_nacked_table,
        properties = { 'recipesets':relation(RecipeSet),
                        'response' : relation(Response,uselist=False)})

mapper(Response,response_table)

mapper(RecipeSet, recipe_set_table,
        properties = {'recipes':relation(Recipe, backref='recipeset'),
                      'activity':relation(RecipeSetActivity,
                        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                        backref='object'),
                      'lab_controller':relation(LabController, uselist=False),
                      'nacked':relation(RecipeSetResponse,cascade="all, delete-orphan",uselist=False),
                     })

mapper(LogRecipe, log_recipe_table)

mapper(LogRecipeTask, log_recipe_task_table)

mapper(LogRecipeTaskResult, log_recipe_task_result_table)

mapper(Recipe, recipe_table,
        polymorphic_on=recipe_table.c.type, polymorphic_identity=u'recipe',
        properties = {'distro_tree':relation(DistroTree, uselist=False,
                        backref=backref('recipes', cascade_backrefs=False)),
                      'resource': relation(RecipeResource, uselist=False,
                                        backref='recipe'),
                      'rendered_kickstart': relation(RenderedKickstart),
                      'watchdog':relation(Watchdog, uselist=False,
                                         cascade="all, delete, delete-orphan"),
                      'systems':relation(System,
                                         secondary=system_recipe_map,
                                         backref='queued_recipes'),
                      'dyn_systems':dynamic_loader(System,
                                         secondary=system_recipe_map,
                                         primaryjoin=recipe_table.c.id==system_recipe_map.c.recipe_id,
                                         secondaryjoin=system_table.c.id==system_recipe_map.c.system_id,
                      ),
                      'tasks':relation(RecipeTask, backref='recipe'),
                      'dyn_tasks': relation(RecipeTask, lazy='dynamic'),
                      'tags':relation(RecipeTag,
                                      secondary=recipe_tag_map,
                                      backref='recipes'),
                      'repos':relation(RecipeRepo),
                      'rpms':relation(RecipeRpm, backref='recipe'),
                      'logs':relation(LogRecipe, backref='parent',
                            cascade='all, delete-orphan'),
                      'custom_packages':relation(TaskPackage,
                                        secondary=task_packages_custom_map),
                      'ks_appends':relation(RecipeKSAppend),
                     }
      )
mapper(GuestRecipe, guest_recipe_table, inherits=Recipe,
        polymorphic_identity=u'guest_recipe')
mapper(MachineRecipe, machine_recipe_table, inherits=Recipe,
        polymorphic_identity=u'machine_recipe',
        properties = {'guests':relation(Recipe, backref=backref('hostrecipe', uselist=False),
                                        secondary=machine_guest_map)})

mapper(RecipeResource, recipe_resource_table,
        polymorphic_on=recipe_resource_table.c.type, polymorphic_identity=None,)
mapper(SystemResource, system_resource_table, inherits=RecipeResource,
        polymorphic_on=recipe_resource_table.c.type, polymorphic_identity=ResourceType.system,
        properties={
            'system': relation(System),
            'reservation': relation(Reservation, uselist=False),
        })
mapper(VirtResource, virt_resource_table, inherits=RecipeResource,
        polymorphic_on=recipe_resource_table.c.type, polymorphic_identity=ResourceType.virt,
        properties={
            'lab_controller': relation(LabController),
        })
mapper(GuestResource, guest_resource_table, inherits=RecipeResource,
        polymorphic_on=recipe_resource_table.c.type, polymorphic_identity=ResourceType.guest)

mapper(RecipeTag, recipe_tag_table)
mapper(RecipeRpm, recipe_rpm_table)
mapper(RecipeRepo, recipe_repo_table)
mapper(RecipeKSAppend, recipe_ksappend_table)

mapper(RecipeTask, recipe_task_table,
        properties = {'results':relation(RecipeTaskResult,
                                         backref='recipetask'),
                      'rpms':relation(RecipeTaskRpm),
                      'comments':relation(RecipeTaskComment,
                                          backref='recipetask'),
                      'params':relation(RecipeTaskParam),
                      'bugzillas':relation(RecipeTaskBugzilla,
                                           backref='recipetask'),
                      'task':relation(Task, uselist=False),
                      'logs':relation(LogRecipeTask, backref='parent',
                            cascade='all, delete-orphan'),
                      'watchdog':relation(Watchdog, uselist=False),
                     }
      )

mapper(RecipeTaskParam, recipe_task_param_table)
mapper(RecipeTaskComment, recipe_task_comment_table,
        properties = {'user':relation(User, uselist=False, backref='comments')})
mapper(RecipeTaskBugzilla, recipe_task_bugzilla_table)
mapper(RecipeTaskRpm, recipe_task_rpm_table)
mapper(RecipeTaskResult, recipe_task_result_table,
        properties = {'logs':relation(LogRecipeTaskResult, backref='parent',
                           cascade='all, delete-orphan'),
                     }
      )
mapper(RenderedKickstart, rendered_kickstart_table)
