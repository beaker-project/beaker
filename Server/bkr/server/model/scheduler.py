# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import crypt
import decimal
import logging
import numbers
import os.path
import random
import re
import shutil
import string
import urllib
import urlparse
import uuid
import xml.dom.minidom
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import chain

import netaddr
from kid import Element
from lxml import etree
from lxml.builder import E
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint, Index,
                        Integer, Unicode, DateTime, Boolean, UnicodeText, String, Numeric,
                        event)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import (relationship, object_mapper,
                            dynamic_loader, validates, synonym, contains_eager, aliased)
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import select, union, and_, or_, not_, func, literal, exists, delete
from turbogears import url
from turbogears.config import get
from turbogears.database import session

from bkr.common.helpers import makedirs_ignore, total_seconds
from bkr.server import identity, metrics, mail
from bkr.server.bexceptions import BX, BeakerException, StaleTaskStatusException
from bkr.server.helpers import make_link, make_fake_link
from bkr.server.hybrid import hybrid_method, hybrid_property
from bkr.server.installopts import InstallOptions
from bkr.server.messaging import send_scheduler_update
from bkr.server.util import absolute_url
from .activity import Activity, ActivityMixin
from .base import DeclarativeMappedObject
from .distrolibrary import (OSMajor, OSVersion, Distro, DistroTree,
                            LabControllerDistroTree, install_options_for_distro, KernelType)
from .identity import User, Group
from .installation import Installation
from .inventory import System, Reservation
from .lab import LabController
from .tasklibrary import Task, TaskPackage
from .types import (UUID, MACAddress, IPAddress, TaskResult, TaskStatus, TaskPriority,
                    ResourceType, RecipeVirtStatus, mac_unix_padded_dialect, SystemStatus,
                    RecipeReservationCondition, SystemSchedulerStatus, ImageType)

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
                                           name='recipe_activity_recipe_id_fk'), nullable=False)
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
            'whiteboard': self.object.whiteboard,
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
    recipeset_id = Column(Integer, ForeignKey('recipe_set.id'), nullable=False)
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


