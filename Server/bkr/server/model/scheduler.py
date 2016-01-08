
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os.path
import logging
from datetime import datetime, timedelta
from copy import copy
from itertools import chain
import re
import shutil
import string
import random
import crypt
import xml.dom.minidom
from collections import defaultdict
import uuid
import urlparse
import urllib
import netaddr
from kid import Element
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Index,
        Integer, Unicode, DateTime, Boolean, UnicodeText, String, Numeric)
from sqlalchemy.sql import select, union, and_, or_, not_, func, literal, exists
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import (mapper, relationship, object_mapper,
        dynamic_loader, validates, synonym, contains_eager)
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears import url
from turbogears.config import get
from turbogears.database import session
from lxml import etree
from lxml.builder import E

from bkr.common.helpers import makedirs_ignore
from bkr.server import identity, metrics, mail, dynamic_virt
from bkr.server.bexceptions import BX, BeakerException, StaleTaskStatusException, DatabaseLookupError
from bkr.server.helpers import make_link, make_fake_link
from bkr.server.hybrid import hybrid_method, hybrid_property
from bkr.server.installopts import InstallOptions, global_install_options
from bkr.server.util import absolute_url
from .types import (UUID, MACAddress, TaskResult, TaskStatus, TaskPriority,
                    ResourceType, RecipeVirtStatus, mac_unix_padded_dialect, SystemStatus)
from .base import DeclarativeMappedObject
from .activity import Activity, ActivityMixin
from .identity import User, Group
from .lab import LabController
from .distrolibrary import (OSMajor, OSVersion, Distro, DistroTree,
        LabControllerDistroTree)
from .tasklibrary import Task, TaskPackage
from .inventory import System, SystemActivity, Reservation

log = logging.getLogger(__name__)

xmldoc = xml.dom.minidom.Document()

def node(element, value):
    node = etree.Element(element)
    node.text = value
    return node

class RecipeActivity(Activity):

    __tablename__ = 'recipe_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id',
        name='recipe_activity_id_fk'), primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id',
        name='recipe_activity_recipe_id_fk'))
    object_id = synonym('recipe_id')
    object = relationship('Recipe', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'recipe_activity'}

    def object_name(self):
        return "Recipe: %s" % self.object.id

    def __json__(self):
        result = super(RecipeActivity, self).__json__()
        result['recipe'] = {
            'id': self.object.id,
            't_id': self.object.t_id,
            'recipeset': {
                'id': self.object.recipeset.id,
                't_id': self.object.recipeset.t_id,
            },
        }
        return result


class RecipeSetActivity(Activity):

    __tablename__ = 'recipeset_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    recipeset_id = Column(Integer, ForeignKey('recipe_set.id'))
    object_id = synonym('recipeset_id')
    object = relationship('RecipeSet', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'recipeset_activity'}

    def object_name(self):
        return "RecipeSet: %s" % self.object.id

    def __json__(self):
        result = super(RecipeSetActivity, self).__json__()
        result['recipeset'] = {
            'id': self.object.id,
            't_id': self.object.t_id,
            'job': {
                'id': self.object.job.id,
                't_id': self.object.job.t_id,
            },
        }
        return result