machine_guest_map = Table('machine_guest_map', DeclarativeMappedObject.metadata,
                          Column('machine_recipe_id', Integer,
                                 ForeignKey('machine_recipe.id', onupdate='CASCADE',
                                            ondelete='CASCADE'),
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

system_hardware_scan_recipe_map = Table('system_hardware_scan_recipe_map',
                                        DeclarativeMappedObject.metadata,
                                        Column('system_id', Integer,
                                               ForeignKey('system.id', onupdate='CASCADE',
                                                          ondelete='CASCADE'),
                                               primary_key=True),
                                        Column('recipe_id', Integer,
                                               ForeignKey('recipe.id', onupdate='CASCADE',
                                                          ondelete='CASCADE'),
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
                                 Column('recipe_id', Integer,
                                        ForeignKey('recipe.id', onupdate='CASCADE',
                                                   ondelete='CASCADE'), primary_key=True),
                                 Column('package_id', Integer, ForeignKey('task_package.id',
                                                                          onupdate='CASCADE',
                                                                          ondelete='CASCADE'),
                                        primary_key=True),
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
                                                       from_obj=Recipe.__table__.join(
                                                           Watchdog.__table__)) \
                                                .where(Watchdog.kill_time > datetime.utcnow()) \
                                                .where(Recipe.recipe_set_id == RecipeSet.id) \
                                                .correlate(RecipeSet.__table__))
        watchdog_query = cls.query.join(Watchdog.recipe).join(Recipe.recipeset) \
            .filter(Watchdog.kill_time != None)
        if labcontroller is not None:
            watchdog_query = watchdog_query.filter(
                RecipeSet.lab_controller == labcontroller)
        if status == 'active':
            watchdog_query = watchdog_query.filter(any_recipe_has_active_watchdog)
        elif status == 'expired':
            watchdog_query = watchdog_query.join(RecipeSet.job) \
                .filter(not_(Job.is_dirty)) \
                .filter(not_(any_recipe_has_active_watchdog))
        else:
            return None
        return watchdog_query

    def __repr__(self):
        return '%s(id=%r, recipe_id=%r, kill_time=%r)' % (self.__class__.__name__,
                                                          self.id, self.recipe_id, self.kill_time)


class Log(DeclarativeMappedObject):
    __abstract__ = True

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
        return dict(server=self.server,
                    path=self.path,
                    filename=self.filename,
                    tid='%s:%s' % (self.type, self.id),
                    filepath=self.parent.filepath,
                    basepath=self.basepath,
                    url=absolute_url(self.href),
                    )

    def to_xml(self):
        return E.log(name=self.combined_path, href=absolute_url(self.href))

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    def __cmp__(self, other):
        """ Used to compare logs that are already stored. Log(path,filename) in Recipe.logs  == True
        """
        if hasattr(other, 'path'):
            path = other.path
        if hasattr(other, 'filename'):
            filename = other.filename
        if "%s/%s" % (self.path, self.filename) == "%s/%s" % (path, filename):
            return 0
        else:
            return 1

    def __json__(self):
        return {
            'id': self.id,
            'start_time': self.start_time,
            'path': self.combined_path,
            'href': url(self.href),
        }


class LogRecipe(Log):
    type = 'R'

    __tablename__ = 'log_recipe'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    # common column definitions are inherited from Log
    recipe_id = Column(Integer, ForeignKey('recipe.id'), nullable=False)
    parent = relationship('Recipe', back_populates='logs')

    @property
    def href(self):
        return '/recipes/%s/logs/%s' % (self.parent.id, self.combined_path)


class LogRecipeTask(Log):
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


class LogRecipeTaskResult(Log):
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


class TaskBase(DeclarativeMappedObject):
    __abstract__ = True

    t_id_types = dict(T='RecipeTask',
                      TR='RecipeTaskResult',
                      R='Recipe',
                      RS='RecipeSet',
                      J='Job')

    # Defined on subclasses
    id = 0
    result = None
    tasks = None
    ttasks = 0
    ntasks = 0
    ptasks = 0
    wtasks = 0
    ftasks = 0
    ktasks = 0

    @property
    def logspath(self):
        return get('basepath.logs')

    @classmethod
    def get_by_t_id(cls, t_id, *args, **kw):
        """
        Return an TaskBase object by it's shorthand i.e 'J:xx, RS:xx'
        """
        # Keep Client/doc/bkr.rst in sync with this
        task_type, id = t_id.split(":")
        try:
            class_str = cls.t_id_types[task_type]
        except KeyError:
            raise BeakerException(_('You have specified an invalid task type:%s' % task_type))

        class_ref = globals()[class_str]
        try:
            obj_ref = class_ref.by_id(id)
        except InvalidRequestError:
            raise BeakerException(_('%s is not a valid %s id' % (id, class_str)))

        return obj_ref

    def _change_status(self, new_status, **kw):
        """
        _change_status will update the status if needed
        Returns True when status is changed
        """
        current_status = self.status  # pylint: disable=E0203
        if current_status != new_status:
            # Sanity check to make sure the status never goes backwards.
            if (isinstance(self, (Recipe, RecipeTask))
                    and ((new_status.queued and not current_status.queued)
                         or (not new_status.finished and current_status.finished))):
                raise ValueError('Invalid state transition for %s: %s -> %s'
                                 % (self.t_id, current_status, new_status))
            # Use a conditional UPDATE to make sure we are really working from
            # the latest database state.
            # The .base_mapper bit here is so we can get from MachineRecipe to
            # Recipe, which is needed due to the limitations of .update()
            if session.query(object_mapper(self).base_mapper) \
                    .filter_by(id=self.id, status=current_status) \
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

    @hybrid_method
    def is_finished(self):
        """
        Simply state if the task is finished or not
        """
        return self.status.finished

    @is_finished.expression
    def is_finished(cls):  # pylint: disable=E0213
        return cls.status.in_([status for status in TaskStatus if status.finished])

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
    def is_failed(cls):  # pylint: disable=E0213
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
        return all([task.status == TaskStatus.aborted for task in self.tasks])

    @is_suspiciously_aborted.expression
    def is_suspiciously_aborted(cls):  # pylint: disable=E0213
        """Returns an SQL expression evaluating to TRUE if the recipe abort was
        suspicious. Note: There is no 'ALL' operator in SQL to get rid of the
        double negation."""
        return not_(cls.tasks.any(RecipeTask.status != TaskStatus.aborted))

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


class Job(TaskBase, ActivityMixin):
    """
    Container to hold like recipe sets.
    """

    __tablename__ = 'job'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    is_dirty = Column(Boolean, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey('tg_user.user_id'), index=True)
    owner = relationship(User, back_populates='jobs',
                         primaryjoin=owner_id == User.user_id)
    submitter_id = Column(Integer,
                          ForeignKey('tg_user.user_id', name='job_submitter_id_fk'))
    submitter = relationship(User, primaryjoin=submitter_id == User.user_id)
    group_id = Column(Integer,
                      ForeignKey('tg_group.group_id', name='job_group_id_fk'))
    group = relationship(Group, back_populates='jobs')
    whiteboard = Column(Unicode(4096))
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
    purged = Column(DateTime, default=None, index=True)
    deleted = Column(DateTime, default=None, index=True)
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
        self.is_dirty = False

    stop_types = ['abort', 'cancel']
    max_by_whiteboard = 20

    def __json__(self):
        return self.to_json()

    def to_json(self, include_recipesets=True):
        data = self.minimal_json_content()
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
        if include_recipesets:
            data['recipesets'] = self.recipesets
        return data

    def minimal_json_content(self):
        return {
            'id': self.id,
            't_id': self.t_id,
            'submitter': self.submitter or self.owner,  # submitter may be NULL prior to Beaker 0.14
            'owner': self.owner,
            'group': self.group,
            'status': self.status,
            'is_finished': self.is_finished(),
            'is_deleted': self.is_deleted,
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
            'recipe_count': self.recipe_count,
            'clone_href': self.clone_link(),
        }

    @classmethod
    def mine(cls, owner):
        """
        Returns a query of all jobs which are owned by the given user.
        """
        return cls.query.filter(or_(Job.owner == owner, Job.submitter == owner))

    @classmethod
    def my_groups(cls, owner):
        """
        ... as in, "my groups' jobs". Returns a query of all jobs which were
        submitted for any of the given user's groups.
        """
        if owner.groups:
            return cls.query.outerjoin(Job.group) \
                .filter(Group.group_id.in_([g.group_id for g in owner.groups]))
        else:
            return cls.query.filter(literal(False))

    @hybrid_method
    def completed_n_days_ago(self, n):
        """
        Returns True if all recipes in this job finished more than *n* days ago.
        """
        # Note that Recipe.finish_time may be null even for a finished recipe,
        # that indicates it was cancelled/aborted before it ever started. In
        # that case we look at RecipeSet.queue_time instead.
        if not self.is_finished():
            return False
        cutoff = datetime.utcnow() - timedelta(days=n)
        for rs in self.recipesets:
            for recipe in rs.recipes:
                finish_time = recipe.finish_time or rs.queue_time
                if finish_time >= cutoff:
                    return False
        return True

    @completed_n_days_ago.expression
    def completed_n_days_ago(cls, n):  # pylint: disable=E0213
        # We let cutoff be computed on the SQL side, in case n is also a SQL
        # expression and not a constant.
        cutoff = func.adddate(func.utc_timestamp(), -n)
        return and_(
            cls.is_finished(),
            not_(exists([1], from_obj=Recipe.__table__.join(RecipeSet.__table__),
                        whereclause=and_(RecipeSet.job_id == Job.id,
                                         func.coalesce(Recipe.finish_time,
                                                       RecipeSet.queue_time) >= cutoff)))
        )

    @hybrid_property
    def is_expired(self):
        """
        A job is expired if:
            * it's not already deleted; and
            * it's older than the expiry time specified by its retention tag.
        Expired jobs will be deleted by beaker-log-delete when it runs.
        """
        if self.deleted:
            return False
        expire_in_days = self.retention_tag.expire_in_days
        if expire_in_days and self.completed_n_days_ago(expire_in_days):
            return True
        return False

    @is_expired.expression
    def is_expired(cls):  # pylint: disable=E0213
        # We *could* rely on the caller to join Job.retention_tag and then use
        # RetentionTag.expire_in_days directly here, instead of a having this
        # correlated subquery. We have used that approach elsewhere in other
        # hybrids. It produces faster queries too. *BUT* if we did that here,
        # and then the caller accidentally forgot to do the join, this clause
        # would silently result in EVERY JOB being expired which would be
        # a huge disaster.
        expire_in_days_subquery = select([RetentionTag.expire_in_days]) \
            .where(RetentionTag.jobs).correlate(Job).label('expire_in_days')
        return and_(
            Job.deleted == None,
            expire_in_days_subquery > 0,
            Job.completed_n_days_ago(expire_in_days_subquery)
        )

    @classmethod
    def has_family(cls, family, query=None, **kw):
        if query is None:
            query = cls.query
        query = query.join(cls.recipesets, RecipeSet.recipes, Recipe.distro_tree, DistroTree.distro,
                           Distro.osversion, OSVersion.osmajor).filter(
            OSMajor.osmajor == family).reset_joinpoint()
        return query

    @classmethod
    def by_tag(cls, tag, query=None):
        if query is None:
            query = cls.query
        if isinstance(tag, basestring):
            tag = [tag]
        tag_query = cls.retention_tag_id.in_([RetentionTag.by_tag(unicode(t)).id for t in tag])

        return query.filter(tag_query)

    @classmethod
    def by_product(cls, product, query=None):
        if query is None:
            query = cls.query
        if isinstance(product, basestring):
            product = [product]
        product_query = cls.product_id.in_([Product.by_name(p).id for p in product])

        return query.join('product').filter(product_query)

    @classmethod
    def by_owner(cls, owner, query=None):
        if query is None:
            query = cls.query
        if isinstance(owner, basestring):
            owner = [owner]
        # by_user_name() returns None for non-existent users
        for o in owner:
            if User.by_user_name(o) is None:
                raise NoResultFound('Owner %s is invalid' % o)
        owner_query = cls.owner_id.in_([User.by_user_name(o).id for o in owner])

        return query.join('owner').filter(owner_query)

    @classmethod
    def by_groups(cls, groups, query=None):
        if query is None:
            query = cls.query
        if isinstance(groups, basestring):
            groups = [groups]
        groups_query = cls.group_id.in_([Group.by_name(g).id for g in groups])
        return query.join('group').filter(groups_query)

    @classmethod
    def by_whiteboard(cls, desc, like=False):
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
        return query

    @classmethod
    def provision_system_job(cls, distro_trees, pick='auto', **kw):
        """ Create a new reserve job, if system_id is defined schedule it too """
        job = Job(ttasks=0, owner=identity.current.user, retention_tag=RetentionTag.get_default())
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard')
        if job.owner.rootpw_expired:
            raise BX(_(
                u"Your root password has expired, please change or clear it in order to submit jobs."))

        for distro_tree in distro_trees:
            recipeSet = RecipeSet(ttasks=2)
            recipe = MachineRecipe(ttasks=2)
            # Inlcude the XML definition so that cloning this job will act as expected.
            recipe.distro_requires = etree.tostring(distro_tree.to_xml(), encoding=unicode)
            recipe.distro_tree = distro_tree
            recipe.installation = recipe.distro_tree.create_installation_from_tree()
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
                if not system.compatible_with_distro_tree(
                        arch=distro_tree.arch,
                        osmajor=distro_tree.distro.osversion.osmajor.osmajor,
                        osminor=distro_tree.distro.osversion.osminor):
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
                pass  # leave hostrequires completely unset
            if kw.get('ks_meta'):
                recipe.ks_meta = kw.get('ks_meta')
            if kw.get('koptions'):
                recipe.kernel_options = kw.get('koptions')
            if kw.get('koptions_post'):
                recipe.kernel_options_post = kw.get('koptions_post')
            # Eventually we will want the option to add more tasks.
            # Add Install task
            recipe.tasks.append(RecipeTask.from_task(
                Task.by_name(u'/distribution/check-install')))
            # Add Reserve task
            reserveTask = RecipeTask.from_task(
                Task.by_name(u'/distribution/reservesys'))
            if kw.get('reservetime'):
                reserveTask.params.append(RecipeTaskParam(name='RESERVETIME',
                                                          value=kw.get('reservetime')
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
        recipe.distro_requires = etree.tostring(distro_tree.to_xml(), encoding=unicode)
        recipe.distro_tree = distro_tree
        system = kw.get('system')
        recipe.installation = Installation(distro_tree=recipe.distro_tree, arch=distro_tree.arch,
                                           distro_name=distro_tree.distro.name,
                                           osmajor=distro_tree.distro.osversion.osmajor.osmajor,
                                           osminor=distro_tree.distro.osversion.osminor,
                                           variant=distro_tree.variant)
        # Some extra sanity checks, to help out the user
        if system.status == SystemStatus.removed:
            raise ValueError(u'%s is removed' % system)
        if not system.can_reserve(job.owner):
            raise ValueError(u'You do not have access to reserve %s' % system)
        recipe.host_requires = u'<hostRequires force="%s" />' % system.fqdn
        recipe.systems.append(system)
        # Add Install task
        install_task = RecipeTask.from_task(Task.by_name(u'/distribution/check-install'))
        recipe.tasks.append(install_task)
        # Add inventory task
        inventory_task = RecipeTask.from_task(Task.by_name(u'/distribution/inventory'))
        recipe.tasks.append(inventory_task)
        recipeSet.recipes.append(recipe)
        job.recipesets.append(recipeSet)
        job.ttasks += recipeSet.ttasks
        job_xml = etree.tostring(job.to_xml(clone=True), encoding=unicode)
        # We have the XML now, so if dry run, roll back
        if dryrun:
            session.rollback()
        else:
            system.hardware_scan_recipes.append(recipe)
            session.flush()
        return job_xml

    @classmethod
    def find_jobs(cls, query=None, tag=None, complete_days=None, family=None,
                  product=None, owner=None, **kw):
        """Return a filtered job query

        Does what it says. Also helps searching for expired jobs
        easier.
        """
        if not query:
            query = cls.query
        query = query.filter(not_(Job.is_deleted))
        if complete_days:
            query = query.filter(Job.completed_n_days_ago(int(complete_days)))
        if family:
            try:
                OSMajor.by_name(family)
            except NoResultFound:
                err_msg = _(u'Family is invalid: %s') % family
                log.exception(err_msg)
                raise BX(err_msg)

            query = cls.has_family(family, query)
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
                query = cls.by_product(product, query)
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
    def cancel_jobs_by_user(cls, user, msg=None):
        jobs = Job.query.filter(and_(Job.owner == user,
                                     Job.status.in_([s for s in TaskStatus if not s.finished])))
        for job in jobs:
            job.cancel(msg=msg)

    def purge(self):
        """
        Purges all results and logs for a deleted job.
        """
        if not self.deleted:
            raise RuntimeError('Attempted to purge %r which is not deleted' % self)
        for rs in self.recipesets:
            rs.purge()
        self.purged = datetime.utcnow()

    def set_waived(self, waived):
        for rs in self.recipesets:
            rs.set_waived(waived)

    def requires_product(self):
        return self.retention_tag.requires_product()

    def all_logs(self, load_parent=True):
        """
        Returns an iterator of all logs in this job.
        """
        return (log for rs in self.recipesets
                for log in rs.all_logs(load_parent=load_parent))

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

    def is_owner(self, user):
        if self.owner == user:
            return True
        return False

    @hybrid_property
    def is_deleted(self):
        if self.deleted:
            return True
        return False

    @is_deleted.expression
    def is_deleted(cls):  # pylint: disable=E0213
        return cls.deleted != None

    def priority_settings(self, prefix, colspan='1'):
        span = Element('span')
        title = Element('td')
        title.attrib['class'] = 'title'
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

    def retention_settings(self, prefix, colspan='1'):
        span = Element('span')
        title = Element('td')
        title.attrib['class'] = 'title'
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

    def _create_job_elem(self, clone=False):
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

    def to_xml(self, clone=False, include_enclosing_job=True, **kwargs):
        job = self._create_job_elem(clone)
        for rs in self.recipesets:
            job.append(rs.to_xml(clone=clone, include_enclosing_job=False, **kwargs))
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
            id="J:%s" % self.id,
            worker=None,
            state_label="%s" % self.status,
            state=self.status.value,
            method="%s" % self.whiteboard,
            result="%s" % self.result,
            is_finished=self.is_finished(),
            is_failed=self.is_failed(),
            owner="{}".format(self.owner),
            submitter="{}".format(self.submitter),
            group="{}".format(self.group)
        )

    def all_recipes(self):
        """
        Return all recipes
        """
        for recipeset in self.recipesets:
            for recipe in recipeset.recipes:
                yield recipe

    all_recipes = property(all_recipes)

    @property
    def recipe_count(self):
        return Recipe.query.join(Recipe.recipeset).filter(RecipeSet.job == self).count()

    def update_status(self):
        if not self.is_dirty:
            # This error should be impossible to trigger in beakerd's
            # update_dirty_jobs thread.
            # If you are seeing this in a test case, it means something
            # *before* this point has failed to mark this job as dirty even
            # though the tests were expecting it to be dirty. That's a real bug
            # which needs fixing in whatever happened before this point.
            # For example: https://bugzilla.redhat.com/show_bug.cgi?id=991245#c15
            raise RuntimeError('Invoked update_status on '
                               'job %s which was not dirty' % self.id)

        self._update_status()
        self._mark_clean()

    def _mark_dirty(self):
        self.is_dirty = True

    def _mark_clean(self):
        # NOTE: this is only race-free if the transaction issued a SELECT...FOR UPDATE
        # on this job row before doing any other work.
        self.is_dirty = False

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
        if status_changed:
            send_scheduler_update(self)
            if self.is_finished():
                # Send email notification
                mail.job_notify(self)

    # def t_id(self):
    #    return "J:%s" % self.id
    # t_id = property(t_id)

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
        return self._can_administer(user)

    def can_change_priority(self, user=None):
        """Return True iff the given user can change the priority"""
        can_change = self._can_administer(user)
        if not can_change and user:
            can_change = user.has_permission('change_prio')
        return can_change

    def can_change_whiteboard(self, user=None):
        """Returns True iff the given user can change the whiteboard"""
        return self._can_administer(user)

    def can_change_product(self, user=None):
        """Returns True iff the given user can change the product"""
        return self._can_administer(user)

    def can_change_retention_tag(self, user=None):
        """Returns True iff the given user can change the retention tag"""
        return self._can_administer(user)

    def can_delete(self, user=None):
        """Returns True iff the given user can delete the job"""
        return self._can_administer(user)

    def can_cancel(self, user=None):
        """Returns True iff the given user can cancel the job"""
        return self._can_administer(user)

    def can_comment(self, user):
        """Returns True iff the given user can comment on this job."""
        if user is None:
            return False
        return True  # anyone can comment on any job

    def can_waive(self, user=None):
        """Returns True iff the given user can waive recipe sets in this job."""
        return self._can_administer(user)

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

    cc = association_proxy('_job_ccs', 'email_address')


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

    @validates('name')
    def validate_name(self, key, value):
        if not value:
            raise ValueError('Product name must not be empty')
        return value

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
    id = Column(Integer, primary_key=True, nullable=False)
    tag = Column(Unicode(20), nullable=False)
    type = Column(Unicode(40), nullable=False)
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': u'tag'}

    def can_delete(self):
        raise NotImplementedError("Please implement 'can_delete'  on %s" % self.__class__.__name__)

    @classmethod
    def by_id(cls, id, *args, **kw):
        return cls.query.filter(cls.id == id).one()

    @classmethod
    def by_tag(cls, tag, *args, **kw):
        return cls.query.filter(cls.tag == tag).one()

    @classmethod
    def get_all(cls, *args, **kw):
        return cls.query


class RetentionTag(BeakerTag):
    __tablename__ = 'retention_tag'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('beaker_tag.id', onupdate='CASCADE',
                                    ondelete='CASCADE'), primary_key=True)
    is_default = Column('default_', Boolean(create_constraint=False))
    expire_in_days = Column(Integer, default=0, nullable=False)
    needs_product = Column(Boolean, default=False, nullable=False)
    __mapper_args__ = {'polymorphic_identity': u'retention_tag'}
    jobs = relationship(Job, back_populates='retention_tag', cascade_backrefs=False)

    def __init__(self, tag, is_default=False, **kwargs):
        super(RetentionTag, self).__init__(tag=tag, **kwargs)
        self.set_default_val(is_default)

    @classmethod
    def by_name(cls, tag):
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
            except InvalidRequestError:
                pass
        self.is_default = is_default

    default = property(get_default_val, set_default_val)

    @classmethod
    def get_default(cls, *args, **kw):
        return cls.query.filter(cls.is_default == True).one()

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


class RecipeSet(TaskBase, ActivityMixin):
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
                            order_by=[RecipeSetActivity.created.desc(),
                                      RecipeSetActivity.id.desc()])
    waived = Column(Boolean, nullable=False, default=False)
    comments = relationship('RecipeSetComment', cascade='all, delete-orphan')

    activity_type = RecipeSetActivity

    stop_types = ['abort', 'cancel']

    def __init__(self, ttasks=0, priority=None):
        super(RecipeSet, self).__init__()
        self.ttasks = ttasks
        self.priority = priority

    def __json__(self):
        return self.to_json()

    def to_json(self, include_job=False, include_recipes=True):
        data = self.minimal_json_content()
        data.update({
            'possible_priorities': list(TaskPriority),
            'comments': self.comments
        })

        if identity.current.user:
            u = identity.current.user
            data['can_change_priority'] = self.can_change_priority(u)
            data['allowed_priorities'] = self.allowed_priorities(u)
            data['can_cancel'] = self.can_cancel(u)
            data['can_comment'] = self.can_comment(u)
            data['can_waive'] = self.can_waive(u)
        else:
            data['can_change_priority'] = False
            data['allowed_priorities'] = []
            data['can_cancel'] = False
            data['can_comment'] = False
            data['can_waive'] = False
        if include_job:
            data['job'] = self.job.to_json(include_recipesets=False)
        if include_recipes:
            data['machine_recipes'] = [recipe.to_json(include_results=False)
                                       for recipe in self.machine_recipes]
        return data

    def minimal_json_content(self):
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
            'waived': self.waived,
            'clone_href': self.clone_link(),
            'queue_time': self.queue_time,
        }

    def all_logs(self, load_parent=True):
        """
        Returns an iterator of all logs in this recipeset.
        """
        return (log for recipe in self.recipes
                for log in recipe.all_logs(load_parent=load_parent))

    def set_waived(self, waived):
        self.record_activity(user=identity.current.user, service=u'XMLRPC',
                             field=u'Waived', action=u'Changed',
                             old=unicode(self.waived), new=unicode(waived))
        self.waived = waived

    def is_owner(self, user):
        if self.owner == user:
            return True
        return False

    def can_comment(self, user):
        """Returns True iff the given user can comment on this recipe set."""
        return self.job.can_comment(user)

    def can_waive(self, user):
        """Return True iff the given user can waive this recipe set."""
        return self.job.can_waive(user)

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

    def owner(self):
        return self.job.owner

    owner = property(owner)

    def to_xml(self, clone=False, include_enclosing_job=False, **kwargs):
        recipeSet = etree.Element("recipeSet")
        recipeSet.set('priority', unicode(self.priority))
        return_node = recipeSet

        if not clone:
            # For backwards compatibility, we still use
            # response="ack" and response="nak" in the <recipeSet/> element
            if self.waived:
                recipeSet.set('response', 'nak')
            else:
                recipeSet.set('response', 'ack')

        if not clone:
            recipeSet.set("id", "%s" % self.id)

        for r in self.machine_recipes:
            recipeSet.append(r.to_xml(clone, include_enclosing_job=False, **kwargs))

        if not clone:
            if self.comments:
                comments = etree.Element('comments')
                for c in self.comments:
                    comments.append(E.comment(c.comment, user=c.user.user_name,
                                              created=c.created.strftime('%Y-%m-%d %H:%M:%S')))
                recipeSet.append(comments)

        if include_enclosing_job:
            job = self.job._create_job_elem(clone)
            job.append(recipeSet)
            return_node = job
        return return_node

    @property
    def machine_recipes(self):
        for recipe in self.recipes:
            if not isinstance(recipe, GuestRecipe):
                yield recipe

    def purge(self):
        for r in self.recipes:
            r.purge()

    @classmethod
    def allowed_priorities_initial(cls, user):
        if not user:
            return
        if user.is_admin() or user.has_permission('change_prio'):
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
            tag_query = cls.retention_tag == RetentionTag.by_tag(unicode(tag))

        return query.filter(tag_query)

    @classmethod
    def by_datestamp(cls, datestamp, query=None):
        if not query:
            query = cls.query
        return query.filter(RecipeSet.queue_time <= datestamp)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_job_id(cls, job_id):
        queri = RecipeSet.query.outerjoin('job').filter(Job.id == job_id)
        return queri

    @classmethod
    def by_recipe_status(cls, status):
        """
        Returns a query of RecipeSet objects, filtered to those where *all*
        the recipes in the set have the given status.

        Selecting any column other than recipe_set_id from this query is not
        likely to work.
        """
        # Previously we used a NOT EXISTS for this but it was too slow because
        # MySQL did not pick the recipe.status index. bz1573081
        all_recipes = aliased(Recipe, name='all_recipes')
        matching_recipes = aliased(Recipe, name='matching_recipes')
        return RecipeSet.query \
            .join(all_recipes) \
            .join(matching_recipes,
                  and_(matching_recipes.recipeset, matching_recipes.status == status)) \
            .group_by(RecipeSet.id) \
            .having(
            func.count(all_recipes.id.distinct()) == func.count(matching_recipes.id.distinct()))

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
        status_changed = self._change_status(min_status)
        self.result = max_result

        if status_changed:
            send_scheduler_update(self)

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
        return map(lambda x: MachineRecipe.query.filter_by(id=x[0]).first(),
                   session.connection(RecipeSet).execute(query).fetchall())

    def task_info(self):
        """
        Method for exporting RecipeSet status for TaskWatcher
        """
        return dict(
            id="RS:%s" % self.id,
            worker=None,
            state_label="%s" % self.status,
            state=self.status.value,
            method=None,
            result="%s" % self.result,
            is_finished=self.is_finished(),
            is_failed=self.is_failed(),
            owner="{}".format(self.owner),
            submitter="{}".format(self.job.submitter),
            group="{}".format(self.job.group),
        )

    def allowed_priorities(self, user):
        if not user:
            return []
        if user.is_admin() or user.has_permission('change_prio'):
            return [pri for pri in TaskPriority]
        elif self.can_change_priority(user):
            # Normal users are only allowed to *reduce* the priority,
            # to prevent unfair queue jumping.
            return [pri for pri in TaskPriority
                    if TaskPriority.index(pri) <= TaskPriority.index(self.priority)]
        return []

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
    when = Column(RecipeReservationCondition.db_type(), nullable=False,
                  default=RecipeReservationCondition.always)

    def __json__(self):
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'duration': self.duration,
            'when': unicode(self.when),
        }

    @classmethod
    def empty_json(cls):
        """
        Returns the JSON representation of a default empty reservation request,
        to be used in the cases where a recipe does not have a reservation request
        yet.
        """
        return {
            'id': None,
            'recipe_id': None,
            'duration': cls.__table__.c.duration.default.arg,
            'when': cls.__table__.c.when.default.arg,
        }


class Recipe(TaskBase, ActivityMixin):
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
    installation = relationship(Installation, uselist=False,
                                back_populates='recipe')
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
    # (if not NULL), the generated kickstart for the recipe is stored on the
    # installation
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
    whiteboard = Column(Unicode(4096))
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

    stop_types = ['abort', 'cancel']
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

    def is_owner(self, user):
        return self.recipeset.job.owner == user

    @property
    def is_deleted(self):
        if self.recipeset.job.is_deleted:
            return True
        return False

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
        job = self.recipeset.job
        return "%s/%02d/%s/%s/%s" % (self.recipeset.queue_time.year,
                                     self.recipeset.queue_time.month,
                                     job.id // Log.MAX_ENTRIES_PER_DIRECTORY, job.id, self.id)

    filepath = property(filepath)

    def owner(self):
        return self.recipeset.job.owner

    owner = property(owner)

    def purge(self):
        """
        How we delete a Recipe.
        """
        self.logs = []
        # Hacking up the associated Installation like this is a little dodgy,
        # the idea is just to save on disk space in the kickstart table. In
        # theory no user will ever end up looking at the Installation now that
        # the recipe is deleted anyway...
        if self.installation and self.installation.rendered_kickstart:
            session.delete(self.installation.rendered_kickstart)
            self.installation.rendered_kickstart = None
        for log in self.all_logs(load_parent=False):
            session.delete(log)
        # Delete all the task result rows as well.
        # We need to delete the logs first because of the foreign key constraint.
        session.flush()
        # sqlalchemy can't produce DELETE... JOIN queries yet:
        # https://bitbucket.org/zzzeek/sqlalchemy/issues/959/support-mysql-delete-from-join
        # so we just fake it with the prefixes parameter:
        # http://stackoverflow.com/a/34854513/120202
        query = delete(RecipeTaskResult.__table__.join(RecipeTask),
                       prefixes=[RecipeTaskResult.__table__.name]) \
            .where(RecipeTask.recipe_id == self.id)
        session.connection(RecipeTaskResult).execute(query)

    def task_repo(self):
        return ('beaker-tasks', absolute_url('/repos/%s' % self.id,
                                             scheme='http',
                                             labdomain=True,
                                             webpath=False,
                                             )
                )

    def harness_repo(self):
        """
        return repos needed for harness and task install
        """
        osmajor = self.installation.osmajor
        if os.path.exists("%s/%s" % (self.harnesspath, osmajor)):
            return ('beaker-harness',
                    absolute_url('/harness/%s/' %
                                 osmajor,
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

    def to_xml(self, clone=False, include_enclosing_job=True,
               include_logs=True, **kwargs):
        recipe = etree.Element(self.xml_element_name)
        if not clone:
            recipe.set("id", "%s" % self.id)
            recipe.set("job_id", "%s" % self.recipeset.job.id)
            recipe.set("recipe_set_id", "%s" % self.recipeset.id)
        autopick = etree.Element("autopick")
        autopick.set("random", "%s" % unicode(self.autopick_random).lower())
        recipe.append(autopick)
        recipe.set("whiteboard", "%s" % self.whiteboard and self.whiteboard or '')
        recipe.set("role", "%s" % self.role and self.role or 'RECIPE_MEMBERS')
        if self.kickstart:
            kickstart = etree.Element("kickstart")
            kickstart.text = etree.CDATA('%s' % self.kickstart)
            recipe.append(kickstart)
        if self.installation and self.installation.rendered_kickstart and not clone:
            recipe.set('kickstart_url', self.installation.rendered_kickstart.link)
        recipe.set("ks_meta", "%s" % self.ks_meta and self.ks_meta or '')
        recipe.set("kernel_options", "%s" % self.kernel_options and self.kernel_options or '')
        recipe.set("kernel_options_post",
                   "%s" % self.kernel_options_post and self.kernel_options_post or '')
        if self.start_time and not clone:
            recipe.set('start_time', unicode(self.start_time))
        if self.finish_time and not clone:
            recipe.set('finish_time', unicode(self.finish_time))
        if self.duration and not clone:
            recipe.set("duration", "%s" % self.duration)
        if self.result and not clone:
            recipe.set("result", "%s" % self.result)
        if self.status and not clone:
            recipe.set("status", "%s" % self.status)
        if not clone:
            if self.distro_tree:
                recipe.set("distro", "%s" % self.distro_tree.distro.name)
                recipe.set("arch", "%s" % self.distro_tree.arch)
                recipe.set("family", "%s" % self.distro_tree.distro.osversion.osmajor)
                recipe.set("variant", "%s" % self.distro_tree.variant)
            else:
                recipe.set("distro", "%s" % self.installation.distro_name)
                recipe.set("arch", "%s" % self.installation.arch)
                recipe.set("family", "%s" % self.installation.osmajor)
                recipe.set("variant", "%s" % self.installation.variant)

        watchdog = etree.Element("watchdog")
        if self.panic:
            watchdog.set("panic", "%s" % self.panic)
        recipe.append(watchdog)
        if self.resource and self.resource.fqdn and not clone:
            recipe.set("system", "%s" % self.resource.fqdn)
        if not clone:
            installation = etree.Element('installation')
            if self.installation:
                if self.installation.install_started:
                    installation.set('install_started',
                                     self.installation.install_started.strftime(
                                         '%Y-%m-%d %H:%M:%S'))
                if self.installation.install_finished:
                    installation.set('install_finished',
                                     self.installation.install_finished.strftime(
                                         '%Y-%m-%d %H:%M:%S'))
                if self.installation.postinstall_finished:
                    installation.set('postinstall_finished',
                                     self.installation.postinstall_finished.strftime(
                                         '%Y-%m-%d %H:%M:%S'))
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
        if self.distro_requires:
            drs = etree.XML(self.distro_requires)
        else:
            drs = self.installation.distro_to_xml()

        hrs = etree.XML(self.host_requires)
        prs = etree.XML(self.partitions)
        recipe.append(drs)
        recipe.append(hrs)
        recipe.append(prs)
        if not clone and include_logs:
            logs = etree.Element('logs')
            logs.extend([log.to_xml() for log in self.logs])
            recipe.append(logs)
        for t in self.tasks:
            recipe.append(t.to_xml(clone=clone, include_logs=include_logs, **kwargs))
        if self.reservation_request:
            reservesys = etree.Element("reservesys")
            reservesys.set('duration', unicode(self.reservation_request.duration))
            reservesys.set('when', unicode(self.reservation_request.when))
            recipe.append(reservesys)
        if include_enclosing_job:
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

    @property
    def task_requirements(self):
        """ return all packages required by tasks
        """
        return (TaskPackage.query
                .select_from(RecipeTask).join(Task).join(Task.required)
                .filter(RecipeTask.recipe == self)
                .order_by(TaskPackage.package).distinct().all())

    def _get_arch(self):
        if self.installation:
            return self.installation.arch

    arch = property(_get_arch)

    @property
    def host_requires(self):
        try:
            hrs = etree.fromstring(self._host_requires)
        except ValueError:
            hrs = etree.Element('hostRequires')

        # If no system_type or system/type is not specified then add default value
        if (not hrs.findall('.//system_type')
                and not hrs.findall('.//system/type')
                and not hrs.get('force')):
            system_type = etree.Element('system_type')
            system_type.set('value', unicode(self.systemtype))
            hrs.append(system_type)

        return etree.tostring(hrs, encoding=unicode)

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
        return etree.tostring(prs, encoding=unicode)

    @partitions.setter
    def partitions(self, value):
        """ set _partitions """
        self._partitions = value

    def _parse_partitions(self):
        """ Parse partitions xml """
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
                partitions.append(dict(name=name, type=type, size=size, fs=fs))
            else:
                partitions.append(dict(name=name, type=type, size=size))
        return partitions

    def _partitionsKSMeta(self):
        """ Add partitions into ks_meta variable which cobbler will understand """
        partitions = []
        for partition in self._parse_partitions():
            if partition.get('fs'):
                partitions.append('%s:%s:%s:%s' % (partition['name'],
                                                   partition['type'], partition['size'],
                                                   partition['fs']))
            else:
                partitions.append('%s:%s:%s' % (partition['name'],
                                                partition['type'], partition['size']))
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
                    # something else must have gone wrong
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
        self.clear_candidate_systems()

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

        if self.installation \
                and (self.installation.rebooted or self.installation.install_started) \
                and not self.installation.postinstall_finished \
                and not self.first_task.start_time \
                and not self.first_task.is_finished():
            min_status = TaskStatus.installing

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
            if (self.status in [TaskStatus.installing, TaskStatus.waiting, TaskStatus.running]
                    and self._should_reserve(min_status, max_result)):
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
                and self.status in [TaskStatus.installing, TaskStatus.running]:
            if self.installation.rebooted:
                self.start_time = self.installation.rebooted
            elif self.installation.install_started:  # in case of manual reboot
                self.start_time = self.installation.install_started
            elif self.first_task.start_time:
                self.start_time = self.first_task.start_time
            else:
                self.start_time = datetime.utcnow()

        if self.start_time and not self.finish_time and self.is_finished():
            # Record the completion of this Recipe.
            self.finish_time = datetime.utcnow()

        if status_changed:
            send_scheduler_update(self)

        if status_changed and self.is_finished():
            metrics.increment('counters.recipes_%s' % self.status.name)
            if self.is_suspiciously_aborted and \
                    getattr(self.resource, 'system', None) and self.distro_tree and \
                    get('beaker.reliable_distro_tag', None) in self.distro_tree.distro.tags:
                self.resource.system.suspicious_abort()

        if self.is_finished():
            # If we have any guests which haven't started, kill them now
            # because there is no way they can ever start.
            for guest in getattr(self, 'guests', []):
                if (not guest.is_finished() and
                        guest.watchdog and not guest.watchdog.kill_time):
                    guest.abort(msg=u'Aborted: host %s finished but guest never started'
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

    def _should_reserve(self, status, result):
        if not self.reservation_request:
            return False
        when = self.reservation_request.when
        if when == RecipeReservationCondition.always:
            return True
        elif when == RecipeReservationCondition.onabort:
            return (status == TaskStatus.aborted)
        elif when == RecipeReservationCondition.onfail:
            return (status == TaskStatus.aborted or result == TaskResult.fail)
        elif when == RecipeReservationCondition.onwarn:
            return (status == TaskStatus.aborted or result == TaskResult.fail
                    or result == TaskResult.warn)

    def reduced_install_options(self):
        sources = []
        sources.append(install_options_for_distro(
            self.installation.osmajor,
            self.installation.osminor,
            self.installation.variant,
            self.installation.arch))
        if self.distro_tree:
            sources.append(self.distro_tree.install_options())
        if self.resource:
            sources.extend(self.resource.install_options(arch=self.installation.arch,
                                                         osmajor=self.installation.osmajor,
                                                         osminor=self.installation.osminor))
        sources.append(self.generated_install_options())
        sources.append(InstallOptions.from_strings(self.ks_meta,
                                                   self.kernel_options, self.kernel_options_post))
        return InstallOptions.reduce(sources)

    def provision(self):
        from bkr.server.kickstart import generate_kickstart
        install_options = self.reduced_install_options()
        if self.distro_tree:
            self.installation.tree_url = self.distro_tree.url_in_lab(
                lab_controller=self.recipeset.lab_controller,
                scheme=install_options.ks_meta.get('method', None))
            by_kernel = ImageType.kernel
            by_initrd = ImageType.initrd
            if getattr(self.resource, 'system', None) and self.resource.system.kernel_type:
                if self.resource.system.kernel_type.uboot:
                    by_kernel = ImageType.uimage
                    by_initrd = ImageType.uinitrd
                kernel_type = self.resource.system.kernel_type
            else:
                kernel_type = KernelType.by_name(u'default')
            self.installation.kernel_path = self.distro_tree.image_by_type(
                by_kernel, kernel_type).path
            self.installation.initrd_path = self.distro_tree.image_by_type(
                by_initrd, kernel_type).path

            if 'no_default_harness_repo' not in install_options.ks_meta \
                    and not self.harness_repo():
                raise ValueError('Failed to find repo for harness')
        ks_keyword = install_options.ks_meta.get('ks_keyword', 'inst.ks')
        # Use only user input for kickstart
        no_ks_template = 'no_ks_template' in install_options.ks_meta
        ks_appends = None

        if ks_keyword in install_options.kernel_options:
            # Use it as is
            rendered_kickstart = None
        else:
            if self.kickstart and not no_ks_template:
                # add in cobbler packages snippet...
                packages_slot = 0
                nopackages = True
                for line in self.kickstart.split('\n'):
                    # Add the length of line + newline
                    packages_slot += len(line) + 1
                    if line.find('%packages') == 0:
                        nopackages = False
                        break
                beforepackages = self.kickstart[:packages_slot - 1]
                afterpackages = self.kickstart[packages_slot:]
                # if no %packages section then add it
                if nopackages:
                    beforepackages = "%s\n%%packages --ignoremissing" % beforepackages
                    afterpackages = "{{ end }}\n%s" % afterpackages
                # Fill in basic requirements for RHTS
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
                    beforepackages=beforepackages,
                    afterpackages=afterpackages)
            elif self.kickstart:
                kickstart = self.kickstart
            else:
                kickstart = None
                ks_appends = [ks_append.ks_append for ks_append in self.ks_appends]
            rendered_kickstart = generate_kickstart(install_options=install_options,
                                                    distro_tree=self.distro_tree,
                                                    system=getattr(self.resource, 'system', None),
                                                    user=self.recipeset.job.owner,
                                                    recipe=self,
                                                    ks_appends=ks_appends,
                                                    kickstart=kickstart,
                                                    no_template=no_ks_template)
            install_options.kernel_options[ks_keyword] = rendered_kickstart.link

        self.installation.kernel_options = install_options.kernel_options_str
        self.installation.rendered_kickstart = rendered_kickstart

        if isinstance(self.resource, SystemResource):
            self.installation.system = self.resource.system
            self.resource.system.configure_netboot(installation=self.installation,
                                                   service=u'Scheduler')
            self.resource.system.action_power(action=u'reboot',
                                              installation=self.installation, service=u'Scheduler')
            self.resource.system.record_activity(user=self.recipeset.job.owner,
                                                 service=u'Scheduler', action=u'Provision',
                                                 field=u'Distro Tree', old=u'',
                                                 new=unicode(self.distro_tree))
        elif isinstance(self.resource, VirtResource):
            # Delayed import to avoid circular dependency
            from bkr.server import dynamic_virt
            manager = dynamic_virt.VirtManager(self.recipeset.job.owner)
            manager.start_vm(self.resource.instance_id)
            self.installation.rebooted = datetime.utcnow()
            self.initial_watchdog()

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

    def clear_candidate_systems(self):
        # The simple approach would be:
        # self.systems = []
        # but that triggers a SELECT of all the rows
        # and then a DELETE of each one indvidually. This is faster.
        query = delete(system_recipe_map) \
            .where(system_recipe_map.c.recipe_id == self.id)
        session.connection(self.__class__).execute(query)
        session.expire(self, ['systems'])

    def task_info(self):
        """
        Method for exporting Recipe status for TaskWatcher
        """
        if self.resource:
            worker = {'name': self.resource.fqdn}
        else:
            worker = None
        return dict(
            id="R:%s" % self.id,
            worker=worker,
            state_label="%s" % self.status,
            state=self.status.value,
            method="%s" % self.whiteboard,
            result="%s" % self.result,
            is_finished=self.is_finished(),
            is_failed=self.is_failed(),
            owner="{}".format(self.recipeset.job.owner),
            submitter="{}".format(self.recipeset.job.submitter),
            group="{}".format(self.recipeset.job.group),
        )

    def extend(self, kill_time):
        """
        Extend the watchdog by kill_time seconds
        """
        if not self.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.id))
        if not isinstance(kill_time, numbers.Number):
            raise TypeError('Pass number of seconds to extend the watchdog by')
        if kill_time:
            self.watchdog.kill_time = datetime.utcnow() + timedelta(
                seconds=kill_time)
        else:
            # kill_time of zero is a special case, it means someone wants to
            # end the recipe right now.
            self.watchdog.kill_time = datetime.utcnow()
            # We need to mark the job as dirty so that update_status will take
            # notice and finish the recipe. beaker-watchdog won't be monitoring
            # this recipe since it's no longer active, from its point of view.
            self.recipeset.job._mark_dirty()
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

    def all_logs(self, load_parent=True):
        """
        Returns an iterator of all logs in this recipe.
        """
        # Get all the logs from log_* tables directly to avoid doing N database
        # queries for N results on large recipes.
        recipe_logs = LogRecipe.query \
            .filter(LogRecipe.recipe_id == self.id)
        recipe_task_logs = LogRecipeTask.query \
            .join(LogRecipeTask.parent) \
            .join(RecipeTask.recipe) \
            .filter(Recipe.id == self.id)
        if load_parent:
            recipe_task_logs = recipe_task_logs.options(contains_eager(LogRecipeTask.parent))
        recipe_task_result_logs = LogRecipeTaskResult.query \
            .join(LogRecipeTaskResult.parent) \
            .join(RecipeTaskResult.recipetask) \
            .join(RecipeTask.recipe) \
            .filter(Recipe.id == self.id)
        if load_parent:
            recipe_task_result_logs = recipe_task_result_logs \
                .options(contains_eager(LogRecipeTaskResult.parent))
        return chain(recipe_logs, recipe_task_logs, recipe_task_result_logs)

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
    def position_in_job(self):
        """
        Returns an ordinal indicating the position of this recipe in the job.
        The first recipe is 1, the second recipe is 2, etc.
        """
        # Using a db query for this in order to avoid loading all recipes in
        # the job.
        # Note that recipe sets/recipes have no explicitly persisted ordering,
        # it's implicit based on insertion order which is then reflected in the
        # id ordering. So the ordinal position of this recipe is really the
        # number of recipes in the job with a lower id than this one, plus 1.
        recipes_before_self = Recipe.query.join(RecipeSet) \
            .filter(RecipeSet.job == self.recipeset.job) \
            .filter(Recipe.id < self.id)
        return recipes_before_self.with_entities(func.count(Recipe.id)).scalar() + 1

    @property
    def first_task(self):
        return self.dyn_tasks.order_by(RecipeTask.id).first()

    @property
    def href(self):
        """Returns a relative URL for recipe's page."""
        return urllib.quote(u'/recipes/%s' % self.id)

    def can_edit(self, user=None):
        """Returns True iff the given user can edit this recipe"""
        return self.recipeset.job.can_edit(user)

    def can_update_reservation_request(self, user=None):
        """Returns True iff the given user can update the reservation request"""
        return self.can_edit(user) and self.status not in (TaskStatus.completed,
                                                           TaskStatus.cancelled, TaskStatus.aborted,
                                                           TaskStatus.reserved)

    def can_comment(self, user):
        """Returns True iff the given user can comment on this recipe."""
        return self.recipeset.can_comment(user)

    def get_reviewed_state(self, user):
        if user is None:
            raise RuntimeError('Cannot get reviewed state for anonymous')
        # Delayed import to avoid circular dependency
        from bkr.server.model import RecipeReviewedState
        rrs = session.object_session(self).query(RecipeReviewedState).filter_by(
            recipe_id=self.id, user_id=user.user_id).first()
        if rrs is not None:
            return rrs.reviewed
        return False

    def set_reviewed_state(self, user, reviewed):
        if user is None:
            raise RuntimeError('Cannot set reviewed state for anonymous')
        # Delayed import to avoid circular dependency
        from bkr.server.model import RecipeReviewedState
        RecipeReviewedState.lazy_create(recipe=self, user=user, reviewed=reviewed)

    def initial_watchdog(self):
        if self.first_task.task:
            initial_watchdog = self.first_task.task.avg_time + 1800
        else:
            initial_watchdog = 1800
        self.extend(initial_watchdog)

    def __json__(self):
        return self.to_json()

    def to_json(self, include_recipeset=False, include_tasks=True, include_results=True):
        data = self.minimal_json_content()
        data.update({
            'distro_tree': self.distro_tree,
            'installation': self.installation,
            'ks_meta': self.ks_meta,
            'kernel_options': self.kernel_options,
            'kernel_options_post': self.kernel_options_post,
            'packages': [package.package for package in self.custom_packages],
            'ks_appends': [ks_append.ks_append for ks_append in self.ks_appends],
            'repos': [{'name': repo.name, 'url': repo.url} for repo in self.repos],
            'partitions': self._parse_partitions(),
            'logs': self.logs,
            'possible_systems': [{'fqdn': system.fqdn} for system in self.systems],
            'clone_href': self.clone_link(),
            'position_in_job': self.position_in_job,
            # for backwards compatibility only:
            'recipe_id': self.id,
            'job_id': self.recipeset.job.t_id,
        })
        # watchdog may not have kill time.
        if self.watchdog and self.watchdog.kill_time:
            data['time_remaining_seconds'] = int(total_seconds(self.time_remaining))
        else:
            data['time_remaining_seconds'] = None
        if self.reservation_request:
            data['reservation_request'] = self.reservation_request.__json__()
        else:
            data['reservation_request'] = RecipeReservationRequest.empty_json()
        if self.is_finished() and not self.recipeset.is_finished():
            data['reservation_held_by_recipes'] = \
                [{'id': recipe.id, 't_id': recipe.t_id, 'whiteboard': recipe.whiteboard}
                 for recipe in self.recipeset.recipes if not recipe.is_finished()]
        else:
            data['reservation_held_by_recipes'] = []
        if identity.current.user:
            u = identity.current.user
            data['can_edit'] = self.can_edit(u)
            data['can_set_reviewed_state'] = True
            data['can_update_reservation_request'] = self.can_update_reservation_request(u)
            data['can_comment'] = self.can_comment(u)
            data['reviewed'] = self.get_reviewed_state(u)
        else:
            data['can_edit'] = False
            data['can_set_reviewed_state'] = False
            data['can_update_reservation_request'] = False
            data['can_comment'] = False
            data['reviewed'] = None
        if include_recipeset:
            data['recipeset'] = self.recipeset.to_json(
                include_job=True, include_recipes=False)
        if include_tasks:
            data['tasks'] = [task.to_json(include_results=include_results)
                             for task in self.tasks]
        return data

    def minimal_json_content(self):
        return {
            'id': self.id,
            't_id': self.t_id,
            'status': self.status,
            'is_finished': self.is_finished(),
            'is_deleted': self.is_deleted,
            'result': self.result,
            'whiteboard': self.whiteboard,
            'role': self.role,
            'resource': self.resource,
            'ntasks': self.ntasks,
            'ptasks': self.ptasks,
            'wtasks': self.wtasks,
            'ftasks': self.ftasks,
            'ktasks': self.ktasks,
            'ttasks': self.ttasks,
            'start_time': self.start_time,
            'finish_time': self.finish_time,
        }


def _roles_to_xml(recipe):
    for key, recipes in sorted(recipe.peer_roles().iteritems()):
        role = etree.Element("role")
        role.set("value", "%s" % key)
        for r in recipes:
            if r.resource:
                system = etree.Element("system")
                system.set("value", "%s" % r.resource.fqdn)
                role.append(system)
        yield (role)


# The recipe status will change Waiting <-> Installing based on the timestamps
# recorded on the installation. So we need to ensure that the job is marked
# dirty whenever a timestamp is recorded, so that beakerd will call update_status.
def _mark_installation_recipe_dirty(installation, value, oldvalue, initiator):
    if installation.recipe:
        installation.recipe.recipeset.job._mark_dirty()


event.listen(Installation.rebooted, 'set', _mark_installation_recipe_dirty)
event.listen(Installation.install_started, 'set', _mark_installation_recipe_dirty)
event.listen(Installation.install_finished, 'set', _mark_installation_recipe_dirty)
event.listen(Installation.postinstall_finished, 'set', _mark_installation_recipe_dirty)


class GuestRecipe(Recipe):
    __tablename__ = 'guest_recipe'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('recipe.id'), primary_key=True)
    guestname = Column(UnicodeText)
    guestargs = Column(UnicodeText)
    __mapper_args__ = {'polymorphic_identity': u'guest_recipe'}
    hostrecipe = relationship('MachineRecipe', secondary=machine_guest_map,
                              uselist=False, back_populates='guests')

    xml_element_name = 'guestrecipe'
    systemtype = 'Virtual'

    def to_json(self, include_hostrecipe=True, **kwargs):
        data = super(GuestRecipe, self).to_json(**kwargs)
        data['guestname'] = self.guestname
        data['guestargs'] = self.guestargs
        if include_hostrecipe:
            data['hostrecipe'] = self.hostrecipe.to_json(include_guests=False,
                                                         include_tasks=False,
                                                         include_recipeset=False)
        return data

    def to_xml(self, clone=False, **kwargs):
        node = super(GuestRecipe, self).to_xml(clone=clone, **kwargs)
        # Note that node may be either a job element or a guestrecipe element,
        # depending on the value of include_enclosing_job kwarg.
        if node.tag != self.xml_element_name:
            recipe = node.find('.//' + self.xml_element_name)
        else:
            recipe = node
        recipe.set("guestname", "%s" % (self.guestname or ""))
        recipe.set("guestargs", "%s" % self.guestargs)
        if self.resource and self.resource.mac_address and not clone:
            recipe.set("mac_address", "%s" % self.resource.mac_address)
        if not clone:
            if self.installation and self.installation.tree_url:
                recipe.set('location', self.installation.tree_url)
            elif self.distro_tree and self.recipeset.lab_controller:
                # We are producing XML for an old recipe provisioned prior to Beaker 25.
                # We used to call reduced_install_options() to find the value
                # of the method= ksmeta var and use that to pick the right
                # distro tree URL. However that code path no longer works for
                # old recipes. This is a second-best attempt. Really, people
                # should not expect the location="" attribute to be reliable
                # after the guest recipe has completed.
                installopts = InstallOptions.from_strings(self.ks_meta, '', '')
                method = installopts.ks_meta.get('method', None)
                location = self.distro_tree.url_in_lab(
                    self.recipeset.lab_controller, scheme=method)
                if location:
                    recipe.set("location", location)
        if self.distro_tree and self.recipeset.lab_controller and not clone:
            scheme_locations = {}
            for lca in self.distro_tree.lab_controller_assocs:
                if lca.lab_controller == self.recipeset.lab_controller:
                    scheme = urlparse.urlparse(lca.url).scheme
                    scheme_locations[scheme] = lca.url
            for scheme, location in sorted(scheme_locations.iteritems()):
                attr = '%s_location' % re.sub(r'[^a-z0-9]+', '_', scheme.lower())
                recipe.set(attr, location)
        return node

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
        return etree.tostring(drs, encoding=unicode)

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

    xml_element_name = 'recipe'
    systemtype = 'Machine'

    def to_json(self, include_guests=True, **kwargs):
        data = super(MachineRecipe, self).to_json(**kwargs)
        if include_guests:
            data['guest_recipes'] = [g.to_json(include_hostrecipe=False,
                                               include_recipeset=False,
                                               include_tasks=kwargs.get('include_tasks', True))
                                     for g in self.guests]
        return data

    def to_xml(self, clone=False, include_enclosing_job=True, **kwargs):
        recipe = super(MachineRecipe, self).to_xml(clone=clone,
                                                   include_enclosing_job=include_enclosing_job,
                                                   **kwargs)
        # insert <guestrecipe>s at the top above other child elements
        recipe[0:0] = [guest.to_xml(clone, include_enclosing_job=False, **kwargs)
                       for guest in self.guests]
        return recipe

    def check_virtualisability(self):
        """
        Decide whether this recipe can be run as a virt guest
        """
        # The job owner needs to create a Keystone trust
        if not self.recipeset.job.owner.openstack_trust_id:
            return RecipeVirtStatus.skipped
        # OpenStack is i386/x86_64 only
        if self.installation.arch.arch not in [u'i386', u'x86_64']:
            return RecipeVirtStatus.precluded
        # Can't run VMs in a VM
        if self.guests:
            return RecipeVirtStatus.precluded
        # Multihost testing won't work (for now!)
        if len(self.recipeset.recipes) > 1:
            return RecipeVirtStatus.precluded
        # The distro needs to support DHCP option 26
        install_options = self.reduced_install_options()
        if 'has_dhcp_mtu_support' not in install_options.ks_meta:
            return RecipeVirtStatus.precluded
        # Check for any host requirements which cannot be virtualised
        # Delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import XmlHost
        host_filter = XmlHost.from_string(self.host_requires)
        if not host_filter.virtualisable():
            return RecipeVirtStatus.precluded
        # iPXE understands only FTP and HTTP URLs
        if not self.installation_tree_is_virt_compatible():
            return RecipeVirtStatus.precluded
        # Checks all passed, so dynamic virt should be attempted
        return RecipeVirtStatus.possible

    def installation_tree_is_virt_compatible(self):
        """Check if tree_url can be run as a virt guest"""
        url_compatible = False
        if self.installation.tree_url:
            url_compatible = urlparse.urlparse(self.installation.tree_url).scheme in ['http', 'ftp']
        elif self.distro_tree and not self.recipeset.lab_controller:
            # No way to determine now
            url_compatible = True
        elif self.distro_tree:
            url_compatible = bool(self.distro_tree.url_in_lab(self.recipeset.lab_controller,
                                                              scheme=['http', 'ftp'],
                                                              required=False))
        return url_compatible

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
        systems = systems.filter(System.can_reserve(self.recipeset.job.owner))
        # delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import XmlHost
        host_filter = XmlHost.from_string(self.host_requires)
        if not host_filter.force:
            systems = host_filter.apply_filter(systems). \
                filter(System.status == SystemStatus.automated)
            systems = systems.filter(System.compatible_with_distro_tree(arch=self.installation.arch,
                                                                        osmajor=self.installation.osmajor,
                                                                        osminor=self.installation.osminor))
        else:
            systems = systems.filter(System.fqdn == host_filter.force). \
                filter(System.status != SystemStatus.removed)
        # If it's a user-supplied distro, assume we can use any lab.
        if self.distro_tree and only_in_lab:
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
        systems = systems.filter(System.can_reserve(user))
        # delayed import to avoid circular dependency
        from bkr.server.needpropertyxml import XmlHost
        systems = XmlHost.from_string('<hostRequires><system_type value="%s"/></hostRequires>' %
                                      cls.systemtype).apply_filter(systems)
        if not force:
            systems = systems.filter(System.status == SystemStatus.automated)
            if distro_tree:
                systems = systems.filter(System.compatible_with_distro_tree(arch=distro_tree.arch,
                                                                            osmajor=distro_tree.distro.osversion.osmajor.osmajor,
                                                                            osminor=distro_tree.distro.osversion.osminor))
        else:
            systems = systems.filter(System.status != SystemStatus.removed)
        if distro_tree:
            systems = systems.filter(System.in_lab_with_distro_tree(distro_tree))
        if lab_controller:
            systems = systems.filter(System.lab_controller == lab_controller)
        systems = System.scheduler_ordering(user, query=systems)
        return systems

    def matching_systems(self):
        """
        Returns a query of systems which are free to run this recipe *right now*.
        Note that this returns a filtered-down version of the candidate system
        list (recipe.systems) which is populated by beakerd from the
        .candidate_systems() query above.
        """
        # The system must be in a lab where this recipe's distro tree is available.
        if self.distro_tree:
            eligible_labcontrollers = set(
                lca.lab_controller for lca in self.distro_tree.lab_controller_assocs)
        else:
            eligible_labcontrollers = set(LabController.query.filter_by(removed=None).all())
        # This recipe's guest recipes' distro trees must also be in the lab.
        for guestrecipe in self.guests:
            if guestrecipe.distro_tree:
                eligible_labcontrollers.intersection_update(lca.lab_controller
                                                            for lca in
                                                            guestrecipe.distro_tree.lab_controller_assocs)
        # Another recipe in the set might have locked us to a specific lab.
        if self.recipeset.lab_controller:
            eligible_labcontrollers.intersection_update([self.recipeset.lab_controller])
        if not eligible_labcontrollers:
            return None
        return self.dyn_systems \
            .join(System.lab_controller) \
            .outerjoin(System.cpu) \
            .filter(System.user == None) \
            .filter(System.scheduler_status == SystemSchedulerStatus.idle) \
            .filter(System.lab_controller_id.in_([lc.id for lc in eligible_labcontrollers])) \
            .filter(LabController.disabled == False) \
            .filter(or_(System.loaned == None, System.loaned == self.recipeset.job.owner))

    @classmethod
    def runnable_on_system(cls, system):
        """
        Like .matching_systems() but from the other direction.
        Returns a query of Recipes which are ready to be run on the given system.
        """
        recipes = system.dyn_queued_recipes \
            .join(Recipe.recipeset) \
            .join(RecipeSet.job) \
            .filter(not_(Job.is_deleted)) \
            .filter(Recipe.status == TaskStatus.queued)
        # The recipe set might be locked to a specific lab by an earlier recipe in the set.
        recipes = recipes.filter(or_(
            RecipeSet.lab_controller == None,
            RecipeSet.lab_controller == system.lab_controller))
        # The recipe's distro tree must be available in the same lab as the system.
        recipes = recipes.filter(or_(
            Recipe.distro_tree_id == None,
            LabControllerDistroTree.query
            .filter(LabControllerDistroTree.lab_controller == system.lab_controller)
            .filter(LabControllerDistroTree.distro_tree_id == Recipe.distro_tree_id)
            .exists().correlate(Recipe)))
        # All of the recipe's guest recipe's distros must also be available in the lab.
        # We have to use the outer-join-not-NULL trick because we want
        # *all* guests, not *any* guest.
        guestrecipe = aliased(Recipe, name='guestrecipe')
        recipes = recipes.filter(not_(exists([1],
                                             from_obj=machine_guest_map
                                             .join(Recipe.__table__.alias('guestrecipe'))
                                             .join(DistroTree.__table__)
                                             .outerjoin(LabControllerDistroTree.__table__,
                                                        and_(
                                                            LabControllerDistroTree.distro_tree_id == DistroTree.id,
                                                            LabControllerDistroTree.lab_controller == system.lab_controller)))
                                      .where(machine_guest_map.c.machine_recipe_id == Recipe.id)
                                      .where(LabControllerDistroTree.id == None)
                                      .correlate(Recipe)))
        # If the system is loaned, it can only run recipes belonging to the loanee.
        if system.loaned:
            recipes = recipes.filter(Job.owner == system.loaned)
        return recipes


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