machine_guest_map =Table('machine_guest_map', DeclarativeMappedObject.metadata,
        Column('machine_recipe_id', Integer,
                ForeignKey('machine_recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('guest_recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        mysql_engine='InnoDB',
)

system_recipe_map = Table('system_recipe_map', DeclarativeMappedObject.metadata,
        Column('system_id', Integer,
                ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        mysql_engine='InnoDB',
)

system_hardware_scan_recipe_map = Table('system_hardware_scan_recipe_map', DeclarativeMappedObject.metadata,
        Column('system_id', Integer,
                ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        mysql_engine='InnoDB',
)


recipe_tag_map = Table('recipe_tag_map', DeclarativeMappedObject.metadata,
        Column('tag_id', Integer,
               ForeignKey('recipe_tag.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('recipe_id', Integer,
               ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        mysql_engine='InnoDB',
)

task_packages_custom_map = Table('task_packages_custom_map', DeclarativeMappedObject.metadata,
    Column('recipe_id', Integer, ForeignKey('recipe.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)


class JobActivity(Activity):

    __tablename__ = 'job_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    job_id = Column(Integer, ForeignKey('job.id'), nullable=False)
    object_id = synonym('job_id')
    object = relationship('Job', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'job_activity'}

    def object_name(self):
        return "Job: %s" % self.object.id

    def __json__(self):
        result = super(JobActivity, self).__json__()
        result['job'] = {'id': self.object.id, 't_id': self.object.t_id}
        return result


class Watchdog(DeclarativeMappedObject):
    """ Every running task has a corresponding watchdog which will
        Return the system if it runs too long
    """

    __tablename__ = 'watchdog'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    recipe = relationship('Recipe')
    recipetask_id = Column(Integer, ForeignKey('recipe_task.id'))
    recipetask = relationship('RecipeTask')
    subtask = Column(Unicode(255))
    kill_time = Column(DateTime)

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

        XXX Note that queries returned by this method do not function correctly
        when Recipe/RecipeSet/Job are joined via a 'chain of joins'. The mapped
        collections need to be joined in seperate and succesive calls to join().
        This appears to be a bug in sqlalchemy 0.6.8, but is no longer an issue
        in 0.8.3 (and perhaps versions in between, although currently untested).
        """
        any_recipe_has_active_watchdog = exists(select([1],
                from_obj=Recipe.__table__.join(Watchdog.__table__))\
                .where(Watchdog.kill_time > datetime.utcnow())\
                .where(Recipe.recipe_set_id == RecipeSet.id)\
                .correlate(RecipeSet.__table__))
        watchdog_query = cls.query.join(Watchdog.recipe).join(Recipe.recipeset)\
                .filter(Watchdog.kill_time != None)
        if labcontroller is not None:
            watchdog_query = watchdog_query.filter(
                RecipeSet.lab_controller==labcontroller)
        if status == 'active':
            watchdog_query = watchdog_query.filter(any_recipe_has_active_watchdog)
        elif status == 'expired':
            watchdog_query = watchdog_query.join(RecipeSet.job)\
                .filter(not_(Job.is_dirty))\
                .filter(not_(any_recipe_has_active_watchdog))
        else:
            return None
        return watchdog_query

    def __repr__(self):
        return '%s(id=%r, kill_time=%r)' % (self.__class__.__name__,
                self.id, self.kill_time)


class Log(object):

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

    id = Column(Integer, primary_key=True)
    path = Column(UnicodeText())
    filename = Column(UnicodeText(), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    server = Column(UnicodeText)
    basepath = Column(UnicodeText)

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
        super(Log, self).__init__()
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

    @property
    def combined_path(self):
        """Combines path (which is really the "subdir" of sorts) with filename:
                      , log.txt => log.txt
                /     , log.txt => log.txt
                /debug, log.txt => debug/log.txt
                debug , log.txt => debug/log.txt
        """
        return os.path.join((self.path or '').lstrip('/'), self.filename)

    @property
    def full_path(self):
        """
        Returns an absolute URL to the log if it's stored remotely, or an 
        absolute filesystem path if it's stored locally.
        """
        if self.server:
            return self.absolute_url
        else:
            return os.path.join(self.parent.logspath, self.parent.filepath,
                self.combined_path)

    @property
    def absolute_url(self):
        if self.server:
            # self.server points at a directory so it should end in 
            # a trailing slash, but older versions of the code didn't do that
            url = self.server
            if not url.endswith('/'):
                url += '/'
            return '%s%s' % (url, self.combined_path)
        else:
            return urlparse.urljoin(absolute_url('/'),
                    os.path.join('/logs', self.parent.filepath, self.combined_path))

    @property
    def link(self):
        """ Return a link to this Log
        """
        return make_link(url=self.href, text=self.combined_path)

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
                    url      = self.absolute_url,
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

class LogRecipe(Log, DeclarativeMappedObject):
    type = 'R'

    __tablename__ = 'log_recipe'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    # common column definitions are inherited from Log
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    parent = relationship('Recipe', back_populates='logs')

    @property
    def href(self):
        return '/recipes/%s/logs/%s' % (self.parent.id, self.combined_path)

class LogRecipeTask(Log, DeclarativeMappedObject):
    type = 'T'

    __tablename__ = 'log_recipe_task'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    # common column definitions are inherited from Log
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'),
            nullable=False)
    parent = relationship('RecipeTask', back_populates='logs')

    @property
    def href(self):
        return '/recipes/%s/tasks/%s/logs/%s' % (self.parent.recipe.id,
                self.parent.id, self.combined_path)

class LogRecipeTaskResult(Log, DeclarativeMappedObject):
    type = 'E'

    __tablename__ = 'log_recipe_task_result'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    # common column definitions are inherited from Log
    recipe_task_result_id = Column(Integer,
                ForeignKey('recipe_task_result.id'), nullable=False)
    parent = relationship('RecipeTaskResult', back_populates='logs')

    @property
    def href(self):
        return '/recipes/%s/tasks/%s/results/%s/logs/%s' % (
                self.parent.recipetask.recipe.id, self.parent.recipetask.id,
                self.parent.id, self.combined_path)

class TaskBase(object):

    t_id_types = dict(T = 'RecipeTask',
                      TR = 'RecipeTaskResult',
                      R = 'Recipe',
                      RS = 'RecipeSet',
                      J = 'Job')

    @property
    def logspath(self):
        return get('basepath.logs')

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
            raise BeakerException(_('You have specified an invalid task type:%s' % task_type))

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
        current_status = self.status #pylint: disable=E0203
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
    def is_failed(cls): #pylint: disable=E0213
        """
        Return SQL expression that is true if the task has failed
        """
        return cls.result.in_([TaskResult.warn,
                               TaskResult.fail,
                               TaskResult.panic])

    @hybrid_property
    def is_suspiciously_aborted(self):
        """Return True if the recipe abort was suspicious. Suspicious meaning
        that all tasks in a recipe are aborted."""
        return (all([task.status == TaskStatus.aborted for task in self.tasks]) and
                self.install_started is None)

    @is_suspiciously_aborted.expression
    def is_suspiciously_aborted(cls): # pylint: disable=E0213
        """Returns an SQL expression evaluating to TRUE if the recipe abort was
        suspicious. Note: There is no 'ALL' operator in SQL to get rid of the
        double negation."""
        return and_(not_(cls.tasks.any(RecipeTask.status != TaskStatus.aborted)),
                    RecipeResource.install_started == None)

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
        nstyle = pstyle = wstyle = fstyle = kstyle = fmt_style % 0
        completed = 0
        if getattr(self, 'ntasks', None):
            completed += self.ntasks
            nstyle = fmt_style % (100.0 * self.ntasks / self.ttasks)
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
        div.append(Element('div', {'class': 'bar bar-default', 'style': nstyle}))
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


class Job(TaskBase, DeclarativeMappedObject, ActivityMixin):
    """
    Container to hold like recipe sets.
    """

    __tablename__ = 'job'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    dirty_version = Column(UUID, nullable=False)
    clean_version = Column(UUID, nullable=False)
    owner_id = Column(Integer, ForeignKey('tg_user.user_id'), index=True)
    owner = relationship(User, back_populates='jobs',
            primaryjoin=owner_id == User.user_id)
    submitter_id = Column(Integer,
            ForeignKey('tg_user.user_id', name='job_submitter_id_fk'))
    submitter = relationship(User, primaryjoin=submitter_id == User.user_id)
    group_id = Column(Integer,
            ForeignKey('tg_group.group_id', name='job_group_id_fk'))
    group = relationship(Group, back_populates='jobs')
    whiteboard = Column(Unicode(2000))
    extra_xml = Column(UnicodeText, nullable=True)
    retention_tag_id = Column(Integer, ForeignKey('retention_tag.id'),
            nullable=False)
    retention_tag = relationship('RetentionTag', back_populates='jobs')
    product_id = Column(Integer, ForeignKey('product.id'), nullable=True)
    product = relationship('Product', back_populates='jobs')
    result = Column(TaskResult.db_type(), nullable=False,
            default=TaskResult.new, index=True)
    status = Column(TaskStatus.db_type(), nullable=False,
            default=TaskStatus.new, index=True)
    deleted = Column(DateTime, default=None, index=True)
    to_delete = Column(DateTime, default=None, index=True)
    # Total tasks
    ttasks = Column(Integer, default=0)
    # Total tasks completed with no result
    ntasks = Column(Integer, default=0)
    # Total Passing tasks
    ptasks = Column(Integer, default=0)
    # Total Warning tasks
    wtasks = Column(Integer, default=0)
    # Total Failing tasks
    ftasks = Column(Integer, default=0)
    # Total Panic tasks
    ktasks = Column(Integer, default=0)
    recipesets = relationship('RecipeSet', back_populates='job')
    _job_ccs = relationship('JobCc', back_populates='job',
            cascade='all, delete-orphan')

    activity = relationship(JobActivity, back_populates='object',
                cascade='all, delete-orphan',
                order_by=[JobActivity.__table__.c.id.desc()])
    activity_type = JobActivity

    def __init__(self, ttasks=0, owner=None, whiteboard=None,
            retention_tag=None, product=None, group=None, submitter=None):
        super(Job, self).__init__()
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

    def __json__(self):
        data = {
            'id': self.id,
            't_id': self.t_id,
            'submitter': self.submitter,
            'owner': self.owner,
            'group': self.group,
            'status': self.status,
            'is_finished': self.is_finished(),
            'result': self.result,
            'whiteboard': self.whiteboard,
            'cc': [cc.email_address for cc in self._job_ccs],
            'submitted_time': self.recipesets[0].queue_time,
            'retention_tag': self.retention_tag.tag,
            'product': self.product.name if self.product else None,
            'ntasks': self.ntasks,
            'ptasks': self.ptasks,
            'wtasks': self.wtasks,
            'ftasks': self.ftasks,
            'ktasks': self.ktasks,
            'ttasks': self.ttasks,
            'recipesets': self.recipesets,
        }
        if identity.current.user:
            u = identity.current.user
            data['can_change_retention_tag'] = self.can_change_retention_tag(u)
            if data['can_change_retention_tag']:
                data['possible_retention_tags'] = RetentionTag.query.all()
            data['can_change_product'] = self.can_change_product(u)
            if data['can_change_product']:
                data['possible_products'] = Product.query.all()
            data['can_cancel'] = self.can_cancel(u)
            data['can_delete'] = self.can_delete(u)
            data['can_edit'] = self.can_edit(u)
        else:
            data['can_change_retention_tag'] = False
            data['can_change_product'] = False
            data['can_cancel'] = False
            data['can_delete'] = False
            data['can_edit'] = False
        return data

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
        queri = select([RecipeSet.id], from_obj=Job.__table__.join(RecipeSet.__table__), whereclause=Job.id.in_(jobs),distinct=True)
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
        queri = select([RecipeSet.id], from_obj=Job.__table__.join(RecipeSet.__table__), whereclause=Job.id.in_(job_ids),distinct=True)
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
        query = query.join(cls.recipesets, RecipeSet.recipes)\
            .filter(func.coalesce(Recipe.finish_time, RecipeSet.queue_time) < datetime.utcnow() - delta)\
            .filter(cls.status.in_([status for status in TaskStatus if status.finished]))
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
    def provision_system_job(cls, distro_trees, pick='auto', **kw):
        """ Create a new reserve job, if system_id is defined schedule it too """
        job = Job(ttasks=0, owner=identity.current.user, retention_tag=RetentionTag.get_default())
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard')
        if job.owner.rootpw_expired:
            raise BX(_(u"Your root password has expired, please change or clear it in order to submit jobs."))

        for distro_tree in distro_trees:
            recipeSet = RecipeSet(ttasks=2)
            recipe = MachineRecipe(ttasks=2)
            # Inlcude the XML definition so that cloning this job will act as expected.
            recipe.distro_requires = etree.tostring(distro_tree.to_xml())
            recipe.distro_tree = distro_tree
            # Don't report panic's for reserve workflow.
            recipe.panic = 'ignore'
            if pick == 'fqdn':
                system = kw.get('system')
                # Some extra sanity checks, to help out the user
                if system.status == SystemStatus.removed:
                    raise BX(_(u'%s is removed' % system))
                if not system.can_reserve(job.owner):
                    raise BX(_(u'You do not have access to reserve %s' % system))
                if not system.in_lab_with_distro_tree(distro_tree):
                    raise BX(_(u'%s is not available on %s'
                            % (distro_tree, system.lab_controller)))
                if not system.compatible_with_distro_tree(distro_tree):
                    raise BX(_(u'%s does not support %s' % (system, distro_tree)))
                # Inlcude the XML definition so that cloning this job will act as expected.
                recipe.host_requires = u'<hostRequires force="%s" />' % system.fqdn
                recipe.systems.append(system)
            elif pick == 'lab':
                lab_controller = kw.get('lab')
                if not distro_tree.url_in_lab(lab_controller):
                    raise BX(_(u'%s is not available on %s'
                            % (distro_tree, lab_controller)))
                if not MachineRecipe.hypothetical_candidate_systems(job.owner,
                        distro_tree=distro_tree,
                        lab_controller=lab_controller).count():
                    raise BX(_(u'No available systems compatible with %s on %s'
                            % (distro_tree, lab_controller)))
                recipe.host_requires = (u'<hostRequires>'
                        u'<labcontroller op="=" value="%s" />'
                        u'<system_type op="=" value="Machine" />'
                        u'</hostRequires>'
                        % lab_controller.fqdn)
                recipeSet.lab_controller = lab_controller
            else:
                if not MachineRecipe.hypothetical_candidate_systems(job.owner,
                        distro_tree=distro_tree).count():
                    raise BX(_(u'No available systems compatible with %s'
                               % distro_tree))
                pass # leave hostrequires completely unset
            if kw.get('ks_meta'):
                recipe.ks_meta = kw.get('ks_meta')
            if kw.get('koptions'):
                recipe.kernel_options = kw.get('koptions')
            if kw.get('koptions_post'):
                recipe.kernel_options_post = kw.get('koptions_post')
            # Eventually we will want the option to add more tasks.
            # Add Install task
            recipe.tasks.append(RecipeTask.from_task(
                    Task.by_name(u'/distribution/install')))
            # Add Reserve task
            reserveTask = RecipeTask.from_task(
                    Task.by_name(u'/distribution/reservesys'))
            if kw.get('reservetime'):
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
    def inventory_system_job(cls, distro_tree, dryrun=False, **kw):
        """ Create a new inventory job and return the job XML.
        If this is not a dry run, then also submit the job
        """
        if not kw.get('owner'):
            owner = identity.current.user
        else:
            owner = kw.get('owner')
        job = Job(ttasks=0, owner=owner, retention_tag=RetentionTag.get_default())
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard')
        if job.owner.rootpw_expired:
            raise ValueError(u'Your root password has expired,' 
                             'please change or clear it in order to submit jobs.')
        recipeSet = RecipeSet(ttasks=2)
        recipe = MachineRecipe(ttasks=2)

        if kw.get('whiteboard'):
            recipe.whiteboard = kw.get('whiteboard')

        # Include the XML definition so that cloning this job will act as expected.
        recipe.distro_requires = etree.tostring(distro_tree.to_xml())
        recipe.distro_tree = distro_tree
        system = kw.get('system')
        # Some extra sanity checks, to help out the user
        if system.status == SystemStatus.removed:
            raise ValueError(u'%s is removed' % system)
        if not system.can_reserve(job.owner):
            raise ValueError(u'You do not have access to reserve %s' % system)
        recipe.host_requires = u'<hostRequires force="%s" />' % system.fqdn
        recipe.systems.append(system)
        # Add Install task
        install_task = RecipeTask.from_task(Task.by_name(u'/distribution/install'))
        recipe.tasks.append(install_task)
        # Add inventory task
        inventory_task = RecipeTask.from_task(Task.by_name(u'/distribution/inventory'))
        recipe.tasks.append(inventory_task)
        recipeSet.recipes.append(recipe)
        job.recipesets.append(recipeSet)
        job.ttasks += recipeSet.ttasks
        job_xml = etree.tostring(job.to_xml(clone=True))
        # We have the XML now, so if dry run, roll back
        if dryrun:
            session.rollback()
        else:
            system.hardware_scan_recipes.append(recipe)
            session.flush()
        return job_xml

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
            query = query.filter(not_(Job.is_deleted))
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
        """
        Returns an iterator of dicts describing all logs in this job.
        """
        return (log for rs in self.recipesets for log in rs.all_logs)

    @property
    def all_activity(self):
        """
        A list of all activity records from this job and its recipe sets, 
        combined in the proper order.
        """
        return sorted(
                sum((rs.activity for rs in self.recipesets), self.activity),
                key=lambda a: a.created, reverse=True)

    def clone_link(self):
        """ return link to clone this job
        """
        return url("/jobs/clone?job_id=%s" % self.id)

    def cancel_link(self):
        """ return link to cancel this job
        """
        return url("/jobs/cancel?id=%s" % self.id)

    @property
    def href(self):
        """Returns a relative URL for job's page."""
        return urllib.quote(u'/jobs/%s' % self.id)

    def is_owner(self,user):
        if self.owner == user:
            return True
        return False

    @hybrid_property
    def is_deleted(self):
        if self.deleted or self.to_delete:
            return True
        return False

    @is_deleted.expression
    def is_deleted(cls): #pylint: disable=E0213
        return or_(cls.deleted != None, cls.to_delete != None)

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

    def _create_job_elem(self, clone=False, *args, **kw):
        job = etree.Element("job")
        if not clone:
            job.set("id", "%s" % self.id)
            job.set("owner", "%s" % self.owner.email_address)
            job.set("result", "%s" % self.result)
            job.set("status", "%s" % self.status)
        if self.cc:
            notify = etree.Element('notify')
            for email_address in self.cc:
                notify.append(node('cc', email_address))
            job.append(notify)
        job.set("retention_tag", "%s" % self.retention_tag.tag)
        if self.group:
            job.set("group", "%s" % self.group.group_name)
        if self.product:
            job.set("product", "%s" % self.product.name)
        job.append(node("whiteboard", self.whiteboard or ''))
        if self.extra_xml:
            job.extend(etree.fromstring(u'<dummy>%s</dummy>' % self.extra_xml).getchildren())
        return job

    def to_xml(self, clone=False, *args, **kw):
        job = self._create_job_elem(clone)
        for rs in self.recipesets:
            job.append(rs.to_xml(clone))
        return job

    def cancel(self, msg=None):
        """
        Method to cancel all unfinished recipes in this job.
        """
        for recipe in self.all_recipes:
            recipe._abort_cancel(TaskStatus.cancelled, msg)
        self._mark_dirty()

    def abort(self, msg=None):
        """
        Method to abort all unfinished tasks in this job.
        """
        for recipeset in self.recipesets:
            for recipe in recipeset.recipes:
                recipe._abort_cancel(TaskStatus.aborted, msg)
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

    @hybrid_property
    def is_dirty(self):
        return (self.dirty_version != self.clean_version)

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ntasks = 0
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = TaskResult.min()
        min_status = TaskStatus.max()
        for recipeset in self.recipesets:
            recipeset._update_status()
            self.ntasks += recipeset.ntasks
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

    def can_edit(self, user=None):
        """Returns True iff the given user can edit the job metadata"""
        return self._can_administer(user) or self._can_administer_old(user)

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
        if not get('beaker.deprecated_job_group_permissions.on', False):
            return False
        if not user:
            return False
        return bool(set(user.groups).intersection(set(self.owner.groups)))

    cc = association_proxy('_job_ccs', 'email_address')

# for fast dirty_version != clean_version comparisons:
Index('ix_job_dirty_clean_version', Job.dirty_version, Job.clean_version)

class JobCc(DeclarativeMappedObject):

    __tablename__ = 'job_cc'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    job_id = Column(Integer, ForeignKey('job.id', ondelete='CASCADE',
            onupdate='CASCADE'), primary_key=True)
    job = relationship(Job, back_populates='_job_ccs')
    email_address = Column(Unicode(255), primary_key=True, index=True)

    def __init__(self, email_address):
        super(JobCc, self).__init__()
        self.email_address = email_address


class Product(DeclarativeMappedObject):

    __tablename__ = 'product'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(Unicode(100), unique=True, index=True, nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    jobs = relationship(Job, back_populates='product', cascade_backrefs=False)

    def __init__(self, name):
        super(Product, self).__init__()
        self.name = name

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf8')

    def __json__(self):
        return {'name': self.name}

    @classmethod
    def by_id(cls, id):
        return cls.query.filter(cls.id == id).one()

    @classmethod
    def by_name(cls, name):
        try:
            return cls.query.filter(cls.name == name).one()
        except NoResultFound:
            raise ValueError('No such product %r' % name)

class BeakerTag(DeclarativeMappedObject):

    __tablename__ = 'beaker_tag'
    __table_args__ = (
        UniqueConstraint('tag', 'type'),
        {'mysql_engine': 'InnoDB'}
    )
    id = Column(Integer, primary_key=True, nullable = False)
    tag = Column(Unicode(20), nullable=False)
    type = Column(Unicode(40), nullable=False)
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': u'tag'}

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

    __tablename__ = 'retention_tag'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('beaker_tag.id', onupdate='CASCADE',
            ondelete='CASCADE'), primary_key=True)
    is_default = Column('default_', Boolean)
    expire_in_days = Column(Integer, default=0, nullable=False)
    needs_product = Column(Boolean, nullable=False)
    __mapper_args__ = {'polymorphic_identity': u'retention_tag'}
    jobs = relationship(Job, back_populates='retention_tag', cascade_backrefs=False)

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

    def __repr__(self):
        return '%s(tag=%r, needs_product=%r, expire_in_days=%r)' % (
                self.__class__.__name__, self.tag, self.needs_product,
                self.expire_in_days)

    def __unicode__(self):
        return self.tag

    def __str__(self):
        return unicode(self).encode('utf8')

    def __json__(self):
        return {
            'tag': self.tag,
            'needs_product': self.needs_product,
        }

class Response(DeclarativeMappedObject):

    __tablename__ = 'response'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    response = Column(Unicode(50), nullable=False)

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

class RecipeSetResponse(DeclarativeMappedObject):
    """
    An acknowledgment of a RecipeSet's results. Can be used for filtering reports
    """

    __tablename__ = 'recipe_set_nacked'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    recipe_set_id = Column(Integer, ForeignKey('recipe_set.id',
            onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    recipesets = relationship('RecipeSet') #: not a list in spite of its name
    response_id = Column(Integer, ForeignKey('response.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    response = relationship(Response)
    comment = Column(Unicode(255), nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)

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

class RecipeSet(TaskBase, DeclarativeMappedObject, ActivityMixin):
    """
    A Collection of Recipes that must be executed at the same time.
    """

    __tablename__ = 'recipe_set'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('job.id'), nullable=False)
    job = relationship(Job, back_populates='recipesets')
    priority = Column(TaskPriority.db_type(), nullable=False,
            default=TaskPriority.default_priority(), index=True)
    queue_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    result = Column(TaskResult.db_type(), nullable=False,
            default=TaskResult.new, index=True)
    status = Column(TaskStatus.db_type(), nullable=False,
            default=TaskStatus.new, index=True)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id'))
    lab_controller = relationship(LabController)
    # Total tasks
    ttasks = Column(Integer, default=0)
    # Total tasks completed with no result
    ntasks = Column(Integer, default=0)
    # Total Passing tasks
    ptasks = Column(Integer, default=0)
    # Total Warning tasks
    wtasks = Column(Integer, default=0)
    # Total Failing tasks
    ftasks = Column(Integer, default=0)
    # Total Panic tasks
    ktasks = Column(Integer, default=0)
    recipes = relationship('Recipe', back_populates='recipeset')
    activity = relationship(RecipeSetActivity, back_populates='object',
            order_by=[RecipeSetActivity.created.desc(), RecipeSetActivity.id.desc()])
    nacked = relationship(RecipeSetResponse, cascade='all, delete-orphan',
            uselist=False)

    activity_type = RecipeSetActivity

    stop_types = ['abort','cancel']

    def __init__(self, ttasks=0, priority=None):
        super(RecipeSet, self).__init__()
        self.ttasks = ttasks
        self.priority = priority

    def __json__(self):
        return {
            'id': self.id,
            't_id': self.t_id,
            'status': self.status,
            'is_finished': self.is_finished(),
            'ntasks': self.ntasks,
            'ptasks': self.ptasks,
            'wtasks': self.wtasks,
            'ftasks': self.ftasks,
            'ktasks': self.ktasks,
            'ttasks': self.ttasks,
            'priority': self.priority,
            'machine_recipes': list(self.machine_recipes),
        }

    def get_log_dirs(self):
        logs = []
        for recipe in self.recipes:
            r_logs = recipe.get_log_dirs()
            if r_logs:
                logs.extend(r_logs)
        return logs

    @property
    def all_logs(self):
        """
        Returns an iterator of dicts describing all logs in this recipeset.
        """
        return (log for recipe in self.recipes for log in recipe.all_logs)

    def set_response(self, response):
        old_response = None
        if self.nacked is None:
            self.nacked = RecipeSetResponse(type=response)
        else:
            old_response = self.nacked.response
            self.nacked.response = Response.by_response(response)
        self.record_activity(user=identity.current.user, service=u'XMLRPC',
                             field=u'Ack/Nak', action='Changed',
                             old=old_response, new=self.nacked.response)

    def is_owner(self, user):
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

    def can_change_priority(self, user):
        """
        Is the given user permitted to change the priority of this recipe 
        set?
        See also #allowed_priorities
        """
        return self.job.can_change_priority(user)

    def build_ancestors(self, *args, **kw):
        """
        return a tuple of strings containing the Recipes RS and J
        """
        return (self.job.t_id,)

    def owner(self):
        return self.job.owner
    owner = property(owner)

    def to_xml(self, clone=False, from_job=True, *args, **kw):
        recipeSet = etree.Element("recipeSet")
        recipeSet.set('priority', unicode(self.priority))
        return_node = recipeSet

        if not clone:
            response = self.get_response()
            if response:
                recipeSet.set('response','%s' % str(response))

        if not clone:
            recipeSet.set("id", "%s" % self.id)

        for r in self.machine_recipes:
            recipeSet.append(r.to_xml(clone, from_recipeset=True))
        if not from_job:
            job = self.job._create_job_elem(clone)
            job.append(recipeSet)
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
        Method to cancel all unfinished recipes in this recipe set.
        """
        for recipe in self.recipes:
            recipe._abort_cancel(TaskStatus.cancelled, msg)
        self.job._mark_dirty()

    def abort(self, msg=None):
        """
        Method to abort all unfinished recipes in this recipe set.
        """
        for recipe in self.recipes:
            recipe._abort_cancel(TaskStatus.aborted, msg)
        self.job._mark_dirty()

    @property
    def is_dirty(self):
        return self.job.is_dirty

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ntasks = 0
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = TaskResult.min()
        min_status = TaskStatus.max()
        for recipe in self.recipes:
            recipe._update_status()
            self.ntasks += recipe.ntasks
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
        query = select([Recipe.id,
                        func.count(System.id).label('count')],
                        from_obj=[Recipe.__table__,
                                  system_recipe_map,
                                  System.__table__,
                                  RecipeSet.__table__,
                                  LabController.__table__],
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


class RecipeReservationRequest(DeclarativeMappedObject):
    """
    Contains a recipe's reservation request if any
    """
    __tablename__ = 'recipe_reservation'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    duration = Column(Integer, default=86400, nullable=False)

    def __init__(self, duration=86400):
        self.duration = duration

    def __json__(self):
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'duration': self.duration,
        }


class Recipe(TaskBase, DeclarativeMappedObject, ActivityMixin):
    """
    Contains requires for host selection and distro selection.
    Also contains what tasks will be executed.
    """

    __tablename__ = 'recipe'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_set_id = Column(Integer, ForeignKey('recipe_set.id'), nullable=False)
    recipeset = relationship(RecipeSet, back_populates='recipes')
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id'))
    distro_tree = relationship(DistroTree, back_populates='recipes')
    rendered_kickstart_id = Column(Integer, ForeignKey('rendered_kickstart.id',
            name='recipe_rendered_kickstart_id_fk', ondelete='SET NULL'))
    rendered_kickstart = relationship('RenderedKickstart')
    result = Column(TaskResult.db_type(), nullable=False,
            default=TaskResult.new, index=True)
    status = Column(TaskStatus.db_type(), nullable=False,
            default=TaskStatus.new, index=True)
    reservation_request = relationship(RecipeReservationRequest, uselist=False)
    start_time = Column(DateTime, index=True)
    finish_time = Column(DateTime)
    _host_requires = Column(UnicodeText())
    _distro_requires = Column(UnicodeText())
    # This column is actually a custom user-supplied kickstart *template*
    # (if not NULL), the generated kickstart for the recipe is defined above
    kickstart = Column(UnicodeText())
    # type = recipe, machine_recipe or guest_recipe
    type = Column(String(30), nullable=False)
    # Total tasks
    ttasks = Column(Integer, default=0)
    # Total tasks completed with no result
    ntasks = Column(Integer, default=0)
    # Total Passing tasks
    ptasks = Column(Integer, default=0)
    # Total Warning tasks
    wtasks = Column(Integer, default=0)
    # Total Failing tasks
    ftasks = Column(Integer, default=0)
    # Total Panic tasks
    ktasks = Column(Integer, default=0)
    whiteboard = Column(Unicode(2000))
    ks_meta = Column(String(1024))
    kernel_options = Column(String(1024))
    kernel_options_post = Column(String(1024))
    role = Column(Unicode(255))
    panic = Column(Unicode(20))
    _partitions = Column(UnicodeText())
    autopick_random = Column(Boolean, nullable=False, default=False)
    log_server = Column(Unicode(255), index=True)
    virt_status = Column(RecipeVirtStatus.db_type(), index=True,
            nullable=False, default=RecipeVirtStatus.possible)
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': u'recipe'}
    resource = relationship('RecipeResource', uselist=False, back_populates='recipe')
    watchdog = relationship(Watchdog, uselist=False,
            cascade='all, delete, delete-orphan')
    systems = relationship(System, secondary=system_recipe_map,
            back_populates='queued_recipes')
    dyn_systems = dynamic_loader(System, secondary=system_recipe_map)
    tasks = relationship('RecipeTask', back_populates='recipe')
    dyn_tasks = relationship('RecipeTask', lazy='dynamic')
    tags = relationship('RecipeTag', secondary=recipe_tag_map,
            back_populates='recipes')
    repos = relationship('RecipeRepo')
    rpms = relationship('RecipeRpm', back_populates='recipe')
    logs = relationship(LogRecipe, back_populates='parent', cascade='all, delete-orphan')
    custom_packages = relationship(TaskPackage,
            secondary=task_packages_custom_map)
    ks_appends = relationship('RecipeKSAppend')

    stop_types = ['abort','cancel']
    activity = relationship(RecipeActivity, back_populates='object',
            cascade='all, delete-orphan',
            order_by=[RecipeActivity.created.desc(), RecipeActivity.id.desc()])
    activity_type = RecipeActivity

    def __init__(self, ttasks=0):
        super(Recipe, self).__init__()
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
        return get('basepath.harness')

    @property
    def repopath(self):
        return get('basepath.repos')

    def is_owner(self,user):
        return self.recipeset.job.owner == user

    def is_deleted(self):
        if self.recipeset.job.is_deleted:
            return True
        return False

    @property
    def install_started(self):
        return getattr(self.resource, 'install_started', None)

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
            'customrepos': [dict(repo_id=r.name, path=r.url) for r in self.repos],
            'taskrepo': '%s,%s' % self.task_repo(),
            'partitions': self.partitionsKSMeta,
        }

        harness_repo = self.harness_repo()
        if harness_repo:
            ks_meta['harnessrepo'] = '%s,%s' % harness_repo

        return InstallOptions(ks_meta, {}, {})

    def to_xml(self, recipe, clone=False, from_recipeset=False, from_machine=False):
        if not clone:
            recipe.set("id", "%s" % self.id)
            recipe.set("job_id", "%s" % self.recipeset.job_id)
            recipe.set("recipe_set_id", "%s" % self.recipe_set_id)
        autopick = etree.Element("autopick")
        autopick.set("random", "%s" % unicode(self.autopick_random).lower())
        recipe.append(autopick)
        recipe.set("whiteboard", "%s" % self.whiteboard and self.whiteboard or '')
        recipe.set("role", "%s" % self.role and self.role or 'RECIPE_MEMBERS')
        if self.kickstart:
            kickstart = etree.Element("kickstart")
            kickstart.text = etree.CDATA('%s' % self.kickstart)
            recipe.append(kickstart)
        if self.rendered_kickstart and not clone:
            recipe.set('kickstart_url', self.rendered_kickstart.link)
        recipe.set("ks_meta", "%s" % self.ks_meta and self.ks_meta or '')
        recipe.set("kernel_options", "%s" % self.kernel_options and self.kernel_options or '')
        recipe.set("kernel_options_post", "%s" % self.kernel_options_post and self.kernel_options_post or '')
        if self.duration and not clone:
            recipe.set("duration", "%s" % self.duration)
        if self.result and not clone:
            recipe.set("result", "%s" % self.result)
        if self.status and not clone:
            recipe.set("status", "%s" % self.status)
        if self.distro_tree and not clone:
            recipe.set("distro", "%s" % self.distro_tree.distro.name)
            recipe.set("arch", "%s" % self.distro_tree.arch)
            recipe.set("family", "%s" % self.distro_tree.distro.osversion.osmajor)
            recipe.set("variant", "%s" % self.distro_tree.variant)
        watchdog = etree.Element("watchdog")
        if self.panic:
            watchdog.set("panic", "%s" % self.panic)
        recipe.append(watchdog)
        if self.resource and self.resource.fqdn and not clone:
            recipe.set("system", "%s" % self.resource.fqdn)
        if not clone:
            installation = etree.Element('installation')
            if self.resource:
                if self.resource.install_started:
                    installation.set('install_started',
                            self.resource.install_started.strftime('%Y-%m-%d %H:%M:%S'))
                if self.resource.install_finished:
                    installation.set('install_finished',
                            self.resource.install_finished.strftime('%Y-%m-%d %H:%M:%S'))
                if self.resource.postinstall_finished:
                    installation.set('postinstall_finished',
                            self.resource.postinstall_finished.strftime('%Y-%m-%d %H:%M:%S'))
            recipe.append(installation)
        packages = etree.Element("packages")
        if self.custom_packages:
            for package in self.custom_packages:
                packages.append(package.to_xml())
        recipe.append(packages)

        ks_appends = etree.Element("ks_appends")
        if self.ks_appends:
            for ks_append in self.ks_appends:
                ks_appends.append(ks_append.to_xml())
        recipe.append(ks_appends)

        if not clone and not self.is_queued():
            roles = etree.Element("roles")
            for role in self.roles_to_xml():
                roles.append(role)
            recipe.append(roles)
        repos = etree.Element("repos")
        for repo in self.repos:
            repos.append(repo.to_xml())
        recipe.append(repos)
        drs = etree.XML(self.distro_requires)
        hrs = etree.XML(self.host_requires)
        prs = etree.XML(self.partitions)
        recipe.append(drs)
        recipe.append(hrs)
        recipe.append(prs)
        for t in self.tasks:
            recipe.append(t.to_xml(clone))
        if self.reservation_request:
            reservesys = etree.Element("reservesys")
            reservesys.set('duration', unicode(self.reservation_request.duration))
            recipe.append(reservesys)
        if not from_recipeset and not from_machine:
            recipe = self._add_to_job_element(recipe, clone)
        return recipe

    def _add_to_job_element(self, recipe, clone):
        recipeSet = etree.Element("recipeSet")
        recipeSet.append(recipe)
        job = etree.Element("job")
        if not clone:
            job.set("owner", "%s" % self.recipeset.job.owner.email_address)
        job.append(node("whiteboard", self.recipeset.job.whiteboard or ''))
        job.append(recipeSet)
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

    @property
    def host_requires(self):
        try:
            hrs = etree.fromstring(self._host_requires)
        except ValueError:
            hrs = etree.Element('hostRequires')

        # If no system_type is specified then add defaults
        if not hrs.findall('system_type') and not hrs.get('force'):
            system_type = etree.Element('system_type')
            system_type.set('value', unicode(self.systemtype))
            hrs.append(system_type)

        return etree.tostring(hrs)

    @host_requires.setter
    def host_requires(self, value):
        self._host_requires = value

    @property
    def partitions(self):
        """ get _partitions """
        try:
            prs = etree.fromstring(self._partitions)
        except ValueError:
            prs = etree.Element("partitions")
        return etree.tostring(prs)

    @partitions.setter
    def partitions(self, value):
        """ set _partitions """
        self._partitions = value

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
        # Record task versions as they existed at this point in time, since we 
        # just created the task library snapshot for this recipe.
        for recipetask in self.tasks:
            if recipetask.task:
                recipetask.version = recipetask.task.version
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

    def _time_remaining(self):
        duration = None
        if self.watchdog and self.watchdog.kill_time:
            delta = self.watchdog.kill_time - datetime.utcnow().replace(microsecond=0)
            duration = delta
        return duration
    time_remaining = property(_time_remaining)

    def return_reservation_link(self):
        """ return link to return the reservation for this recipe
        """
        return url("/recipes/return_reservation?recipe_id=%s" % self.id)

    def return_reservation(self):
        self.extend(0)
        self.recipeset.job._mark_dirty()

    def _abort_cancel(self, status, msg=None):
        """
        Method to abort/cancel all unfinished tasks in this recipe.
        """
        # This ensures that the recipe does not stay Reserved when it is already
        # Reserved and the watchdog expires (for abort) or, is cancelled 
        # (user initiated)
        if self.watchdog:
            self.extend(0)
        for task in self.tasks:
            if not task.is_finished():
                task._abort_cancel(status, msg)
        # clear rows in system_recipe_map
        self.systems = []

    def abort(self, msg=None):
        """
        Method to abort all unfinished tasks in this recipe.
        """
        self._abort_cancel(TaskStatus.aborted, msg)
        self.recipeset.job._mark_dirty()

    @property
    def is_dirty(self):
        return self.recipeset.job.is_dirty

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ntasks = 0
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
                elif task.result == TaskResult.warn:
                    self.wtasks += 1
                elif task.result == TaskResult.fail:
                    self.ftasks += 1
                elif task.result == TaskResult.panic:
                    self.ktasks += 1
                else:
                    self.ntasks += 1
            if task.status.severity < min_status.severity:
                min_status = task.status
            if task.result.severity > max_result.severity:
                max_result = task.result
        if self.status.finished and not min_status.finished:
            min_status = self._fix_zombie_tasks()

        if min_status.finished and min_status != TaskStatus.cancelled:
            if self.status == TaskStatus.running and self.reservation_request:
                min_status = TaskStatus.reserved
                self.extend(self.reservation_request.duration)
                mail.reservesys_notify(self)
                log.debug('%s moved to Reserved', self.t_id)
            elif self.status == TaskStatus.reserved and self.status_watchdog() > 0:
                min_status = TaskStatus.reserved

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
            if self.is_suspiciously_aborted and \
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

        from bkr.server.kickstart import generate_kickstart
        install_options = InstallOptions.reduce(chain(
                [global_install_options()],
                self.distro_tree.install_options(),
                self.resource.install_options(self.distro_tree),
                [self.generated_install_options(),
                 InstallOptions.from_strings(self.ks_meta,
                    self.kernel_options, self.kernel_options_post)]))

        if 'contained_harness' not in install_options.ks_meta \
           and 'ostree_repo_url' not in install_options.ks_meta:
            if 'harness' not in install_options.ks_meta and not self.harness_repo():
                raise ValueError('Failed to find repo for harness')
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
{%% snippet 'postinstall_done' %%}
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
{%% snippet 'postinstall_done' %%}
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
            self.resource.system.record_activity(user=self.recipeset.job.owner,
                    service=u'Scheduler', action=u'Provision',
                    field=u'Distro Tree', old=u'',
                    new=unicode(self.distro_tree))
        elif isinstance(self.resource, VirtResource):
            self.resource.kernel_options = install_options.kernel_options_str
            manager = dynamic_virt.VirtManager(self.recipeset.job.owner)
            manager.start_vm(self.resource.instance_id)
            self.resource.rebooted = datetime.utcnow()
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
        if self.resource:
            worker = {'name': self.resource.fqdn}
        else:
            worker = None
        return dict(
                    id              = "R:%s" % self.id,
                    worker          = worker,
                    state_label     = "%s" % self.status,
                    state           = self.status.value,
                    method          = "%s" % self.whiteboard,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
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
        if self.watchdog and self.watchdog.kill_time:
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
        Returns an iterator of dicts describing all logs in this recipe.
        """
        # Get all the logs from log_* tables directly to avoid doing N database
        # queries for N results on large recipes.
        recipe_logs = LogRecipe.query\
                .filter(LogRecipe.recipe_id == self.id).all()
        recipe_task_logs = LogRecipeTask.query\
                .join(LogRecipeTask.parent)\
                .join(RecipeTask.recipe)\
                .options(contains_eager(LogRecipeTask.parent))\
                .filter(Recipe.id == self.id).all()
        recipe_task_result_logs =  LogRecipeTaskResult.query\
                .join(LogRecipeTaskResult.parent)\
                .join(RecipeTaskResult.recipetask)\
                .join(RecipeTask.recipe)\
                .options(contains_eager(LogRecipeTaskResult.parent))\
                .filter(Recipe.id == self.id).all()
        return chain((log.dict for log in recipe_logs),
               (log.dict for log in recipe_task_logs),
               (log.dict for log in recipe_task_result_logs))

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
        return _roles_to_xml(self)

    @property
    def first_task(self):
        return self.dyn_tasks.order_by(RecipeTask.id).first()

    def can_edit(self, user=None):
        """Returns True iff the given user can edit this recipe"""
        return self.recipeset.job.can_edit(user)

    def can_update_reservation_request(self, user=None):
        """Returns True iff the given user can update the reservation request"""
        return self.can_edit(user) and self.status not in (TaskStatus.completed,
                TaskStatus.cancelled, TaskStatus.aborted, TaskStatus.reserved)

    def __json__(self):
        data = {
            'id': self.id,
            't_id': self.t_id,
            'status': self.status,
            'is_finished': self.is_finished(),
            'result': self.result,
            'whiteboard': self.whiteboard,
            'distro_tree': self.distro_tree,
            'resource': self.resource,
            'role': self.role,
            'ntasks': self.ntasks,
            'ptasks': self.ptasks,
            'wtasks': self.wtasks,
            'ftasks': self.ftasks,
            'ktasks': self.ktasks,
            'ttasks': self.ttasks,
            # for backwards compatibility only:
            'recipe_id': self.id,
            'job_id': self.recipeset.job.t_id,
        }
        if identity.current.user:
            u = identity.current.user
            data['can_edit'] = self.can_edit(u)
            data['can_update_reservation_request'] = self.can_update_reservation_request(u)
        else:
            data['can_edit'] = False
            data['can_update_reservation_request'] = False
        return data


def _roles_to_xml(recipe):
    for key, recipes in sorted(recipe.peer_roles().iteritems()):
        role = etree.Element("role")
        role.set("value", "%s" % key)
        for r in recipes:
            if r.resource:
                system = etree.Element("system")
                system.set("value", "%s" % r.resource.fqdn)
                role.append(system)
        yield(role)


class GuestRecipe(Recipe):

    __tablename__ = 'guest_recipe'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('recipe.id'), primary_key=True)
    guestname = Column(UnicodeText)
    guestargs = Column(UnicodeText)
    __mapper_args__ = {'polymorphic_identity': u'guest_recipe'}
    hostrecipe = relationship('MachineRecipe', secondary=machine_guest_map,
            uselist=False, back_populates='guests')

    systemtype = 'Virtual'

    def to_xml(self, clone=False, from_recipeset=False, from_machine=False):
        recipe = etree.Element("guestrecipe")
        recipe.set("guestname", "%s" % (self.guestname or ""))
        recipe.set("guestargs", "%s" % self.guestargs)
        if self.resource and self.resource.mac_address and not clone:
            recipe.set("mac_address", "%s" % self.resource.mac_address)
        if self.distro_tree and self.recipeset.lab_controller and not clone:
            location = self.distro_tree.url_in_lab(self.recipeset.lab_controller)
            if location:
                recipe.set("location", location)
            for lca in self.distro_tree.lab_controller_assocs:
                if lca.lab_controller == self.recipeset.lab_controller:
                    scheme = urlparse.urlparse(lca.url).scheme
                    attr = '%s_location' % re.sub(r'[^a-z0-9]+', '_', scheme.lower())
                    recipe.set(attr, lca.url)

        return Recipe.to_xml(self, recipe, clone, from_recipeset, from_machine)

    def _add_to_job_element(self, guestrecipe, clone):
        recipe = etree.Element('recipe')
        if self.resource and not clone:
            recipe.set('system', '%s' % self.hostrecipe.resource.fqdn)
        recipe.append(guestrecipe)
        job = super(GuestRecipe, self)._add_to_job_element(recipe, clone)
        return job

    def _get_distro_requires(self):
        try:
            drs = etree.fromstring(self._distro_requires)
        except TypeError:
            drs = etree.Element("distroRequires")
        return etree.tostring(drs)

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

    __tablename__ = 'machine_recipe'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('recipe.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': u'machine_recipe'}
    guests = relationship(GuestRecipe, secondary=machine_guest_map,
            back_populates='hostrecipe')

    systemtype = 'Machine'

    def __json__(self):
        data = super(MachineRecipe, self).__json__()
        data.update({'guest_recipes': self.guests})
        return data

    def to_xml(self, clone=False, from_recipeset=False):
        recipe = etree.Element("recipe")
        for guest in self.guests:
            recipe.append(guest.to_xml(clone, from_machine=True))
        return Recipe.to_xml(self, recipe, clone, from_recipeset)

    def check_virtualisability(self):
        """
        Decide whether this recipe can be run as a virt guest
        """
        # The job owner needs to have supplied their OpenStack credentials
        if (not self.recipeset.job.owner.openstack_username
                or not self.recipeset.job.owner.openstack_password
                or not self.recipeset.job.owner.openstack_tenant_name):
            return RecipeVirtStatus.skipped
        # OpenStack is i386/x86_64 only
        if self.distro_tree.arch.arch not in [u'i386', u'x86_64']:
            return RecipeVirtStatus.precluded
        # Can't run VMs in a VM
        if self.guests:
            return RecipeVirtStatus.precluded
        # Multihost testing won't work (for now!)
        if len(self.recipeset.recipes) > 1:
            return RecipeVirtStatus.precluded
        # Check for any host requirements which cannot be virtualised
        # Delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import XmlHost
        host_filter = XmlHost.from_string(self.host_requires)
        if not host_filter.virtualisable():
            return RecipeVirtStatus.precluded
        # Checks all passed, so dynamic virt should be attempted
        return RecipeVirtStatus.possible

    @classmethod
    def get_queue_stats(cls, recipes=None):
        """Returns a dictionary of status:count pairs for active recipes"""
        if recipes is None:
            recipes = cls.query
        active_statuses = [s for s in TaskStatus if not s.finished]
        query = (recipes.filter(cls.status.in_(active_statuses))
                  .group_by(cls.status)
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
                 .filter(cls.status.in_(active_statuses))
                 .group_by(grouping, cls.status))
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

    def candidate_systems(self, only_in_lab=True):
        """
        Returns a query of systems which are candidates to run this recipe.
        """
        systems = System.all(self.recipeset.job.owner)
        # delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import XmlHost
        host_filter = XmlHost.from_string(self.host_requires)
        if not host_filter.force:
            systems = host_filter.apply_filter(systems). \
                      filter(System.status == SystemStatus.automated)
        else:
            systems = systems.filter(System.fqdn == host_filter.force). \
                      filter(System.status != SystemStatus.removed)

        systems = systems.filter(System.can_reserve(self.recipeset.job.owner))
        systems = systems.filter(System.compatible_with_distro_tree(self.distro_tree))
        if only_in_lab:
            systems = systems.filter(System.in_lab_with_distro_tree(self.distro_tree))
        systems = System.scheduler_ordering(self.recipeset.job.owner, query=systems)
        return systems

    @classmethod
    def hypothetical_candidate_systems(cls, user, distro_tree=None, lab_controller=None, 
                                       force=False):
        """
        If a recipe were constructed according to the given arguments, what 
        would its candidate systems be?
        """
        systems = System.all(user)
        # delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import XmlHost
        systems = XmlHost.from_string('<hostRequires><system_type value="%s"/></hostRequires>' %
                                      cls.systemtype).apply_filter(systems)
        systems = systems.filter(System.can_reserve(user))
        if not force:
            systems = systems.filter(System.status == SystemStatus.automated)
        else:
            systems = systems.filter(System.status != SystemStatus.removed)

        if distro_tree:
            systems = systems.filter(System.compatible_with_distro_tree(distro_tree))
            systems = systems.filter(System.in_lab_with_distro_tree(distro_tree))
        if lab_controller:
            systems = systems.filter(System.lab_controller == lab_controller)
        systems = System.scheduler_ordering(user, query=systems)
        return systems


class RecipeTag(DeclarativeMappedObject):
    """
    Each recipe can be tagged with information that identifies what is being
    executed.  This is helpful when generating reports.
    """

    __tablename__ = 'recipe_tag'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    tag = Column(Unicode(255))
    recipes = relationship(Recipe, secondary=recipe_tag_map, back_populates='tags')


class RecipeTask(TaskBase, DeclarativeMappedObject):
    """
    This holds the results/status of the task being executed.
    """

    __tablename__ = 'recipe_task'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    recipe = relationship(Recipe, back_populates='tasks')
    name = Column(Unicode(255), nullable=False, index=True)
    version = Column(Unicode(255), index=True)
    # each RecipeTask must have either a fetch_url or a task reference
    fetch_url = Column(Unicode(2048))
    fetch_subdir = Column(Unicode(2048), nullable=False, default=u'')
    task_id = Column(Integer, ForeignKey('task.id'))
    task = relationship(Task)
    start_time = Column(DateTime)
    finish_time = Column(DateTime)
    result = Column(TaskResult.db_type(), nullable=False, default=TaskResult.new)
    status = Column(TaskStatus.db_type(), nullable=False, default=TaskStatus.new)
    role = Column(Unicode(255))
    results = relationship('RecipeTaskResult', back_populates='recipetask')
    rpms = relationship('RecipeTaskRpm')
    comments = relationship('RecipeTaskComment', back_populates='recipetask')
    params = relationship('RecipeTaskParam')
    bugzillas = relationship('RecipeTaskBugzilla', back_populates='recipetask')
    logs = relationship(LogRecipeTask, back_populates='parent',
            cascade='all, delete-orphan')
    watchdog = relationship(Watchdog, uselist=False)

    result_types = ['pass_','warn','fail','panic', 'result_none']
    stop_types = ['stop','abort','cancel']

    def record_activity(self, **kwds):
        """
        Will implement it in the future.
        """
        pass

    @classmethod
    def from_task(cls, task):
        """
        Constructs a RecipeTask for the given Task from the task library.
        """
        return cls(name=task.name, task=task)

    @classmethod
    def from_fetch_url(cls, url, subdir=None, name=None):
        """
        Constructs an external RecipeTask for the given fetch URL. If name is 
        not given it defaults to the fetch URL combined with the subdir (if any).
        """
        if name is None:
            if subdir:
                name = u'%s %s' % (url, subdir)
            else:
                name = url
        return cls(name=name, fetch_url=url, fetch_subdir=subdir)

    @validates('task')
    def validate_task(self, key, value):
        if value is not None and self.fetch_url is not None:
            raise ValueError('RecipeTask cannot have both task and fetch_url')
        return value

    @validates('fetch_url')
    def validate_fetch_url(self, key, value):
        if value is not None and self.task is not None:
            raise ValueError('RecipeTask cannot have both fetch_url and task')
        return value

    def __json__(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'status': unicode(self.status),
            'recipe_id': self.recipe_id,
            't_id': self.t_id,
            'task': self.task,
            'distro_tree': self.recipe.distro_tree,
            'start_time': self.start_time,
            'finish_time': self.finish_time,
            'result': self.result,
        }

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
        task = etree.Element("task")
        task.set("name", "%s" % self.name)
        task.set("role", "%s" % self.role and self.role or 'STANDALONE')
        if not clone:
            if self.version is not None:
                task.set('version', self.version)
            task.set("id", "%s" % self.id)
            task.set("result", "%s" % self.result)
            task.set("status", "%s" % self.status)
            if self.task:
                task.set("avg_time", "%s" % self.task.avg_time)
                rpm = etree.Element("rpm")
                name = self.task.rpm[:self.task.rpm.find('-%s' % self.task.version)]
                rpm.set("name", name)
                rpm.set("path", "%s" % self.task.path)
                task.append(rpm)
            if self.duration:
                task.set("duration", "%s" % self.duration)
        if self.fetch_url:
            fetch = etree.Element('fetch')
            fetch.set('url', self.fetch_url)
            if self.fetch_subdir:
                fetch.set('subdir', self.fetch_subdir)
            task.append(fetch)
        if not clone and not self.is_queued():
            roles = etree.Element("roles")
            for role in self.roles_to_xml():
                roles.append(role)
            task.append(roles)
        if self.params:
            params = etree.Element("params")
            for p in self.params:
                params.append(p.to_xml())
            task.append(params)
        if self.results and not clone:
            results = etree.Element("results")
            for result in self.results:
                results.append(result.to_xml())
            task.append(results)
        return task

    def _get_duration(self):
        duration = None
        if self.finish_time and self.start_time:
            duration =  self.finish_time - self.start_time
        elif self.watchdog and self.watchdog.kill_time:
            delta = self.watchdog.kill_time - datetime.utcnow().replace(microsecond=0)
            duration = 'Time Remaining %s' % delta
        return duration
    duration = property(_get_duration)

    def link_id(self):
        """ Return a link to this Executed Recipe->Task
        """
        return make_link(url = '/recipes/%s#task%s' % (self.recipe.id, self.id),
                         text = 'T:%s' % self.id)

    link_id = property(link_id)

    @property
    def name_markup(self):
        """
        Returns HTML markup (in the form of a kid.Element) displaying the name. 
        The name is linked to the task library when applicable.
        """
        if self.task:
            return make_link(url = '/tasks/%s' % self.task.id,
                             text = self.name)
        else:
            span = Element('span')
            span.text = self.name
            return span

    @property
    def all_logs(self):
        """
        Returns an iterator of dicts describing all logs in this task.
        """
        recipe_task_logs = LogRecipeTask.query\
                .filter(LogRecipeTask.recipe_task_id == self.id).all()
        recipe_task_result_logs =  LogRecipeTaskResult.query\
                .join(LogRecipeTaskResult.parent)\
                .join(RecipeTaskResult.recipetask)\
                .filter(RecipeTask.id == self.id)\
                .options(contains_eager(LogRecipeTaskResult.parent))\
                .all()
        return chain([log.dict for log in recipe_task_logs],
               [log.dict for log in recipe_task_result_logs])

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
            task_time = self.task.avg_time if self.task else 0
            # add in 30 minutes at a minimum
            self.recipe.watchdog.kill_time = (datetime.utcnow() +
                    timedelta(seconds=(task_time + 1800)))
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
        self.results.append(RecipeTaskResult(
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
        # Enforce results-per-recipe limit if configured
        max_results_per_recipe = get('beaker.max_results_per_recipe', 7500)
        if max_results_per_recipe and max_results_per_recipe > 0:
            result_count = RecipeTaskResult.query.join(RecipeTaskResult.recipetask)\
                    .filter(RecipeTask.recipe_id == self.recipe_id).count()
            if result_count >= max_results_per_recipe:
                raise ValueError('Too many results in recipe %s' % self.recipe_id)
        recipeTaskResult = RecipeTaskResult(
                                   path=path,
                                   result=result,
                                   score=score,
                                   log=summary)
        self.results.append(recipeTaskResult)
        # Flush the result to the DB so we can return the id.
        session.add(recipeTaskResult)
        session.flush()
        return recipeTaskResult.id

    @property
    def resource(self):
        return self.recipe.resource

    def task_info(self):
        """
        Method for exporting Task status for TaskWatcher
        """
        if self.resource:
            worker = {'name': self.resource.fqdn}
        else:
            worker = None
        return dict(
                    id              = "T:%s" % self.id,
                    worker          = worker,
                    state_label     = "%s" % self.status,
                    state           = self.status.value,
                    method          = "%s" % self.name,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
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
            if i >= len(peer.tasks):
                # We have uneven tasks
                continue
            peertask = peer.tasks[i]
            result.setdefault(peertask.role, []).append(peertask)
        return result

    def roles_to_xml(self):
        return _roles_to_xml(self)

    def can_stop(self, user=None):
        """Returns True iff the given user can stop this recipe task"""
        return self.recipe.recipeset.job.can_stop(user)

Index('ix_recipe_task_name_version', RecipeTask.name, RecipeTask.version)


class RecipeTaskParam(DeclarativeMappedObject):
    """
    Parameters for task execution.
    """

    __tablename__ = 'recipe_task_param'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'))
    name = Column(Unicode(255))
    value = Column(UnicodeText)

    def __init__(self, name, value):
        super(RecipeTaskParam, self).__init__()
        self.name = name
        self.value = value

    def to_xml(self):
        param = etree.Element("param")
        param.set("name", "%s" % self.name)
        param.set("value", "%s" % self.value)
        return param


class RecipeRepo(DeclarativeMappedObject):
    """
    Custom repos
    """

    __tablename__ = 'recipe_repo'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    name = Column(Unicode(255))
    url = Column(Unicode(1024))

    def __init__(self, name, url):
        super(RecipeRepo, self).__init__()
        self.name = name
        self.url = url

    def to_xml(self):
        repo = etree.Element("repo")
        repo.set("name", "%s" % self.name)
        repo.set("url", "%s" % self.url)
        return repo


class RecipeKSAppend(DeclarativeMappedObject):
    """
    Kickstart appends
    """

    __tablename__ = 'recipe_ksappend'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    ks_append = Column(UnicodeText)

    def __init__(self, ks_append):
        super(RecipeKSAppend, self).__init__()
        self.ks_append = ks_append

    def to_xml(self):
        ks_append = etree.Element("ks_append")
        ks_append.text = etree.CDATA('%s' % self.ks_append)
        return ks_append

    def __repr__(self):
        return self.ks_append

class RecipeTaskComment(DeclarativeMappedObject):
    """
    User comments about the task execution.
    """

    __tablename__ = 'recipe_task_comment'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'))
    recipetask = relationship(RecipeTask, back_populates='comments')
    comment = Column(UnicodeText)
    created = Column(DateTime)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'), index=True)
    user = relationship(User)


class RecipeTaskBugzilla(DeclarativeMappedObject):
    """
    Any bugzillas filed/found due to this task execution.
    """

    __tablename__ = 'recipe_task_bugzilla'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'))
    recipetask = relationship(RecipeTask, back_populates='bugzillas')
    bugzilla_id = Column(Integer)


class RecipeRpm(DeclarativeMappedObject):
    """
    A list of rpms that were installed at the time.
    """

    __tablename__ = 'recipe_rpm'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    recipe = relationship(Recipe, back_populates='rpms')
    package = Column(Unicode(255))
    version = Column(Unicode(255))
    release = Column(Unicode(255))
    epoch = Column(Integer)
    arch = Column(Unicode(255))
    running_kernel = Column(Boolean)


class RecipeTaskRpm(DeclarativeMappedObject):
    """
    the versions of the RPMS listed in the tasks runfor list.
    """

    __tablename__ = 'recipe_task_rpm'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'),
            primary_key=True)
    package = Column(Unicode(255))
    version = Column(Unicode(255))
    release = Column(Unicode(255))
    epoch = Column(Integer)
    arch = Column(Unicode(255))
    running_kernel = Column(Boolean)


class RecipeTaskResult(TaskBase, DeclarativeMappedObject):
    """
    Each task can report multiple results
    """

    __tablename__ = 'recipe_task_result'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'))
    recipetask = relationship(RecipeTask, back_populates='results')
    path = Column(Unicode(2048))
    result = Column(TaskResult.db_type(), nullable=False, default=TaskResult.new)
    score = Column(Numeric(10))
    log = Column(UnicodeText)
    start_time = Column(DateTime, default=datetime.utcnow)
    logs = relationship(LogRecipeTaskResult, back_populates='parent',
            cascade='all, delete-orphan')

    def __init__(self, recipetask=None, path=None, result=None,
            score=None, log=None):
        super(RecipeTaskResult, self).__init__()
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
        #FIXME Append any binary logs as URI's
        return E.result(
            unicode(self.log),
            id=unicode(self.id),
            path=unicode(self.path),
            score=unicode(self.score)
        )

    @property
    def all_logs(self):
        """
        Returns an iterator of dicts describing all logs in this result.
        """
        return (mylog.dict for mylog in self.logs)

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
    def duration(self):
        """
        Task results happen at a fixed point in time so they don't really have 
        a duration. This property is really the time since the previous result, 
        or else the time since the start of the task if this is the first 
        result.
        In a sense this is the duration of the stuff that happened in order to 
        produce this result.
        """
        index = self.recipetask.results.index(self)
        if index == 0:
            return self.start_time - self.recipetask.start_time
        else:
            previous_result = self.recipetask.results[index - 1]
            return self.start_time - previous_result.start_time

    @property
    def short_path(self):
        """
        Remove the parent from the begining of the path if present
        """
        if not self.path:
            short_path = self.path
        elif self.path.rstrip('/') == self.recipetask.name:
            short_path = ''
        elif self.path.startswith(self.recipetask.name + '/'):
            short_path = self.path.replace(self.recipetask.name + '/', '', 1)
        else:
            short_path = self.path
        return short_path

    @property
    def display_label(self):
        """
        Human-friendly label for the result, when shown alongside its parent 
        task. The conventions here are basically a historical RHTSism.
        """
        if not self.path or self.path == '/':
            return self.log or './'
        return self.short_path or './'

class RecipeResource(DeclarativeMappedObject):
    """
    Base class for things on which a recipe can be run.
    """

    __tablename__ = 'recipe_resource'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipe.id',
            name='recipe_resource_recipe_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'),
            nullable=False, unique=True)
    recipe = relationship(Recipe, back_populates='resource')
    type = Column(ResourceType.db_type(), nullable=False)
    fqdn = Column(Unicode(255), default=None, index=True)
    rebooted = Column(DateTime, nullable=True, default=None)
    install_started = Column(DateTime, nullable=True, default=None)
    install_finished = Column(DateTime, nullable=True, default=None)
    postinstall_finished = Column(DateTime, nullable=True, default=None)
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': None}

    def __str__(self):
        return unicode(self).encode('utf8')

    def __unicode__(self):
        return unicode(self.fqdn)

    @staticmethod
    def _lowest_free_mac():
        base_addr = netaddr.EUI(get('beaker.base_mac_addr', '52:54:00:00:00:00'))
        session.flush()
        # This subquery gives all MAC addresses in use right now
        guest_mac_query = session.query(GuestResource.mac_address.label('mac_address'))\
                .filter(GuestResource.mac_address != None)\
                .join(RecipeResource.recipe).join(Recipe.recipeset)\
                .filter(not_(RecipeSet.status.in_([s for s in TaskStatus if s.finished])))
        # This trickery finds "gaps" of unused MAC addresses by filtering for MAC
        # addresses where address + 1 is not in use.
        # We union with base address - 1 to find any gap at the start.
        # Note that this relies on the MACAddress type being represented as
        # BIGINT in the database, which lets us do arithmetic on it.
        left_side = union(guest_mac_query,
                select([int(base_addr) - 1])).alias('left_side')
        right_side = guest_mac_query.subquery()
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

    __tablename__ = 'system_resource'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('recipe_resource.id',
            name='system_resource_id_fk'), primary_key=True)
    system_id = Column(Integer, ForeignKey('system.id',
            name='system_resource_system_id_fk'), nullable=False)
    system = relationship(System)
    reservation_id = Column(Integer, ForeignKey('reservation.id',
            name='system_resource_reservation_id_fk'))
    reservation = relationship(Reservation)
    __mapper_args__ = {'polymorphic_identity': ResourceType.system}

    def __init__(self, system):
        super(SystemResource, self).__init__()
        self.system = system
        self.fqdn = system.fqdn

    def __repr__(self):
        return '%s(fqdn=%r, system=%r, reservation=%r)' % (
                self.__class__.__name__, self.fqdn, self.system,
                self.reservation)

    def __json__(self):
        return {
            'fqdn': self.fqdn,
            'system': self.system,
        }

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
    For a MachineRecipe which is running on an OpenStack instance.
    """

    __tablename__ = 'virt_resource'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('recipe_resource.id',
            name='virt_resource_id_fk'), primary_key=True)
    # OpenStack treats these ids as opaque strings, but we rely on them being 
    # 128-bit numbers because we use the SMBIOS UUID field in our iPXE hackery. 
    # So we store it as an actual UUID, not an opaque string.
    instance_id = Column(UUID, nullable=False)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id',
            name='virt_resource_lab_controller_id_fk'))
    lab_controller = relationship(LabController)
    kernel_options = Column(Unicode(2048))
    __mapper_args__ = {'polymorphic_identity': ResourceType.virt}

    @classmethod
    def by_instance_id(cls, instance_id):
        if isinstance(instance_id, basestring):
            instance_id = uuid.UUID(instance_id)
        return cls.query.filter(cls.instance_id == instance_id).one()

    def __init__(self, instance_id, lab_controller):
        super(VirtResource, self).__init__()
        if isinstance(instance_id, basestring):
            instance_id = uuid.UUID(instance_id)
        self.instance_id = instance_id
        self.lab_controller = lab_controller

    def __json__(self):
        return {
            'fqdn': self.fqdn,
            'instance_id': self.instance_id,
        }

    @property
    def link(self):
        span = Element('span')
        span.text = u''
        if self.fqdn:
            span.text += self.fqdn + u' '
        span.text += u'(OpenStack instance '
        if not self.href:
            span.text += unicode(self.instance_id) + u')'
        else:
            a = make_link(url=self.href, text=unicode(self.instance_id))
            a.tail = u')'
            span.append(a)
        return span

    @property
    def href(self):
        """
        Returns the URL to the Horizon dashboard for this instance.
        """
        # don't hyperlink it if the instance is deleted
        if self.recipe.is_finished():
            return None
        return urlparse.urljoin(get('openstack.dashboard_url'),
                'project/instances/%s/' % self.instance_id)

    def install_options(self, distro_tree):
        yield InstallOptions.from_strings('hwclock_is_utc', u'console=tty0 console=ttyS0,115200n8', '')

    def release(self):
        try:
            log.debug('Releasing vm %s for recipe %s',
                    self.instance_id, self.recipe.id)
            manager = dynamic_virt.VirtManager(self.recipe.recipeset.job.owner)
            manager.destroy_vm(self.instance_id)
        except Exception:
            log.exception('Failed to destroy vm %s, leaked!',
                    self.instance_id)
            # suppress exception, nothing more we can do now


class GuestResource(RecipeResource):
    """
    For a GuestRecipe which is running on a guest associated with a parent 
    MachineRecipe.
    """

    __tablename__ = 'guest_resource'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('recipe_resource.id',
            name='guest_resource_id_fk'), primary_key=True)
    mac_address = Column(MACAddress(), index=True, default=None)
    __mapper_args__ = {'polymorphic_identity': ResourceType.guest}

    def __repr__(self):
        return '%s(fqdn=%r, mac_address=%r)' % (self.__class__.__name__,
                self.fqdn, self.mac_address)

    def __json__(self):
        return {'fqdn': self.fqdn}

    @property
    def link(self):
        return self.fqdn # just text, not a link

    def install_options(self, distro_tree):
        ks_meta = {
            'hwclock_is_utc': True,
        }
        yield InstallOptions(ks_meta, {}, {})

    def allocate(self):
        self.mac_address = self._lowest_free_mac()
        log.debug('Allocated MAC address %s for recipe %s', self.mac_address, self.recipe.id)

    def release(self):
        pass

class RenderedKickstart(DeclarativeMappedObject):

    # This is for storing final generated kickstarts to be provisioned,
    # not user-supplied kickstart templates or anything else like that.

    __tablename__ = 'rendered_kickstart'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    # Either kickstart or url should be populated -- if url is present,
    # it means fetch the kickstart from there instead
    kickstart = Column(UnicodeText)
    url = Column(UnicodeText)

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