class RecipeTask(TaskBase):
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
    logs = relationship(LogRecipeTask, back_populates='parent',
                        cascade='all, delete-orphan')
    watchdog = relationship(Watchdog, uselist=False)

    result_types = ['pass_', 'warn', 'fail', 'panic', 'result_none', 'skip']
    stop_types = ['stop', 'abort', 'cancel']

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
        return self.to_json()

    def to_json(self, include_results=True):
        data = self.minimal_json_content()
        data.update({
            'distro_tree': self.recipe.distro_tree,
            'fetch_url': self.fetch_url,
            'fetch_subdir': self.fetch_subdir,
            'role': self.role,
            'params': self.params,
            'logs': self.logs,
            'comments': self.comments,
        })
        if self.task:
            data['task'] = {
                'id': self.task.id,
                'name': self.task.name
            }
        else:
            data['task'] = None
        if identity.current.user:
            u = identity.current.user
            data['can_comment'] = self.can_comment(u)
        else:
            data['can_comment'] = False
        if include_results:
            data['results'] = self.results
        return data

    def minimal_json_content(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'status': unicode(self.status),
            'recipe_id': self.recipe_id,
            't_id': self.t_id,
            'is_finished': self.is_finished(),
            'start_time': self.start_time,
            'finish_time': self.finish_time,
            'result': self.result,
        }

    def filepath(self):
        """
        Return file path for this task
        """
        job = self.recipe.recipeset.job
        recipe = self.recipe
        return "%s/%02d/%s/%s/%s/%s" % (recipe.recipeset.queue_time.year,
                                        recipe.recipeset.queue_time.month,
                                        job.id // Log.MAX_ENTRIES_PER_DIRECTORY, job.id,
                                        recipe.id, self.id)

    filepath = property(filepath)

    def to_xml(self, clone=False, include_logs=True, **kwargs):
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
            if self.start_time:
                task.set('start_time', unicode(self.start_time))
            if self.finish_time:
                task.set('finish_time', unicode(self.finish_time))
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
        if not clone and include_logs:
            logs = etree.Element('logs')
            logs.extend([log.to_xml() for log in self.logs])
            task.append(logs)
        if self.results and not clone:
            results = etree.Element("results")
            for result in self.results:
                results.append(result.to_xml(include_logs=include_logs, **kwargs))
            task.append(results)
        return task

    def _get_duration(self):
        duration = None
        if self.finish_time and self.start_time:
            duration = self.finish_time - self.start_time
        elif self.start_time and self.watchdog and self.watchdog.kill_time:
            delta = self.watchdog.kill_time - datetime.utcnow().replace(microsecond=0)
            duration = 'Time Remaining %s' % delta
        return duration

    duration = property(_get_duration)

    def link_id(self):
        """ Return a link to this Executed Recipe->Task
        """
        return make_link(url='/recipes/%s#task%s' % (self.recipe.id, self.id),
                         text='T:%s' % self.id)

    link_id = property(link_id)

    @property
    def name_markup(self):
        """
        Returns HTML markup (in the form of a kid.Element) displaying the name.
        The name is linked to the task library when applicable.
        """
        if self.task:
            return make_link(url='/tasks/%s' % self.task.id,
                             text=self.name)
        else:
            span = Element('span')
            span.text = self.name
            return span

    def all_logs(self, load_parent=True):
        """
        Returns an iterator all logs in this task.
        """
        recipe_task_logs = LogRecipeTask.query \
            .filter(LogRecipeTask.recipe_task_id == self.id)
        recipe_task_result_logs = LogRecipeTaskResult.query \
            .join(LogRecipeTaskResult.parent) \
            .join(RecipeTaskResult.recipetask) \
            .filter(RecipeTask.id == self.id)
        if load_parent:
            recipe_task_result_logs = recipe_task_result_logs \
                .options(contains_eager(LogRecipeTaskResult.parent))
        return chain(recipe_task_logs, recipe_task_result_logs)

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
            send_scheduler_update(self)

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
        if self.is_finished():
            raise ValueError('Cannot change status for finished task %s' % self.t_id)
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

    def skip(self, path, score, summary):
        return self._result(TaskResult.skip, path, score, summary)

    def _result(self, result, path, score, summary):
        """
        Record a result
        """
        if self.is_finished():
            raise ValueError('Cannot record result for finished task %s' % self.t_id)
        # see https://bugzilla.redhat.com/show_bug.cgi?id=1586049
        # and https://bugzilla.redhat.com/show_bug.cgi?id=1600281
        # MySQL 5.x (non-strict) was coercing whatever string passed in to an
        # int value, and silently capping it at the maximum representable
        # value, whereas MariaDB (strict) will raise an error. This is a
        # backwards compatible "hack" for the same MySQL 5.x behaviour.
        if isinstance(score, basestring):
            number_match = re.match('-?\d+(\.\d+)?', score)
            if not number_match:
                score = 0
            else:
                score = round(decimal.Decimal(number_match.group()))
        score = min(score, RecipeTaskResult.max_score)
        recipeTaskResult = RecipeTaskResult(recipetask=self,
                                            path=path,
                                            result=result,
                                            score=score,
                                            log=summary)
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
            id="T:%s" % self.id,
            worker=worker,
            state_label="%s" % self.status,
            state=self.status.value,
            method="%s" % self.name,
            result="%s" % self.result,
            is_finished=self.is_finished(),
            is_failed=self.is_failed(),
            owner="{}".format(self.recipe.recipeset.job.owner),
            submitter="{}".format(self.recipe.recipeset.job.submitter),
            group="{}".format(self.recipe.recipeset.job.group),
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

    def can_comment(self, user):
        """Returns True iff the given user can comment on this recipe task."""
        return self.recipe.can_comment(user)


Index('ix_recipe_task_name_version', RecipeTask.name, RecipeTask.version)


class RecipeTaskParam(DeclarativeMappedObject):
    """
    Parameters for task execution.
    """

    __tablename__ = 'recipe_task_param'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'), nullable=False)
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

    def __json__(self):
        return {
            'id': self.id,
            'name': self.name,
            'value': self.value
        }


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


class RecipeTaskResult(TaskBase):
    """
    Each task can report multiple results
    """

    __tablename__ = 'recipe_task_result'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id'), nullable=False)
    recipetask = relationship(RecipeTask, back_populates='results')
    path = Column(Unicode(2048))
    result = Column(TaskResult.db_type(), nullable=False, default=TaskResult.new)
    score = Column(Numeric(10, 0))
    log = Column(UnicodeText)
    start_time = Column(DateTime, default=datetime.utcnow)
    logs = relationship(LogRecipeTaskResult, back_populates='parent',
                        cascade='all, delete-orphan')
    comments = relationship('RecipeTaskResultComment', back_populates='recipetaskresult')

    #: Maximum allowable value for the score column.
    max_score = 10 ** score.type.precision - 1

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
        job = self.recipetask.recipe.recipeset.job
        recipe = self.recipetask.recipe
        task_id = self.recipetask.id
        return "%s/%02d/%s/%s/%s/%s/%s" % (recipe.recipeset.queue_time.year,
                                           recipe.recipeset.queue_time.month,
                                           job.id // Log.MAX_ENTRIES_PER_DIRECTORY, job.id,
                                           recipe.id, task_id, self.id)

    filepath = property(filepath)

    def to_xml(self, include_logs=True, **kwargs):
        """
        Return result in xml
        """
        result = E.result(
            unicode(self.log),
            id=unicode(self.id),
            path=unicode(self.path),
            result=unicode(self.result),
            score=unicode(self.score),
            start_time=unicode(self.start_time),
        )
        if include_logs and self.logs:
            logs = E.logs()
            logs.extend([log.to_xml() for log in self.logs])
            result.append(logs)
        return result

    def all_logs(self):
        """
        Returns an iterator of all logs in this result.
        """
        return iter(self.logs)

    def task_info(self):
        """
        Method for exporting RecipeTaskResult status for TaskWatcher
        """
        return dict(
            id="TR:%s" % self.id,
            worker=dict(name="%s" % None),
            state_label="%s" % self.result,
            state=self.result.value,
            method="%s" % self.path,
            result="%s" % self.result,
            is_finished=True,
            is_failed=False
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
        The duration can be None if the task was never started.
        """
        index = self.recipetask.results.index(self)
        if index == 0:
            if self.recipetask.start_time:
                return self.start_time - self.recipetask.start_time
            else:
                return None
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

    def can_comment(self, user):
        """Returns True iff the given user can comment on this recipe task result."""
        return self.recipetask.can_comment(user)

    def __json__(self):
        data = {
            'id': self.id,
            'path': self.path,
            'message': self.log,
            'result': self.result,
            'score': self.score,
            'start_time': self.start_time,
            'logs': self.logs,
            'comments': self.comments,
        }
        if identity.current.user:
            u = identity.current.user
            data['can_comment'] = self.can_comment(u)
        else:
            data['can_comment'] = False
        return data


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
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': None}

    def __str__(self):
        return unicode(self).encode('utf8')

    def __unicode__(self):
        return unicode(self.fqdn)

    def __json__(self):
        return {
            'fqdn': self.fqdn,
            'type': self.type,
        }

    @staticmethod
    def _lowest_free_mac():
        base_addr = netaddr.EUI(get('beaker.base_mac_addr', '52:54:00:00:00:00'))
        session.flush()
        # This subquery gives all MAC addresses in use right now
        guest_mac_query = session.query(GuestResource.mac_address.label('mac_address')) \
            .filter(GuestResource.mac_address != None) \
            .join(RecipeResource.recipe).join(Recipe.recipeset) \
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
                                                                       onclause=left_side.c.mac_address + 1 == right_side.c.mac_address)) \
                                   .where(right_side.c.mac_address == None) \
                                   .where(left_side.c.mac_address + 1 >= int(base_addr)) \
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
        data = super(SystemResource, self).__json__()
        data['system'] = self.system
        return data

    @property
    def mac_address(self):
        # XXX the type of system.mac_address should be changed to MACAddress,
        # but for now it's not
        return netaddr.EUI(self.system.mac_address, dialect=mac_unix_padded_dialect)

    @property
    def link(self):
        return make_link(url='/view/%s' % self.system.fqdn,
                         text=self.fqdn)

    def install_options(self, arch, osmajor, osminor):
        return self.system.install_options(arch, osmajor, osminor)

    def allocate(self):
        log.debug('Reserving system %s for recipe %s', self.system, self.recipe.id)
        self.reservation = self.system.reserve_for_recipe(
            service=u'Scheduler',
            user=self.recipe.recipeset.job.owner)

    def release(self):
        # Note that this may be called *many* times for a recipe, even when it
        # has already been cleaned up, so we have to handle that gracefully
        # (and cheaply!)
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
    network_id = Column(UUID, nullable=True)
    subnet_id = Column(UUID, nullable=True)
    router_id = Column(UUID, nullable=True)
    floating_ip = Column(IPAddress(), nullable=True, default=None)
    instance_created = Column(DateTime, nullable=True, default=None)
    instance_deleted = Column(DateTime, nullable=True, default=None)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id',
                                                   name='virt_resource_lab_controller_id_fk'))
    lab_controller = relationship(LabController)
    __mapper_args__ = {'polymorphic_identity': ResourceType.virt}

    @classmethod
    def by_instance_id(cls, instance_id):
        if isinstance(instance_id, basestring):
            instance_id = uuid.UUID(instance_id)
        return cls.query.filter(cls.instance_id == instance_id).one()

    def __init__(self, instance_id, network_id, subnet_id, router_id, floating_ip,
                 lab_controller):
        super(VirtResource, self).__init__()
        if isinstance(instance_id, basestring):
            instance_id = uuid.UUID(instance_id)
        self.instance_id = instance_id
        if isinstance(network_id, basestring):
            network_id = uuid.UUID(network_id)
        self.network_id = network_id
        if isinstance(subnet_id, basestring):
            subnet_id = uuid.UUID(subnet_id)
        self.subnet_id = subnet_id
        if isinstance(router_id, basestring):
            router_id = uuid.UUID(router_id)
        self.router_id = router_id
        self.floating_ip = floating_ip
        self.lab_controller = lab_controller

    @validates('network_id')
    def validate_network_id(self, key, network_id):
        if not network_id:
            raise ValueError('OpenStack instance must have an associated network')
        return network_id

    @validates('subnet_id')
    def validate_subnet_id(self, key, subnet_id):
        if not subnet_id:
            raise ValueError('OpenStack instance must have an associated subnet')
        return subnet_id

    @validates('router_id')
    def validate_router_id(self, key, router_id):
        if not router_id:
            raise ValueError('OpenStack instance must have an associated router')
        return router_id

    @validates('floating_ip')
    def validate_floating_ip(self, key, floating_ip):
        if not floating_ip:
            raise ValueError('OpenStack instance must have an associated floating ip address')
        return floating_ip

    def __repr__(self):
        return '%s(fqdn=%r, instance_id=%r, lab_controller=%r)' % (
            self.__class__.__name__, self.fqdn, self.instance_id,
            self.lab_controller)

    def __json__(self):
        data = super(VirtResource, self).__json__()
        data['instance_id'] = unicode(self.instance_id)
        data['floating_ip'] = unicode(self.floating_ip)
        data['instance_created'] = self.instance_created
        data['instance_deleted'] = self.instance_deleted
        data['href'] = self.href
        return data

    @property
    def link(self):
        span = Element('span')
        span.text = u''
        if self.fqdn:
            if self.fqdn.endswith('.openstacklocal'):
                span.text += unicode(self.floating_ip) + u' '
            else:
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

    def install_options(self, arch, osmajor, osminor):
        yield InstallOptions.from_strings('hwclock_is_utc', u'console=tty0 console=ttyS0,115200n8',
                                          '')

    def release(self):
        # Note that this may be called *many* times for a recipe, even when it
        # has already been cleaned up, so we have to handle that gracefully
        # (and cheaply!)
        if self.instance_deleted:
            return
        try:
            log.debug('Releasing vm %s for recipe %s',
                      self.instance_id, self.recipe.id)
            # Delayed import to avoid circular dependency
            from bkr.server import dynamic_virt
            manager = dynamic_virt.VirtManager(self.recipe.recipeset.job.owner)
            manager.destroy_vm(self)
            self.instance_deleted = datetime.utcnow()
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

    @property
    def link(self):
        return self.fqdn  # just text, not a link

    def install_options(self, arch, osmajor, osminor):
        ks_meta = {
            'hwclock_is_utc': True,
        }
        yield InstallOptions(ks_meta, {}, {})

    def allocate(self):
        self.mac_address = self._lowest_free_mac()
        log.debug('Allocated MAC address %s for recipe %s', self.mac_address, self.recipe.id)

    def release(self):
        # Note that this may be called *many* times for a recipe, even when it
        # has already been cleaned up, so we have to handle that gracefully
        # (and cheaply!)
        pass
