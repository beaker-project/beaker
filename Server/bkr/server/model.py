import sys
import re
from turbogears.database import metadata, session
from turbogears.config import get
from turbogears import url
from copy import copy
import ldap
from sqlalchemy import (Table, Column, Index, ForeignKey, UniqueConstraint,
                        String, Unicode, Integer, DateTime,
                        UnicodeText, Boolean, Float, VARCHAR, TEXT, Numeric,
                        or_, and_, not_, select, case, func, BigInteger)

from sqlalchemy.orm import relation, backref, synonym, dynamic_loader, \
        query, object_mapper, mapper, column_property, contains_eager
from sqlalchemy.orm.interfaces import AttributeExtension
from sqlalchemy.orm.attributes import NEVER_SET
from sqlalchemy.sql import exists, union
from sqlalchemy.sql.expression import join
from sqlalchemy.exc import InvalidRequestError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import TypeDecorator
from identity import LdapSqlAlchemyIdentityProvider
from bkr.server.installopts import InstallOptions, global_install_options
from sqlalchemy.orm.collections import attribute_mapped_collection, MappedCollection, collection
from sqlalchemy.util import OrderedDict
from sqlalchemy.ext.associationproxy import association_proxy
import socket
from xmlrpclib import ProtocolError
import time
from kid import Element
from bkr.server.bexceptions import BeakerException, BX, VMCreationFailedException
from bkr.server.enum import DeclEnum
from bkr.server.helpers import *
from bkr.server.util import unicode_truncate, absolute_url
from bkr.server import mail, metrics
import traceback
from BasicAuthTransport import BasicAuthTransport
import xmlrpclib
import bkr.timeout_xmlrpclib
import os
import shutil
import urllib
import urlparse
import posixpath
import crypt
import random
import string
import cracklib
import lxml.etree
import netaddr
from bkr.common.helpers import Flock, makedirs_ignore, unlink_ignore
import subprocess
from turbogears import identity
import ovirtsdk.api
from datetime import timedelta, date, datetime
from hashlib import md5
import xml.dom.minidom
from xml.dom.minidom import Node, parseString

import logging
log = logging.getLogger(__name__)

class TaskStatus(DeclEnum):

    symbols = [
        ('new',       u'New',       dict(severity=10, finished=False, queued=True)),
        ('processed', u'Processed', dict(severity=20, finished=False, queued=True)),
        ('queued',    u'Queued',    dict(severity=30, finished=False, queued=True)),
        ('scheduled', u'Scheduled', dict(severity=40, finished=False, queued=True)),
        # RUNNING and WAITING are transient states.  It will never be final.
        #  But having it the lowest Severity will show a job as 
        #  Running until it finishes with either Completed, Cancelled or 
        #  Aborted.
        ('waiting',   u'Waiting',   dict(severity=7, finished=False, queued=False)),
        ('running',   u'Running',   dict(severity=5, finished=False, queued=False)),
        ('completed', u'Completed', dict(severity=50, finished=True, queued=False)),
        ('cancelled', u'Cancelled', dict(severity=60, finished=True, queued=False)),
        ('aborted',   u'Aborted',   dict(severity=70, finished=True, queued=False)),
    ]

    @classmethod
    def max(cls):
        return max(cls, key=lambda s: s.severity)

class CommandStatus(DeclEnum):

    symbols = [
        ('queued',    u'Queued',    dict()),
        ('running',   u'Running',   dict()),
        ('completed', u'Completed', dict()),
        ('failed',    u'Failed',    dict()),
        ('aborted',   u'Aborted',   dict()),
    ]

class TaskResult(DeclEnum):

    symbols = [
        ('new',   u'New',   dict(severity=10)),
        ('pass_', u'Pass',  dict(severity=20)),
        ('warn',  u'Warn',  dict(severity=30)),
        ('fail',  u'Fail',  dict(severity=40)),
        ('panic', u'Panic', dict(severity=50)),
    ]

    @classmethod
    def min(cls):
        return min(cls, key=lambda r: r.severity)

class TaskPriority(DeclEnum):

    symbols = [
        ('low',    u'Low',    dict()),
        ('medium', u'Medium', dict()),
        ('normal', u'Normal', dict()),
        ('high',   u'High',   dict()),
        ('urgent', u'Urgent', dict()),
    ]

    @classmethod
    def default_priority(cls):
        return cls.normal

class SystemStatus(DeclEnum):

    # Changing a system from a "bad" status to a "good" status will cause its 
    # status_reason to be cleared, see 
    # bkr.server.controller_utilities._SystemSaveFormHandler

    symbols = [
        ('automated', u'Automated', dict(bad=False)),
        ('broken',    u'Broken',    dict(bad=True)),
        ('manual',    u'Manual',    dict(bad=False)),
        ('removed',   u'Removed',   dict(bad=True)),
    ]

class SystemType(DeclEnum):

    symbols = [
        ('laptop',    u'Laptop',    dict()),
        ('machine',   u'Machine',   dict()),
        ('prototype', u'Prototype', dict()),
        ('resource',  u'Resource',  dict()),
    ]


class ReleaseAction(DeclEnum):

    symbols = [
        ('power_off',   u'PowerOff',    dict()),
        ('leave_on',    u'LeaveOn',     dict()),
        ('reprovision', u'ReProvision', dict()),
    ]

class ImageType(DeclEnum):

    symbols = [
        ('kernel', u'kernel', dict()),
        ('initrd', u'initrd', dict()),
        ('live', u'live', dict()),
        ('uimage', u'uimage', dict()),
        ('uinitrd', u'uinitrd', dict())
    ]

class ResourceType(DeclEnum):
    """Type discriminator for RecipeResource classes."""
    symbols = [
        ('system', u'system', dict()),
        ('virt',   u'virt',   dict()),
        ('guest',  u'guest',  dict()),
    ]

class RecipeVirtStatus(DeclEnum):

    symbols = [
        ('possible',    u'Possible',    dict()),
        ('precluded',   u'Precluded',   dict()),
        ('succeeded',   u'Succeeded',   dict()),
        ('skipped',     u'Skipped',     dict()),
        ('failed',      u'Failed',      dict()),
    ]

# A netaddr "dialect" for formatting MAC addresses... this is the most common 
# format, and is expected by virt-install, so I'm not sure why netaddr doesn't 
# ship with it...
class _mac_unix(netaddr.mac_unix):
    word_fmt = '%02x'

class MACAddress(TypeDecorator):
    """
    Database type for MAC (EUI) addresses. Stores them as raw integers, which 
    lets us do arithmetic on them in the database.
    """
    impl = BigInteger

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, netaddr.EUI):
            return int(value)
        return int(netaddr.EUI(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return netaddr.EUI(value, dialect=_mac_unix)

xmldoc = xml.dom.minidom.Document()

def node(element, value):
    node = xmldoc.createElement(element)
    node.appendChild(xmldoc.createTextNode(value))
    return node

hypervisor_table = Table('hypervisor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('hypervisor', Unicode(100), nullable=False),
    mysql_engine='InnoDB',
)

kernel_type_table = Table('kernel_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('kernel_type', Unicode(100), nullable=False),
    Column('uboot', Boolean(), default=False),
    mysql_engine='InnoDB',
)

system_table = Table('system', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn', Unicode(255), nullable=False),
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
           ForeignKey('tg_user.user_id'), nullable=False),
    Column('user_id', Integer,
           ForeignKey('tg_user.user_id')),
    Column('type', SystemType.db_type(), nullable=False),
    Column('status', SystemStatus.db_type(), nullable=False),
    Column('status_reason',Unicode(255)),
    Column('shared', Boolean, default=False),
    Column('private', Boolean, default=False),
    Column('deleted', Boolean, default=False),
    Column('memory', Integer),
    Column('checksum', String(32)),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id')),
    Column('mac_address',String(18)),
    Column('loan_id', Integer,
           ForeignKey('tg_user.user_id')),
    Column('release_action', ReleaseAction.db_type()),
    Column('reprovision_distro_tree_id', Integer,
           ForeignKey('distro_tree.id')),
    Column('hypervisor_id', Integer,
           ForeignKey('hypervisor.id')),
    Column('kernel_type_id', Integer,
           ForeignKey('kernel_type.id'),
           default=select([kernel_type_table.c.id], limit=1).where(kernel_type_table.c.kernel_type==u'default').correlate(None),
           nullable=False),
    mysql_engine='InnoDB',
)

system_cc_table = Table('system_cc', metadata,
        Column('system_id', Integer, ForeignKey('system.id', ondelete='CASCADE',
            onupdate='CASCADE'), primary_key=True),
        Column('email_address', Unicode(255), primary_key=True, index=True),
        mysql_engine='InnoDB',
)

system_device_map = Table('system_device_map', metadata,
    Column('system_id', Integer,
           ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True),
    Column('device_id', Integer,
           ForeignKey('device.id'),
           primary_key=True),
    mysql_engine='InnoDB',
)

arch_table = Table('arch', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('arch', String(20), unique=True),
    mysql_engine='InnoDB',
)

system_arch_map = Table('system_arch_map', metadata,
    Column('system_id', Integer,
           ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
           primary_key=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True),
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

provision_table = Table('provision', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
    Column('arch_id', Integer, ForeignKey('arch.id'), nullable=False),
    mysql_engine='InnoDB',
)

provision_family_table = Table('provision_family', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('provision_id', Integer, ForeignKey('provision.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id'), nullable=False),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
    mysql_engine='InnoDB',
)

provision_family_update_table = Table('provision_update_family', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('provision_family_id', Integer, ForeignKey('provision_family.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('osversion_id', Integer, ForeignKey('osversion.id'), nullable=False),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
    mysql_engine='InnoDB',
)

exclude_osmajor_table = Table('exclude_osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('arch_id', Integer, ForeignKey('arch.id'), nullable=False),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id'), nullable=False),
    mysql_engine='InnoDB',
)

exclude_osversion_table = Table('exclude_osversion', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('arch_id', Integer, ForeignKey('arch.id'), nullable=False),
    Column('osversion_id', Integer, ForeignKey('osversion.id'), nullable=False),
    mysql_engine='InnoDB',
)

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

labinfo_table = Table('labinfo', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('orig_cost', Numeric(precision=16, scale=2, asdecimal=True)),
    Column('curr_cost', Numeric(precision=16, scale=2, asdecimal=True)),
    Column('dimensions', String(255)),
    Column('weight', Numeric(asdecimal=False)),
    Column('wattage', Numeric(asdecimal=False)),
    Column('cooling', Numeric(asdecimal=False)),
    mysql_engine='InnoDB',
)

watchdog_table = Table('watchdog', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('recipe_id', Integer, ForeignKey('recipe.id'), nullable=False),
    Column('recipetask_id', Integer, ForeignKey('recipe_task.id')),
    Column('subtask', Unicode(255)),
    Column('kill_time', DateTime),
    mysql_engine='InnoDB',
)

cpu_table = Table('cpu', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
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
    mysql_engine='InnoDB',
)

cpu_flag_table = Table('cpu_flag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('cpu_id', Integer, ForeignKey('cpu.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('flag', String(255)),
    mysql_engine='InnoDB',
)

numa_table = Table('numa', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('nodes',Integer),
    mysql_engine='InnoDB',
)

device_class_table = Table('device_class', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column("device_class", VARCHAR(24), nullable=False, unique=True),
    Column("description", TEXT),
    mysql_engine='InnoDB',
)

device_table = Table('device', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('vendor_id',String(4)),
    Column('device_id',String(4)),
    Column('subsys_device_id',String(4)),
    Column('subsys_vendor_id',String(4)),
    Column('bus',String(255)),
    Column('driver', String(255), index=True),
    Column('description',String(255)),
    Column('device_class_id', Integer,
           ForeignKey('device_class.id'), nullable=False),
    Column('date_added', DateTime, 
           default=datetime.utcnow, nullable=False),
    UniqueConstraint('vendor_id', 'device_id', 'subsys_device_id',
           'subsys_vendor_id', 'bus', 'driver', 'description', name='device_uix_1'),
    mysql_engine='InnoDB',
)
Index('ix_device_pciid', device_table.c.vendor_id, device_table.c.device_id)

locked_table = Table('locked', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    mysql_engine='InnoDB',
)

power_type_table = Table('power_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('name', String(255), nullable=False),
    mysql_engine='InnoDB',
)

power_table = Table('power', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('power_type_id', Integer, ForeignKey('power_type.id'),
           nullable=False),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('power_address', String(255), nullable=False),
    Column('power_user', String(255)),
    Column('power_passwd', String(255)),
    Column('power_id', String(255)),
    mysql_engine='InnoDB',
)

serial_table = Table('serial', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    mysql_engine='InnoDB',
)

serial_type_table = Table('serial_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    mysql_engine='InnoDB',
)

install_table = Table('install', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
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

lab_controller_table = Table('lab_controller', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn',Unicode(255), unique=True),
    Column('disabled', Boolean, nullable=False, default=False),
    Column('removed', DateTime, nullable=True, default=None),
    Column('user_id', Integer,
           ForeignKey('tg_user.user_id'), nullable=False),
    mysql_engine='InnoDB',
)

osmajor_table = Table('osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor', Unicode(255), unique=True),
    Column('alias', Unicode(25), unique=True),
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

# the identity schema

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    Column('expiry', DateTime),
    mysql_engine='InnoDB',
)


visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True, unique=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'),
            nullable=False, index=True),
    Column('proxied_by_user_id', Integer, ForeignKey('tg_user.user_id'),
            nullable=True),
    mysql_engine='InnoDB',
)

groups_table = Table('tg_group', metadata,
    Column('group_id', Integer, primary_key=True),
    Column('group_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.utcnow),
    mysql_engine='InnoDB',
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(255), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(40)),
    Column('root_password', String(255), nullable=True, default=None),
    Column('rootpw_changed', DateTime, nullable=True, default=None),
    Column('created', DateTime, default=datetime.utcnow),
    Column('disabled', Boolean, nullable=False, default=False),
    Column('removed', DateTime, nullable=True, default=None),
    mysql_engine='InnoDB',
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255)),
    mysql_engine='InnoDB',
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

sshpubkey_table = Table('sshpubkey', metadata,
    Column('id', Integer, autoincrement=True, nullable=False,
        primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('keytype', Unicode(16), nullable=False),
    Column('pubkey', UnicodeText(), nullable=False),
    Column('ident', Unicode(63), nullable=False),
    mysql_engine='InnoDB',
)

system_group_table = Table('system_group', metadata,
    Column('system_id', Integer, ForeignKey('system.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('admin', Boolean, nullable=False, default=False),
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
    Column('tag', Unicode(20), primary_key=True, nullable = False),
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


group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

# activity schema

# TODO This will require some indexes for performance.
activity_table = Table('activity', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow,
           index=True),
    Column('type', Unicode(40), nullable=False),
    Column('field_name', Unicode(40), nullable=False),
    Column('service', Unicode(100), nullable=False),
    Column('action', Unicode(40), nullable=False),
    Column('old_value', Unicode(60)),
    Column('new_value', Unicode(60)),
    mysql_engine='InnoDB',
)

system_activity_table = Table('system_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), nullable=True),
    mysql_engine='InnoDB',
)

lab_controller_activity_table = Table('lab_controller_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id'),
        nullable=False),
    mysql_engine='InnoDB',
)

recipeset_activity_table = Table('recipeset_activity', metadata,
    Column('id', Integer,ForeignKey('activity.id'), primary_key=True),
    Column('recipeset_id', Integer, ForeignKey('recipe_set.id')),
    mysql_engine='InnoDB',
)

group_activity_table = Table('group_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id'),
        nullable=False),
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

command_queue_table = Table('command_queue', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
           onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('status', CommandStatus.db_type(), nullable=False),
    Column('task_id', String(255)),
    Column('delay_until', DateTime, default=None),
    Column('updated', DateTime, default=datetime.utcnow),
    Column('callback', String(255)),
    Column('distro_tree_id', Integer, ForeignKey('distro_tree.id')),
    Column('kernel_options', UnicodeText),
    mysql_engine='InnoDB',
)

# note schema
note_table = Table('note', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id', onupdate='CASCADE',
           ondelete='CASCADE'), nullable=False, index=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    Column('text',TEXT, nullable=False),
    Column('deleted', DateTime, nullable=True, default=None),
    mysql_engine='InnoDB',
)

key_table = Table('key_', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('key_name', String(50), nullable=False, unique=True),
    Column('numeric', Boolean, default=False),
    mysql_engine='InnoDB',
)

key_value_string_table = Table('key_value_string', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False, index=True),
    Column('key_id', Integer, ForeignKey('key_.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False, index=True),
    Column('key_value',TEXT, nullable=False),
    mysql_engine='InnoDB',
)

key_value_int_table = Table('key_value_int', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False, index=True),
    Column('key_id', Integer, ForeignKey('key_.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False, index=True),
    Column('key_value',Integer, nullable=False),
    mysql_engine='InnoDB',
)

job_table = Table('job',metadata,
        Column('id', Integer, primary_key=True),
        Column('owner_id', Integer,
                ForeignKey('tg_user.user_id'), index=True),
        Column('whiteboard',Unicode(2000)),
        Column('retention_tag_id', Integer, ForeignKey('retention_tag.id'), nullable=False),
        Column('product_id', Integer, ForeignKey('product.id'),nullable=True),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new),
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
                default=TaskPriority.default_priority()),
        Column('queue_time',DateTime, nullable=False, default=datetime.utcnow),
        Column('result', TaskResult.db_type(), nullable=False,
                default=TaskResult.new),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new),
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

reservation_table = Table('reservation', metadata,
        Column('id', Integer, primary_key=True),
        Column('system_id', Integer, ForeignKey('system.id'), nullable=False),
        Column('user_id', Integer, ForeignKey('tg_user.user_id'),
            nullable=False),
        Column('start_time', DateTime, index=True, nullable=False,
            default=datetime.utcnow),
        Column('finish_time', DateTime, index=True),
        # type = 'manual' or 'recipe'
        # XXX Use Enum types
        Column('type', Unicode(30), index=True, nullable=False),
        mysql_engine='InnoDB',
)

# this only really exists to make reporting efficient
system_status_duration_table = Table('system_status_duration', metadata,
        Column('id', Integer, primary_key=True),
        Column('system_id', Integer, ForeignKey('system.id'), nullable=False),
        Column('status', SystemStatus.db_type(), nullable=False),
        Column('start_time', DateTime, index=True, nullable=False,
            default=datetime.utcnow),
        Column('finish_time', DateTime, index=True),
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
                default=TaskResult.new),
        Column('status', TaskStatus.db_type(), nullable=False,
                default=TaskStatus.new),
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

task_table = Table('task',metadata,
        Column('id', Integer, primary_key=True),
        Column('name', Unicode(2048)),
        Column('rpm', Unicode(2048)),
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

task_packages_custom_map = Table('task_packages_custom_map', metadata,
    Column('recipe_id', Integer, ForeignKey('recipe.id', onupdate='CASCADE',
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

config_item_table = Table('config_item', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode(255), unique=True),
    Column('description', Unicode(255)),
    Column('numeric', Boolean, default=False),
    Column('readonly', Boolean, default=False),
    mysql_engine='InnoDB',
)

config_value_string_table = Table('config_value_string', metadata,
    Column('id', Integer, primary_key=True),
    Column('config_item_id', Integer, ForeignKey('config_item.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('modified', DateTime, default=datetime.utcnow),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), nullable=False),
    Column('valid_from', DateTime, default=datetime.utcnow),
    Column('value', TEXT, nullable=True),
    mysql_engine='InnoDB',
)

config_value_int_table = Table('config_value_int', metadata,
    Column('id', Integer, primary_key=True),
    Column('config_item_id', Integer, ForeignKey('config_item.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('modified', DateTime, default=datetime.utcnow),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), nullable=False),
    Column('valid_from', DateTime, default=datetime.utcnow),
    Column('value', Integer, nullable=True),
    mysql_engine='InnoDB',
)

class MappedObject(object):

    query = session.query_property()

    @classmethod
    def lazy_create(cls, **kwargs):
        """
        Returns the instance identified by the given uniquely-identifying 
        attributes. If it doesn't exist yet, it is inserted first.
        """
        session.begin_nested()
        try:
            item = cls(**kwargs)
            session.commit()
        except IntegrityError:
            session.rollback()
            item = cls.query.filter_by(**kwargs).one()
        return item

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        # XXX Calling session.add(self) here is a bad idea! We only do it 
        # because it was inherited from TurboGears 1.0 a long time ago. If 
        # something causes the session to be flushed (for example lazy_create) 
        # we could end up trying to persist an object which has not been fully 
        # populated yet. See bug 869455 for an example of this.
        # Beware that some classes are already opting out of this behaviour by 
        # not chaining up to this __init__ method. We should work towards 
        # eliminating it completely.
        session.add(self)

    def __repr__(self):
        # pretty-print the attributes, so we can see what's getting autoloaded for us:
        attrStr = ""
        numAttrs = 0
        for attr in self.__dict__:
            if attr[0] != '_':
                if numAttrs>0:
                    attrStr += ', '
                attrStr += '%s=%s' % (attr, repr(self.__dict__[attr]))
                numAttrs += 1
        return "%s(%s)" % (self.__class__.__name__, attrStr)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

# the identity model
class Visit(MappedObject):
    """
    A visit to your site
    """
    def lookup_visit(cls, visit_key):
        return cls.query.get(visit_key)
    lookup_visit = classmethod(lookup_visit)


class VisitIdentity(MappedObject):
    """
    A Visit that is link to a User object
    """
    pass


class User(MappedObject):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """
    ldapenabled = get("identity.ldap.enabled",False)
    if ldapenabled:
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
        return cls.query.filter_by(email_address=email).one()

    by_email_address = classmethod(by_email_address)

    def email_link(self):
        a = Element('a', {'href': 'mailto:%s' % self.email_address})
        a.text = self.user_name
        return a
    email_link = property(email_link)

    @classmethod
    def by_id(cls, user_id):
        """
        A class method that permits to search users
        based on their user_id attribute.
        """
        return cls.query.filter_by(user_id=user_id).first()
    
    @classmethod
    def by_user_name(cls, user_name):
        """
        A class method that permits to search users
        based on their user_name attribute.
        """
        # Try to look up the user via local DB first.
        user = cls.query.filter_by(user_name=user_name).first()
        # If user doesn't exist in DB check ldap if enabled.
        # Presence of '/' indicates a Kerberos service principal.
        if not user and cls.ldapenabled and '/' not in user_name:
            filter = "(uid=%s)" % user_name
            ldapcon = ldap.initialize(cls.uri)
            rc = ldapcon.search(cls.basedn, ldap.SCOPE_SUBTREE, filter)
            objects = ldapcon.result(rc)[1]
            # no match
            if(len(objects) == 0):
                return None
            # need exact match
            elif(len(objects) > 1):
                return None
            if cls.autocreate:
                user = User()
                user.user_name = user_name
                user.display_name = objects[0][1]['cn'][0]
	        user.email_address = objects[0][1]['mail'][0]
                session.add(user)
                session.flush([user])
        return user

    @classmethod
    def list_by_name(cls, username,find_anywhere=False,find_ldap_users=True):
        ldap_users = []
        if cls.ldapenabled and find_ldap_users is True:
            filter = "(uid=%s*)" % username
            ldapcon = ldap.initialize(cls.uri)
            rc = ldapcon.search(cls.basedn, ldap.SCOPE_SUBTREE, filter)
            objects = ldapcon.result(rc)[1]
            ldap_users = [object[0].split(',')[0].split('=')[1] for object in objects]
        if find_anywhere:
            f = User.user_name.like('%%%s%%' % username)
        else:
            f = User.user_name.like('%s%%' % username)
        # Don't return Removed Users
        # They may still be listed in ldap though.
        db_users = [user.user_name for user in cls.query.filter(f).\
                    filter(User.removed==None)]
        return list(set(db_users + ldap_users))
        
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

    def _set_root_password(self, password):
        "Set the password to be used for root on provisioned systems, hashing if necessary"
        if password:
            if len(password.split('$')) != 4:
                salt = ''.join([random.choice(string.digits + string.ascii_letters)
                                for i in range(8)])
                self._root_password = crypt.crypt(cracklib.VeryFascistCheck(password), "$1$%s$" % salt)
            else:
                self._root_password = password
            self.rootpw_changed = datetime.utcnow()
        else:
            self._root_password = None
            self.rootpw_changed = None

    def _get_root_password(self):
        if self._root_password:
            return self._root_password
        else:
            pw = ConfigItem.by_name(u'root_password').current_value()
            if pw:
                salt = ''.join([random.choice(string.digits + string.ascii_letters)
                                for i in range(8)])
                return crypt.crypt(pw, "$1$%s$" % salt)

    root_password = property(_get_root_password, _set_root_password)

    @property
    def rootpw_expiry(self):
        if not self._root_password:
            return
        validity = ConfigItem.by_name(u'root_password_validity').current_value()
        if validity:
            return self.rootpw_changed + timedelta(days=validity)

    @property
    def rootpw_expired(self):
        if self.rootpw_expiry and self.rootpw_expiry < datetime.utcnow():
            return True
        else:
            return False

    def __repr__(self):
        return self.user_name

    def is_admin(self):
        return u'admin' in [group.group_name for group in self.groups]

    def in_group(self,check_groups):
        my_groups = [group.group_name for group in self.groups]
        for my_g in check_groups:
            if my_g in my_groups:
                return True
        return False

    def has_permission(self, requested_permission):
        """ Check if user has requested permission """
        try:
            permission = Permission.by_name(requested_permission)
        except NoResultFound:
            permission = None
        if permission in self.permissions:
            return True
        return False


class Permission(MappedObject):
    """
    A relationship that determines what each Group can do
    """
    @classmethod
    def by_id(cls, id):
      return cls.query.filter_by(permission_id=id).one()

    @classmethod
    def by_name(cls, permission_name, anywhere=False):
        if anywhere:
            return cls.query.filter(cls.permission_name.like('%%%s%%' % permission_name)).all()
        return cls.query.filter(cls.permission_name == permission_name).one()

    def __init__(self, permission_name):
        super(Permission, self).__init__()
        self.permission_name = permission_name

class SystemObject(MappedObject):
    @classmethod
    def get_tables(cls):
        tables = cls.get_dict().keys()
        tables.sort()
        return tables

    @classmethod
    def get_dict(cls):
        tables = dict( system = dict(joins=[], cls=cls))
        for property in cls.mapper.iterate_properties:
            mapper = getattr(property, 'mapper', None)
            if mapper: 
                remoteTables = {}
                try: 
                    remoteTables = property.mapper.class_._get_dict()
                except Exception: pass
                for key in remoteTables.keys(): 
                    joins = [property.key]
                    joins.extend(remoteTables[key]['joins']) 
                    tables['system/%s/%s' % (property.key, key)] = dict(joins=joins, cls=remoteTables[key]['cls'])
               
                tables['system/%s' % property.key] = dict(joins=[property.key], cls=property.mapper.class_) 
        return tables

    def _get_dict(cls):
        tables = {}
        for property in cls.mapper.iterate_properties:
            mapper = getattr(property, 'mapper', None)
            if mapper:
                remoteTables = {}
                try:
                    remoteTables = property.mapper.class_._get_dict()
                except Exception: pass
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

class Group(MappedObject):
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
    def list_by_name(cls, name, find_anywhere=False):
        """
        A class method that can be used to search groups
        based on the group_name
        """
        if find_anywhere:
            q = cls.query.filter(Group.group_name.like('%%%s%%' % name))
        else:
            q = cls.query.filter(Group.group_name.like('%s%%' % name))
        return q

    @classmethod
    def by_user(cls,user):
        try:
            groups = Group.query.join('users').filter(User.user_id == user.user_id)
            return groups
        except Exception, e: 
            log.error(e)
            return

    systems = association_proxy('system_assocs', 'system',
            creator=lambda system: SystemGroup(system=system))

class System(SystemObject):

    def __init__(self, fqdn=None, status=SystemStatus.broken, contact=None, location=None,
                       model=None, type=SystemType.machine, serial=None, vendor=None,
                       owner=None, lab_controller=None, lender=None,
                       hypervisor=None, loaned=None, memory=None,
                       kernel_type=None):
        super(System, self).__init__()
        self.fqdn = fqdn
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
            except AttributeError, e:
                user = None

        if user:
            if not user.is_admin() and \
               not user.has_permission(u'secret_visible'):
                query = query.filter(
                            or_(System.private==False,
                                System.groups.any(Group.users.contains(user)),
                                System.owner == user,
                                System.loaned == user,
                                System.user == user))
        else:
            query = query.filter(System.private==False)
         
        return query


    @classmethod
    def free(cls, user, systems=None):
        """
        Builds on available.  Only systems with no users, and not Loaned.
        """
        return System.available(user,systems).filter(and_(System.user==None, or_(System.loaned==None, System.loaned==user)))

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

        query = query.filter(or_(and_(System.owner==user), 
                                System.loaned == user,
                                and_(System.shared==True, 
                                     System.group_assocs==None,
                                    ),
                                and_(System.shared==True,
                                     System.groups.any(Group.users.contains(user)),
                                    )
                                )
                            )
        return query


    @classmethod
    def available(cls, user, systems=None):
        """
        Will return systems that are available to user
        """
        return cls._available(user, systems=systems)

    @classmethod
    def available_order(cls, user, systems=None):
        return cls.available_for_schedule(user,systems=systems).order_by(case([(System.owner==user, 1),
                          (and_(System.owner!=user, System.group_assocs != None), 2)],
                              else_=3))

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

    def unreserve_manually_reserved(self, *args, **kw):
        open_reservation = self.open_reservation
        if not open_reservation:
            raise BX(_(u'System %s is not currently reserved' % self.fqdn))
        reservation_type = open_reservation.type
        if reservation_type != 'manual':
            raise BX(_(u'Cannot release %s. Was not manually reserved' % self.fqdn))
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
        result = global_install_options()
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

    def is_admin(self, user=None, *args, **kw):
        # We are either using a passed in user, or the current user, not both
        if not user:
            try:
                user = identity.current.user
            except AttributeError, e: pass #May not be logged in

        if not user: #Can't verify anything
            return False

        if user.is_admin(): #first let's see if we are an _admin_
            return True

        #If we are the owner....
        if self.owner == user:
            return True

        user_groups = user.groups
        if user_groups:
            if any(ga.admin and ga.group in user_groups
                    for ga in self.group_assocs):
                return True

        return False

    def can_admin(self,user=None):
        if user:
            if user == self.owner or user.is_admin() or self.is_admin(user=user):
                return True
        return False

    def can_provision_now(self,user=None):
        if user is None:
            return False
        elif self.loaned == user:
            return True
        elif self._user_in_systemgroup(user):
            return True
        elif user is None:
            return False
        if self.status==SystemStatus.manual: #If it's manual then we us our original perm system.
            return self._has_regular_perms(user)
        return False

    def can_loan(self, user=None):
        if user and not self.loaned:
            if self.can_admin(user):
                return True
        return False

    def current_loan(self, user=None):
        if user and self.loaned:
            if self.loaned == user or \
               self.owner  == user or \
               self.is_admin():
                return True
        return False

    def current_user(self, user=None):
        if user and self.user:
            if self.user  == user \
               or self.can_admin(user):
                return True
        return False

    def _user_in_systemgroup(self,user=None):
        if self.groups:
            for group in user.groups:
                if group in self.groups:
                    return True


    def is_available(self,user=None):
        """
        is_available() will return true if this system is allowed to be used by the user.
        """
        if user:
            if self.shared:
                # If the user is in the Systems groups
                if self.groups:
                    if self._user_in_systemgroup(user):
                        return True
                else:
                    return True
            elif self.loaned and self.loaned == user:
                return True
            elif self.owner == user:
                return True
        
    def can_share(self, user=None):
        """
        can_share() will return True id the system is currently free and allwoed to be used by the user
        """
        if user and not self.user:
            return self._has_regular_perms(user)
        return False

    def _has_regular_perms(self, user=None, *args, **kw):
        """
        This represents the basic system perms,loanee, owner,  shared and in group or shared and no group
        """
        # If user is None then probably not logged in.
        if not user:
            return False
        if self.loaned:
            if user == self.loaned:
                return True
            else:
                return False
        # If its the owner always allow.
        if user == self.owner:
            return True
        if self.shared:
            # If the user is in the Systems groups
            return self._in_group(user)

    def _in_group(self, user=None, *args, **kw):
            if user is None:
                return False
            if self.groups:
                for group in user.groups:
                    if group in self.groups:
                        return True
            else:
                # If the system has no groups
                return True

    ALLOWED_ATTRS = ['vendor', 'model', 'memory'] #: attributes which the inventory scripts may set
    PRESERVED_ATTRS = ['vendor', 'model'] #: attributes which should only be set when empty

    def get_update_method(self,obj_str):
        methods = dict ( Cpu = self.updateCpu, Arch = self.updateArch, 
                         Devices = self.updateDevices, Numa = self.updateNuma,
                         Hypervisor = self.updateHypervisor, )
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
            try:
                new_arch = Arch.by_name(arch)
            except NoResultFound:
                new_arch = Arch(arch=arch)
            if new_arch not in self.arch:
                self.arch.append(new_arch)
                self.activity.append(SystemActivity(
                        user=identity.current.user,
                        service=u'XMLRPC', action=u'Added',
                        field_name=u'Arch', old_value=None,
                        new_value=new_arch.arch))

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
                    .correlate(distro_tree_table)))\
                .filter(not_(OSVersion.excluded_osversions.any(and_(
                    ExcludeOSVersion.system == self,
                    ExcludeOSVersion.arch_id == DistroTree.arch_id))
                    .correlate(distro_tree_table)))
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
            activity = CommandActivity(user, service, action, status, callback)
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
                Recipe.finish_time > nonaborted_recipe_subquery.as_scalar()))\
            .value(func.count(DistroTree.id.distinct()))
        if count >= 2:
            # Broken!
            metrics.increment('counters.suspicious_aborts')
            reason = unicode(_(u'System has a run of aborted recipes ' 
                    'with reliable distros'))
            log.warn(reason)
            self.mark_broken(reason=reason)

    def reserve(self, service, user=None, reservation_type=u'manual'):
        if user is None:
            user = identity.current.user
        if self.user is not None and self.user == user:
            raise BX(_(u'User %s has already reserved system %s')
                    % (user, self))
        if not self.can_share(user):
            raise BX(_(u'User %s cannot reserve system %s')
                    % (user, self))
        # Atomic operation to reserve the system
        session.flush()
        if session.connection(System).execute(system_table.update(
                and_(system_table.c.id == self.id,
                     system_table.c.user_id == None)),
                user_id=user.user_id).rowcount != 1:
            raise BX(_(u'System %r is already reserved') % self)
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

        # Some sanity checks
        if self.user is None:
            raise BX(_(u'System is not reserved'))
        if not self.current_user(user):
            raise BX(_(u'System is reserved by a different user'))

        # Update reservation atomically first, to avoid races
        session.flush()
        my_reservation_id = reservation.id
        if session.connection(System).execute(reservation_table.update(
                and_(reservation_table.c.id == my_reservation_id,
                     reservation_table.c.finish_time == None)),
                finish_time=datetime.utcnow()).rowcount != 1:
            raise BX(_(u'System does not have an open reservation'))
        old_user = self.user
        self.user = None
        self.action_release(service=service)
        activity = SystemActivity(user=user,
                service=service, action=u'Returned', field_name=u'User',
                old_value=old_user.user_name, new_value=u'')
        self.activity.append(activity)

    cc = association_proxy('_system_ccs', 'email_address')

    groups = association_proxy('group_assocs', 'group',
            creator=lambda group: SystemGroup(group=group))

class SystemStatusAttributeExtension(AttributeExtension):

    def set(self, state, child, oldchild, initiator):
        obj = state.obj()
        log.debug('%r status changed from %r to %r', obj, oldchild, child)
        if child == oldchild:
            return child
        if oldchild in (None, NEVER_SET):
            assert not obj.status_durations
        else:
            assert obj.status_durations[0].finish_time is None
            assert obj.status_durations[0].status == oldchild
            obj.status_durations[0].finish_time = datetime.utcnow()
        obj.status_durations.insert(0,
                SystemStatusDuration(system=obj, status=child))
        return child

class SystemCc(SystemObject):

    def __init__(self, email_address):
        super(SystemCc, self).__init__()
        self.email_address = email_address

class SystemGroup(MappedObject):

    pass


class KernelType(SystemObject):

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


class Hypervisor(SystemObject):

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


class OSVersion(MappedObject):
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

    


class LabControllerDistroTree(MappedObject):
    pass


class LabController(SystemObject):
    def __repr__(self):
        return "%s" % (self.fqdn)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(fqdn=name).one()

    @classmethod
    def get_all(cls, valid=False):
        """
        Desktop, Server, Virtual
        """
        all = cls.query
        if valid:
            all = cls.query.filter_by(removed=None)
        return [(lc.id, lc.fqdn) for lc in all]

    # XXX this is a bit sad... RHEV data center names must be <40 chars and
    # cannot contain periods, so we have to munge the fqdn
    @property
    def data_center_name(self):
        return self.fqdn.replace('.', '_')[:40]
    @classmethod
    def by_data_center_name(cls, data_center):
        for lc in cls.query:
            if lc.data_center_name == data_center:
                return lc
        return None


class Watchdog(MappedObject):
    """ Every running task has a corresponding watchdog which will
        Return the system if it runs too long
    """

    @classmethod
    def by_status(cls, labcontroller=None, status="active"):
        """
        Returns a list of all watchdog entries that are either active or 
        expired for this lab controller.

        A recipe is only returned as "expired" if all the recipes in the recipe 
        set have expired. Similarly, a recipe is returned as "active" so long 
        as any recipe in the recipe set is still active. Some tasks rely on 
        this behaviour. In particular, the host recipe in virt testing will 
        finish while its guests are still running, but we want to keep 
        monitoring the host's console log in case of a panic.
        """
        query = cls.query.join(Watchdog.recipe, Recipe.recipeset)
        if labcontroller:
            query = query.filter(RecipeSet.lab_controller == labcontroller)

        REMAP_STATUS = {
            "active"  : dict(
                               op = "__gt__",
                              fop = "max",
                            ),
            "expired" : dict(
                               op = "__le__",
                              fop = "min",
                            ),
        }
        op = REMAP_STATUS.get(status, None)['op']
        fop = REMAP_STATUS.get(status, None)['fop']
        query = query.filter(RecipeSet.id.in_(
                select([recipe_set_table.c.id],
                    from_obj=[watchdog_table.join(recipe_table).join(recipe_set_table)])
                .group_by(RecipeSet.id)
                .having(getattr(func, fop)(
                    getattr(Watchdog.kill_time, op)(datetime.utcnow())))
                ))
        return query

class LabInfo(SystemObject):
    fields = ['orig_cost', 'curr_cost', 'dimensions', 'weight', 'wattage', 'cooling']


class Cpu(SystemObject):
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

class CpuFlag(SystemObject):
    def __init__(self, flag=None):
        super(CpuFlag, self).__init__()
        self.flag = flag

    def __repr__(self):
        return self.flag

    def by_flag(cls, flag):
        return cls.query.filter_by(flag=flag)

    by_flag = classmethod(by_flag)


class Numa(SystemObject):
    def __init__(self, nodes=None):
        super(Numa, self).__init__()
        self.nodes = nodes

    def __repr__(self):
        return str(self.nodes)


class DeviceClass(SystemObject):

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


class Device(SystemObject):
    pass


class Locked(MappedObject):
    def __init__(self, name=None):
        super(Locked, self).__init__()
        self.name = name


class PowerType(MappedObject):

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

class Power(SystemObject):
    pass


class Serial(MappedObject):
    def __init__(self, name=None):
        super(Serial, self).__init__()
        self.name = name


class SerialType(MappedObject):
    def __init__(self, name=None):
        super(SerialType, self).__init__()
        self.name = name


class Install(MappedObject):
    def __init__(self, name=None):
        super(Install, self).__init__()
        self.name = name


def _create_tag(tag):
    """A creator function."""
    try:
        tag = DistroTag.by_tag(tag)
    except InvalidRequestError:
        tag = DistroTag(tag=tag)
        session.add(tag)
        session.flush([tag])
    return tag


class Distro(MappedObject):

    @classmethod
    def lazy_create(cls, name, osversion):
        """
        Distro is unique on name only, but osversion_id also needs to be
        supplied on insertion because it is not NULLable. So this is
        a specialisation of the usual lazy_create method.
        """
        session.begin_nested()
        try:
            item = cls(name=name, osversion=osversion)
            session.commit()
        except IntegrityError:
            session.rollback()
            item = cls.query.filter_by(name=name).one()
            item.osversion = osversion
        return item

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

    def expire(self, service='XMLRPC'):
        for tree in self.trees:
            tree.expire(service=service)

    tags = association_proxy('_tags', 'tag', creator=_create_tag)

class DistroTree(MappedObject):

    @classmethod
    def by_filter(cls, filter):
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
        return self.all_systems(user).join(System.lab_controller)\
                .filter(LabController._distro_trees.any(
                    LabControllerDistroTree.distro_tree == self))

    def all_systems(self, user=None, systems=None):
        """
        List of systems that support this distro tree.
        Will return all possible systems even if the tree is not on the lab controller yet.
        Limit to what is available to user if user passed in.
        """
        if user:
            systems = System.available_order(user, systems=systems)
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

    pass

class DistroTreeImage(MappedObject):

    pass

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

# Activity model
class Activity(MappedObject):
    def __init__(self, user=None, service=None, action=None,
                 field_name=None, old_value=None, new_value=None, **kw):
        """
        The *service* argument should be a string such as 'Scheduler' or 
        'XMLRPC', describing the means by which the change has been made. This 
        constructor will override it with something more specific (such as the 
        name of an external service) if appropriate.
        """
        super(Activity, self).__init__(**kw)
        self.user = user
        self.service = service
        try:
            self.service = identity.current.visit_link.proxied_by_user.user_name
        except (AttributeError, identity.exceptions.RequestRequiredException):
            pass # probably running in beakerd or such
        self.field_name = field_name
        self.action = action
        # These values are likely to be truncated by MySQL, so let's make sure 
        # we don't end up with invalid UTF-8 chars at the end
        if old_value and isinstance(old_value, unicode):
            old_value = unicode_truncate(old_value,
                bytes_length=object_mapper(self).c.old_value.type.length)
        if new_value and isinstance(new_value, unicode):
            new_value = unicode_truncate(new_value,
                bytes_length=object_mapper(self).c.new_value.type.length)
        self.old_value = old_value
        self.new_value = new_value

    @classmethod
    def all(cls):
        return cls.query

    def object_name(self):
        return None


class LabControllerActivity(Activity):
    def object_name(self):
        return 'LabController: %s' % self.object.fqdn


class SystemActivity(Activity):
    def object_name(self):
        return "System: %s" % self.object.fqdn

class RecipeSetActivity(Activity):
    def object_name(self):
        return "RecipeSet: %s" % self.object.id

class GroupActivity(Activity):
    def object_name(self):
        return "Group: %s" % self.object.display_name

class DistroActivity(Activity):
    def object_name(self):
        return "Distro: %s" % self.object.name

class DistroTreeActivity(Activity):
    def object_name(self):
        return u'DistroTree: %s' % self.object

class CommandActivity(Activity):
    def __init__(self, user, service, action, status, callback=None):
        Activity.__init__(self, user, service, action, u'Command', u'', u'')
        self.status = status
        self.callback = callback

    def object_name(self):
        return "Command: %s %s" % (self.object.fqdn, self.action)

    def log_to_system_history(self):
        sa = SystemActivity(self.user, self.service, self.action, u'Power', u'',
                            self.new_value and u'%s: %s' % (self.status, self.new_value) \
                            or u'%s' % self.status)
        self.system.activity.append(sa)

    def abort(self, msg=None):
        log.error('Command %s aborted: %s', (self.id, msg))
        self.status = CommandStatus.aborted
        self.new_value = msg
        self.log_to_system_history()

# note model
class Note(MappedObject):
    def __init__(self, user=None, text=None):
        super(Note, self).__init__()
        self.user = user
        self.text = text

    @classmethod
    def all(cls):
        return cls.query


class Key(SystemObject):

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
class Key_Value_String(MappedObject):

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


class Key_Value_Int(MappedObject):

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
        """
        Unlike the "real" lazy_create above, we can't rely on unique
        constraints here because 'path' and 'filename' are TEXT columns and
        MySQL can't index those. :-(

        So we just use a query-then-insert approach. There is a race window
        between querying and inserting, but it's about the best we can do.
        """
        item = cls.query.filter_by(path=cls._normalized_path(path),
                **kwargs).first()
        if item is None:
            item = cls(path=path, **kwargs)
            session.add(item)
            session.flush()
        return item

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
            return os.path.join(self.parent.logspath, self.parent.filepath, self._combined_path())

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

    def link(self):
        """ Return a link to this Log
        """
        text = '/%s' % self._combined_path()
        text = text[-50:]
        return make_link(url = self.href,
                         text = text)
    link = property(link)

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
        except KeyError, e:
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

    def is_failed(self):
        """ 
        Return True if the task has failed
        """
        if self.result in [TaskResult.warn,
                           TaskResult.fail,
                           TaskResult.panic]:
            return True
        else:
            return False

    def progress_bar(self):
        pwidth=0
        wwidth=0
        fwidth=0
        kwidth=0
        completed=0
        if not getattr(self, 'ttasks', None):
            return None
        if getattr(self, 'ptasks', None):
            completed += self.ptasks
            pwidth = int(float(self.ptasks)/float(self.ttasks)*100)
        if getattr(self, 'wtasks', None):
            completed += self.wtasks
            wwidth = int(float(self.wtasks)/float(self.ttasks)*100)
        if getattr(self, 'ftasks', None):
            completed += self.ftasks
            fwidth = int(float(self.ftasks)/float(self.ttasks)*100)
        if getattr(self, 'ktasks', None):
            completed += self.ktasks
            kwidth = int(float(self.ktasks)/float(self.ttasks)*100)
        percentCompleted = int(float(completed)/float(self.ttasks)*100)
        div   = Element('div', {'class': 'dd'})
        div.append(Element('div', {'class': 'green', 'style': 'width:%s%%' % pwidth}))
        div.append(Element('div', {'class': 'orange', 'style': 'width:%s%%' % wwidth}))
        div.append(Element('div', {'class': 'red', 'style': 'width:%s%%' % fwidth}))
        div.append(Element('div', {'class': 'blue', 'style': 'width:%s%%' % kwidth}))

        percents = Element('div', {'class': 'progressPercentage'})
        percents.text = "%s%%" % percentCompleted

        span = Element('span')
        span.append(percents)
        span.append(div)

        return span
    progress_bar = property(progress_bar)
    
    def access_rights(self,user):
        if not user:
            return
        try:
            if self.owner == user or (user.in_group(['admin','queue_admin'])):
                return True
        except Exception:
            return

    def t_id(self):
        for t, class_ in self.t_id_types.iteritems():
            if self.__class__.__name__ == class_:
                return '%s:%s' % (t, self.id)
    t_id = property(t_id)

class Job(TaskBase):
    """
    Container to hold like recipe sets.
    """

    def __init__(self, ttasks=0, owner=None, whiteboard=None,
            retention_tag=None, product=None):
        # Intentionally not chaining to super(), to avoid session.add(self)
        self.ttasks = ttasks
        self.owner = owner
        self.whiteboard = whiteboard
        self.retention_tag = retention_tag
        self.product = product

    stop_types = ['abort','cancel']
    max_by_whiteboard = 20

    @classmethod
    def mine(cls, owner):
        """
        A class method that can be used to search for Jobs that belong to a user
        """
        return cls.query.filter(Job.owner==owner)

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
                    except KeyError, e:
                        pass # Possibly already removed
        return logs_to_return

    @classmethod
    def expired_logs(cls, limit=None):
        """Return log files for expired recipes

        Will not return recipes that have already been deleted. Does
        return recipes that are marked to be deleted though.
        """
        expired_logs = []
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
            if kw.get('system_id'):
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
        product=None, include_deleted=False, include_to_delete=False, **kw):
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
        return query

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
        Method to cancel all recipesets for this job.
        """
        for recipeset in self.recipesets:
            recipeset._cancel(msg)
        self.update_status()

    def abort(self, msg=None):
        """
        Method to abort all recipesets for this job.
        """
        for recipeset in self.recipesets:
            recipeset._abort(msg)
        self.update_status()

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

    def _bubble_up(self):
        """
        Bubble Status updates up the chain.
        """
        self._update_status()

    def _bubble_down(self):
        """
        Bubble Status updates down the chain.
        """
        for child in self.recipesets:
            child._bubble_down()
        self._update_status()

    update_status = _bubble_down

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
            self.ptasks += recipeset.ptasks
            self.wtasks += recipeset.wtasks
            self.ftasks += recipeset.ftasks
            self.ktasks += recipeset.ktasks
            if recipeset.status.severity < min_status.severity:
                min_status = recipeset.status
            if recipeset.result.severity > max_result.severity:
                max_result = recipeset.result
        self._change_status(min_status)
        self.result = max_result
        if self.is_finished():
            # Send email notification
            mail.job_notify(self)

    #def t_id(self):
    #    return "J:%s" % self.id
    #t_id = property(t_id)

    @property
    def link(self):
        return make_link(url='/jobs/%s' % self.id, text=self.t_id)

    def can_admin(self, user=None):
        """Returns True iff the given user can administer this Job."""
        if user:
            return self.owner == user or user.is_admin() or self.owner.in_group([g.group_name for g in user.groups])
        return False

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
        return cls.query.filter(cls.name == name).one()

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
        return cls.query.filter_by(tag=tag).one()

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
        job_ids_type = type(job_ids)
        if job_ids_type == type(list()):
            clause = Job.id.in_(job_ids)
        elif job_ids_type == int:
            clause = Job.id == job_id
        else:
            raise BeakerException('job_ids needs to be either type \'int\' or \'list\'. Found %s' % job_ids_type)
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
        Method to cancel all recipes in this recipe set.
        """
        self._cancel(msg)
        self.update_status()

    def _cancel(self, msg=None):
        """
        Method to cancel all recipes in this recipe set.
        """ 
        self._change_status(TaskStatus.cancelled)
        for recipe in self.recipes:
            recipe._cancel(msg)

    def abort(self, msg=None):
        """
        Method to abort all recipes in this recipe set.
        """
        self._abort(msg)
        self.update_status()

    def _abort(self, msg=None):
        """
        Method to abort all recipes in this recipe set.
        """
        self._change_status(TaskStatus.aborted)
        for recipe in self.recipes:
            recipe._abort(msg)

    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        for child in self.recipes:
            child._bubble_down()
        self._update_status()
        self.job._bubble_up()

    def _bubble_up(self):
        """
        Bubble Status updates up the chain.
        """
        self._update_status()
        # we should be able to add some logic to not call job._bubble_up() if our status+result didn't change.
        self.job._bubble_up()

    def _bubble_down(self):
        """
        Bubble Status updates down the chain.
        """
        for child in self.recipes:
            child._bubble_down()
        self._update_status()

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

    @property
    def harnesspath(self):
        return get('basepath.harness', '/var/www/beaker/harness')

    @property
    def rpmspath(self):
        return get('basepath.rpms', '/var/www/beaker/rpms')

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
        return make_link(url='/recipes/%s' % self.id, text=self.t_id)

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
        logs_to_return = [os.path.dirname(log.full_path) for log in self.logs]

        for task in self.tasks:
            rt_log = task.get_log_dirs()
            if rt_log:
                logs_to_return.extend(rt_log)
        return logs_to_return

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
            recipeSet = xmldoc.createElement("recipeSet")
            recipeSet.appendChild(recipe)
            job = xmldoc.createElement("job")
            if not clone:
                job.setAttribute("owner", "%s" % self.recipeset.job.owner.email_address)
            job.appendChild(node("whiteboard", self.recipeset.job.whiteboard or ''))
            job.appendChild(recipeSet)
            return job
        return recipe

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
        if session.connection(Recipe).execute(recipe_table.update(
          and_(recipe_table.c.id==self.id,
               recipe_table.c.status==TaskStatus.processed)),
          status=TaskStatus.queued).rowcount == 1:
            self._queue()
            self.update_status()
        else:
            raise BX(_('Invalid state transition for Recipe ID %s' % self.id))

    def _queue(self):
        """
        Move from Processed -> Queued
        """
        for task in self.tasks:
            task._queue()

    def process(self):
        """
        Move from New -> Processed
        """
        if session.connection(Recipe).execute(recipe_table.update(
          and_(recipe_table.c.id==self.id,
               recipe_table.c.status==TaskStatus.new)),
          status=TaskStatus.processed).rowcount == 1:
            self._process()
            self.update_status()
        else:
            raise BX(_('Invalid state transition for Recipe ID %s' % self.id))

    def _process(self):
        """
        Move from New -> Processed
        """
        for task in self.tasks:
            task._process()

    def _link_rpms(self, dst):
        """
        Hardlink the task rpms into dst
        """
        names = os.listdir(self.rpmspath)
        makedirs_ignore(dst, 0755)
        for name in names:
            srcname = os.path.join(self.rpmspath, name)
            dstname = os.path.join(dst, name)
            if os.path.isdir(srcname):
                continue
            else:
                unlink_ignore(dstname)
                os.link(srcname, dstname)

    def createRepo(self):
        """
        Create Recipe specific task repo based on the tasks requested.
        """
        directory = os.path.join(self.repopath, str(self.id))
        try:
            os.makedirs(directory)
        except OSError:
            # This can happen when beakerd.virt_recipes() creates a repo
            # but the subsequent virt provisioning fails and the recipe
            # falls back to being queued on a regular system
            if not os.path.isdir(directory):
                #something else must have gone wrong
                raise
        # This should only run if we are missing repodata in the rpms path
        # since this should normally be updated when new tasks are uploaded
        if not os.path.isdir(os.path.join(self.rpmspath, 'repodata')):
            log.info("repodata missing, generating...")
            Task.update_repo()
        if not os.path.isdir(os.path.join(directory, 'repodata')):
            # Copy updated repo to recipe specific repo
            with Flock(self.rpmspath):
                self._link_rpms(directory)
                shutil.copytree(os.path.join(self.rpmspath, 'repodata'),
                                os.path.join(directory, 'repodata')
                               )
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
        if session.connection(Recipe).execute(recipe_table.update(
          and_(recipe_table.c.id==self.id,
               recipe_table.c.status==TaskStatus.queued)),
          status=TaskStatus.scheduled).rowcount == 1:
            self._schedule()
            self.update_status()
        else:
            raise BX(_('Invalid state transition for Recipe ID %s' % self.id))

    def _schedule(self):
        """
        Move from Processed -> Scheduled
        """
        for task in self.tasks:
            task._schedule()

    def waiting(self):
        """
        Move from Scheduled to Waiting
        """
        if session.connection(Recipe).execute(recipe_table.update(
          and_(recipe_table.c.id==self.id,
               recipe_table.c.status==TaskStatus.scheduled)),
          status=TaskStatus.waiting).rowcount == 1:
            self._waiting()
            self.update_status()
        else:
            raise BX(_('Invalid state transition for Recipe ID %s' % self.id))

    def _waiting(self):
        """
        Move from Scheduled to Waiting
        """
        for task in self.tasks:
            task._waiting()

    def cancel(self, msg=None):
        """
        Method to cancel all tasks in this recipe.
        """
        self._cancel(msg)
        self.update_status()

    def _cancel(self, msg=None):
        """
        Method to cancel all tasks in this recipe.
        """
        self._change_status(TaskStatus.cancelled)
        for task in self.tasks:
            task._cancel(msg)

    def abort(self, msg=None):
        """
        Method to abort all tasks in this recipe.
        """
        self._abort(msg)
        self.update_status()
        session.flush() # XXX bad
        if getattr(self.resource, 'system', None) and \
                get('beaker.reliable_distro_tag', None) in self.distro_tree.distro.tags:
            self.resource.system.suspicious_abort()

    def _abort(self, msg=None):
        """
        Method to abort all tasks in this recipe.
        """
        self._change_status(TaskStatus.aborted)
        for task in self.tasks:
            task._abort(msg)

    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        for child in self.tasks:
            child._bubble_down()
        self._update_status()
        self.recipeset._bubble_up()

    def _bubble_up(self):
        """
        Bubble Status updates up the chain.
        """
        self._update_status()
        # we should be able to add some logic to not call recipeset._bubble_up() if our status+result didn't change.
        self.recipeset._bubble_up()

    def _bubble_down(self):
        """
        Bubble Status updates down the chain.
        """
        for child in self.tasks:
            child._bubble_down()
        self._update_status()

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
        self._change_status(min_status)
        self.result = max_result

        # Record the start of this Recipe.
        if not self.start_time \
           and self.status == TaskStatus.running:
            self.start_time = datetime.utcnow()

        if self.start_time and not self.finish_time and self.is_finished():
            # Record the completion of this Recipe.
            self.finish_time = datetime.utcnow()
            metrics.increment('counters.recipes_%s' % self.status.name)

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
                                     callback='bkr.server.model.auto_cmd_handler')
            self.resource.system.activity.append(SystemActivity(
                    user=self.recipeset.job.owner,
                    service=u'Scheduler', action=u'Provision',
                    field_name=u'Distro Tree', old_value=u'',
                    new_value=unicode(self.distro_tree)))
        elif isinstance(self.resource, VirtResource):
            with VirtManager() as manager:
                manager.start_install(self.resource.system_name,
                        self.distro_tree, install_options.kernel_options_str,
                        self.resource.lab_controller)
            self.tasks[0].start()

    def cleanup(self):
        log.debug('Removing watchdog and cleaning up for recipe %s', self.id)
        self.destroyRepo()
        if self.resource:
            self.resource.release()
        if self.watchdog:
            session.delete(self.watchdog)

    def task_info(self):
        """
        Method for exporting Recipe status for TaskWatcher
        """
        return dict(
                    id              = "R:%s" % self.id,
                    worker          = dict(name = self.resource.fqdn),
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

    def check_virtualisability(self):
        """
        Decide whether this recipe can be run as a virt guest
        """
        # RHEL3 lacks virtio (XXX hardcoding this here is not great)
        if self.distro_tree.distro.osversion.osmajor.osmajor == \
                u'RedHatEnterpriseLinux3':
            return RecipeVirtStatus.precluded
        # Can't run VMs in a VM
        if self.guests:
            return RecipeVirtStatus.precluded
        # Multihost testing won't work (for now!)
        if len(self.recipeset.recipes) > 1:
            return RecipeVirtStatus.precluded
        return RecipeVirtStatus.possible


class GuestRecipe(Recipe):
    systemtype = 'Virtual'
    def to_xml(self, clone=False, from_recipeset=False, from_machine=False):
        recipe = xmldoc.createElement("guestrecipe")
        recipe.setAttribute("guestname", "%s" % self.guestname)
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
    result_types = ['pass_','warn','fail','panic']
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
        logs_to_return = [os.path.dirname(log.full_path) for log in self.logs]
        for result in self.results:
            rtr_log = result.get_log_dirs()
            if rtr_log:
                logs_to_return.extend(rtr_log)
        return logs_to_return

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

    def set_status(self, value):
        self._status = value


    def _bubble_up(self):
        """
        Bubble Status updates up the chain.
        """
        self._update_status()
        # we should be able to add some logic to not call recipe._bubble_up() if our status+result didn't change.
        self.recipe._bubble_up()

    update_status = _bubble_up

    def _bubble_down(self):
        """
        Bubble Status updates down the chain.
        """
        self._update_status()

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        max_result = TaskResult.min()
        for result in self.results:
            if result.result.severity > max_result.severity:
                max_result = result.result
        self.result = max_result

    def queue(self):
        """
        Moved from New -> Queued
        """
        self._queue()
        self.update_status()

    def _queue(self):
        """
        Moved from New -> Queued
        """
        self._change_status(TaskStatus.queued)

    def process(self):
        """
        Moved from Queued -> Processed
        """
        self._process()
        self.update_status()

    def _process(self):
        """
        Moved from Queued -> Processed
        """
        self._change_status(TaskStatus.processed)

    def schedule(self):
        """
        Moved from Processed -> Scheduled
        """
        self._schedule()
        self.update_status()

    def _schedule(self):
        """
        Moved from Processed -> Scheduled
        """
        self._change_status(TaskStatus.scheduled)

    def waiting(self):
        """
        Moved from Scheduled -> Waiting
        """
        self._waiting()
        self.update_status()

    def _waiting(self):
        """
        Moved from Scheduled -> Waiting
        """
        self._change_status(TaskStatus.waiting)

    def start(self, watchdog_override=None):
        """
        Record the start of this task
         If watchdog_override is defined we will use that time instead
         of what the tasks default time is.  This should be defined in number
         of seconds
        """
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
        self.update_status()
        return True

    def extend(self, kill_time):
        """
        Extend the watchdog by kill_time seconds
        """
        if not self.recipe.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.recipe.id))
        self.recipe.watchdog.kill_time = datetime.utcnow() + timedelta(
                                                              seconds=kill_time)
        return self.status_watchdog()

    def status_watchdog(self):
        """
        Return the number of seconds left on the current watchdog if it exists.
        """
        if self.recipe.watchdog:
            delta = self.recipe.watchdog.kill_time - datetime.utcnow()
            return delta.seconds + (86400 * delta.days)
        else:
            return False

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
        self.update_status()
        return True

    def owner(self):
        return self.recipe.recipeset.job.owner
    owner = property(owner)

    def cancel(self, msg=None):
        """
        Cancel this task
        """
        self._cancel(msg)
        self.update_status()

    def _cancel(self, msg=None):
        """
        Cancel this task
        """
        return self._abort_cancel(TaskStatus.cancelled, msg)

    def abort(self, msg=None):
        """
        Abort this task
        """
        self._abort(msg)
        self.update_status()
    
    def _abort(self, msg=None):
        """
        Abort this task
        """
        return self._abort_cancel(TaskStatus.aborted, msg)
    
    def _abort_cancel(self, status, msg=None):
        """
        cancel = User instigated
        abort  = Auto instigated
        """
        # Only record an abort/cancel on tasks that are New, Queued, Scheduled 
        # or Running.
        if not self.is_finished():
            if self.start_time:
                self.finish_time = datetime.utcnow()
            self._change_status(status)
            self.results.append(RecipeTaskResult(recipetask=self,
                                       path=u'/',
                                       result=TaskResult.warn,
                                       score=0,
                                       log=msg))
        return True

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

    def _result(self, result, path, score, summary):
        """
        Record a result 
        """
        if not self.recipe.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.recipe.id))
        recipeTaskResult = RecipeTaskResult(recipetask=self,
                                   path=path,
                                   result=result,
                                   score=score,
                                   log=summary)
        self.results.append(recipeTaskResult)
        # Flush the result to the DB so we can return the id.
        session.add(recipeTaskResult)
        session.flush([recipeTaskResult])
        return recipeTaskResult.id

    def task_info(self):
        """
        Method for exporting Task status for TaskWatcher
        """
        return dict(
                    id              = "T:%s" % self.id,
                    worker          = dict(name = self.recipe.resource.fqdn),
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
    def to_xml(self):
        repo = xmldoc.createElement("repo")
        repo.setAttribute("name", "%s" % self.name)
        repo.setAttribute("url", "%s" % self.url)
        return repo


class RecipeKSAppend(MappedObject):
    """
    Kickstart appends
    """
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
        return [os.path.dirname(log.full_path) for log in self.logs]

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

    def short_path(self):
        """
        Remove the parent from the begining of the path if present
        Try really hard to start path with ./
        """
        short_path = self.path
        if self.path and self.path.startswith(self.recipetask.task.name):
            short_path = self.path.replace(self.recipetask.task.name,'')
        if not short_path:
            short_path = './'
        if short_path.startswith('/'):
            short_path = '.%s' % short_path
        elif not short_path.startswith('.'):
            short_path = './%s' % short_path
        if self.path == '/' and self.log:
            short_path = self.log
        return short_path

    short_path = property(short_path)

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
                .join(RecipeResource.recipe)\
                .filter(not_(Recipe.status.in_([s for s in TaskStatus if s.finished])))
        virt_mac_query = session.query(VirtResource.mac_address.label('mac_address'))\
                .filter(VirtResource.mac_address != None)\
                .join(RecipeResource.recipe)\
                .filter(not_(Recipe.status.in_([s for s in TaskStatus if s.finished])))
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
                .order_by(left_side.c.mac_address).limit(1))
        # The type of (left_side.c.mac_address + 1) comes out as Integer
        # instead of MACAddress, I think it's a sqlalchemy bug :-(
        return netaddr.EUI(free_addr, dialect=_mac_unix)

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
        return netaddr.EUI(self.system.mac_address, dialect=_mac_unix)

    @property
    def link(self):
        return make_link(url='/view/%s' % self.system.fqdn,
                         text=self.fqdn)

    def install_options(self, distro_tree):
        return self.system.install_options(distro_tree)

    def allocate(self):
        log.debug('Reserving system %s for recipe %s', self.system, self.recipe.id)
        self.reservation = self.system.reserve(service=u'Scheduler',
                user=self.recipe.recipeset.job.owner,
                reservation_type=u'recipe')

    def release(self):
        if self.reservation.finish_time:
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
        self.lab_controller = manager.create_vm(self.system_name,
                lab_controllers, self.mac_address)

    def release(self):
        try:
            log.debug('Releasing vm %s for recipe %s',
                    self.system_name, self.recipe.id)
            with VirtManager() as manager:
                manager.destroy_vm(self.system_name)
        except Exception, e:
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

class Task(MappedObject):
    """
    Tasks that are available to schedule
    """

    @property
    def task_dir(self):
        return get("basepath.rpms", "/var/www/beaker/rpms")

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
    def update_repo(cls):
        basepath = get("basepath.rpms", "/var/www/beaker/rpms")
        with Flock(basepath):
            # Removed --baseurl, if upgrading you will need to manually
            # delete repodata directory before this will work correctly.
            subprocess.check_call(['createrepo', '-q', '--update',
                                   '--checksum', 'sha', '.'],
                                  cwd=basepath)

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


    def elapsed_time(self, suffixes=[' year',' week',' day',' hour',' minute',' second'], add_s=True, separator=', '):
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
        rpm_path = os.path.join(self.task_dir, self.rpm)
        if os.path.exists(rpm_path):
            os.unlink(rpm_path)
        self.valid=False
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

class Reservation(MappedObject): pass

class SystemStatusDuration(MappedObject): pass

class SSHPubKey(MappedObject):
    def __init__(self, keytype, pubkey, ident):
        self.keytype = keytype
        self.pubkey = pubkey
        self.ident = ident

    def __repr__(self):
        return "%s %s %s" % (self.keytype, self.pubkey, self.ident)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

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

class ConfigItem(MappedObject):
    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name=name).one()

    @classmethod
    def list_by_name(cls, name, find_anywhere=False):
        if find_anywhere:
            q = cls.query.filter(ConfigItem.name.like('%%%s%%' % name))
        else:
            q = cls.query.filter(ConfigItem.name.like('%s%%' % name))
        return q

    def _value_class(self):
        if self.numeric:
            return ConfigValueInt
        else:
            return ConfigValueString
    value_class = property(_value_class)

    def values(self):
        return self.value_class.query.filter(self.value_class.config_item_id == self.id)

    def current_value(self, default=None):
        v = self.values().\
            filter(and_(self.value_class.valid_from <= datetime.utcnow(), self.value_class.config_item_id == self.id)).\
            order_by(self.value_class.valid_from.desc()).first()
        if v:
            return v.value
        else:
            return default

    def next_value(self):
        return self.values().filter(self.value_class.valid_from > datetime.utcnow()).\
                order_by(self.value_class.valid_from.asc()).first()

    def set(self, value, valid_from=None, user=None):
        if user is None:
            try:
                user = identity.current.user
            except AttributeError, e:
                raise BX(_('Settings may not be changed anonymously'))
        if valid_from:
            if valid_from < datetime.utcnow():
                raise BX(_('%s is in the past') % valid_from)
        self.value_class(self, value, user, valid_from)

class ConfigValueString(MappedObject):
    def __init__(self, config_item, value, user, valid_from=None):
        super(ConfigValueString, self).__init__()
        self.config_item = config_item
        self.value = value
        self.user = user
        if valid_from:
            self.valid_from = valid_from

class ConfigValueInt(MappedObject):
    def __init__(self, config_item, value, user, valid_from=None):
        super(ConfigValueInt, self).__init__()
        self.config_item = config_item
        self.value = value
        self.user = user
        if valid_from:
            self.valid_from = valid_from

class VirtManager(object):

    def __init__(self):
        self.api = None

    def __enter__(self):
        self.api = ovirtsdk.api.API(url=get('ovirt.api_url'),
                username=get('ovirt.username'), password=get('ovirt.password'),
                # XXX add some means to specify SSL CA cert
                insecure=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.api, api = None, self.api
        api.disconnect()

    def create_vm(self, name, lab_controllers, mac_address):
        if self.api is None:
            raise RuntimeError('Context manager was not entered')
        from ovirtsdk.xml.params import VM, Template, NIC, Network, Disk, \
                StorageDomains, MAC
        # Default of 1GB memory and 20GB disk
        memory = ConfigItem.by_name('default_guest_memory').current_value(1024) * 1024**2
        disk_size = ConfigItem.by_name('default_guest_disk_size').current_value(20) * 1024**3
        # Try to create the VM on every cluster that is in an acceptable data center
        cluster_query = ' or '.join('datacenter.name=%s' % lc.data_center_name
                for lc in lab_controllers)
        for cluster in self.api.clusters.list(cluster_query):
            log.debug('Trying to create vm %s on cluster %s', name, cluster.name)
            vm = None
            try:
                vm_definition = VM(name=name, memory=memory, cluster=cluster,
                        type_='virtio26', template=Template(name='Blank'))
                vm = self.api.vms.add(vm_definition)
                nic = NIC(name='eth0', interface='virtio', network=Network(name='rhevm'),
                        mac=MAC(address=str(mac_address)))
                vm.nics.add(nic)
                sd_query = ' or '.join('datacenter=%s' % lc.data_center_name
                        for lc in lab_controllers)
                storage_domain_name = get('ovirt.storage_domain')
                if storage_domain_name:
                    storage_domains = [self.api.storagedomains.get(storage_domain_name)]
                else:
                    storage_domains = self.api.storagedomains.list(sd_query)
                disk = Disk(storage_domains=StorageDomains(storage_domain=storage_domains),
                        size=disk_size, type_='data', interface='virtio', format='cow',
                        bootable=True)
                vm.disks.add(disk)

                # Wait up to twenty seconds(!) for the disk image to be created
                for _ in range(20):
                    if self.api.vms.get(name).status.state != 'image_locked':
                        break
                    time.sleep(1)
                state = self.api.vms.get(name).status.state
                if state == 'image_locked':
                    raise ValueError('VM %s state %s', name, state)

                dc_name = self.api.datacenters.get(id=cluster.data_center.id).name
                return LabController.by_data_center_name(dc_name)
            except Exception:
                log.exception("Failed to create VM %r on %r cluster %r",
                        name, self, cluster.name)
                if vm is not None:
                    try:
                        vm.delete()
                    except Exception:
                        pass
                continue
        raise VMCreationFailedException('No clusters successfully created VM %s' % name)

    def start_install(self, name, distro_tree, kernel_options, lab_controller):
        if self.api is None:
            raise RuntimeError('Context manager was not entered')
        from ovirtsdk.xml.params import OperatingSystem, Action, VM
        # RHEV can only handle a local path to kernel/initrd, so we rely on autofs for now :-(
        # XXX when this constraint is lifted, fix beakerd.virt_recipes too
        location = distro_tree.url_in_lab(lab_controller, 'nfs', required=True)
        kernel = distro_tree.image_by_type(ImageType.kernel, KernelType.by_name(u'default'))
        initrd = distro_tree.image_by_type(ImageType.initrd, KernelType.by_name(u'default'))
        local_path = location.replace('nfs://', '/net/', 1).replace(':/', '/', 1)
        kernel_path = os.path.join(local_path, kernel.path)
        initrd_path = os.path.join(local_path, initrd.path)
        log.debug(u'Starting VM %s installing %s', name, distro_tree)
        a = Action(vm=VM(os=OperatingSystem(kernel=kernel_path,
                initrd=initrd_path, cmdline=kernel_options)))
        self.api.vms.get(name).start(action=a)

    def destroy_vm(self, name):
        from ovirtsdk.infrastructure.errors import RequestError
        if self.api is None:
            raise RuntimeError('Context manager was not entered')
        vm = self.api.vms.get(name)
        if vm is not None:
            try:
                log.debug('Stopping %s on %r', name, self)
                vm.stop()
            except RequestError:
                pass # probably not running for some reason
            log.debug('Deleting %s on %r', name, self)
            vm.delete()

# set up mappers between identity tables and classes
Hypervisor.mapper = mapper(Hypervisor, hypervisor_table)
KernelType.mapper = mapper(KernelType, kernel_type_table)
System.mapper = mapper(System, system_table,
                   properties = {
                     'status': column_property(system_table.c.status,
                        extension=SystemStatusAttributeExtension()),
                     'devices':relation(Device,
                                        secondary=system_device_map,backref='systems'),
                     'arch':relation(Arch,
                                     order_by=[arch_table.c.arch],
                                        secondary=system_arch_map,
                                        backref='systems'),
                     'labinfo':relation(LabInfo, uselist=False, backref='system',
                        cascade='all, delete, delete-orphan'),
                     'cpu':relation(Cpu, uselist=False,backref='systems',
                        cascade='all, delete, delete-orphan'),
                     'numa':relation(Numa, uselist=False, backref='system',
                        cascade='all, delete, delete-orphan'),
                     'power':relation(Power, uselist=False, backref='system',
                        cascade='all, delete, delete-orphan'),
                     'excluded_osmajor':relation(ExcludeOSMajor, backref='system',
                        cascade='all, delete, delete-orphan'),
                     'excluded_osversion':relation(ExcludeOSVersion, backref='system',
                        cascade='all, delete, delete-orphan'),
                     'provisions':relation(Provision, collection_class=attribute_mapped_collection('arch'),
                                                 backref='system', cascade='all, delete, delete-orphan'),
                     'loaned':relation(User, uselist=False,
                          primaryjoin=system_table.c.loan_id==users_table.c.user_id,foreign_keys=system_table.c.loan_id),
                     'user':relation(User, uselist=False,
                          primaryjoin=system_table.c.user_id==users_table.c.user_id,foreign_keys=system_table.c.user_id),
                     'owner':relation(User, uselist=False,
                          primaryjoin=system_table.c.owner_id==users_table.c.user_id,foreign_keys=system_table.c.owner_id),
                     'lab_controller':relation(LabController, uselist=False,
                                               backref='systems'),
                     'notes':relation(Note,
                                      order_by=[note_table.c.created.desc()],
                                      cascade="all, delete, delete-orphan"),
                     'key_values_int':relation(Key_Value_Int,
                                      cascade="all, delete, delete-orphan",
                                                backref='system'),
                     'key_values_string':relation(Key_Value_String,
                                      cascade="all, delete, delete-orphan",
                                                backref='system'),
                     'activity':relation(SystemActivity,
                        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                        backref='object', cascade='all, delete'),
                     'dyn_activity': dynamic_loader(SystemActivity,
                        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()]),
                     'command_queue':relation(CommandActivity,
                        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                        backref='object', cascade='all, delete, delete-orphan'),
                     'dyn_command_queue': dynamic_loader(CommandActivity),
                     'reprovision_distro_tree':relation(DistroTree, uselist=False),
                      '_system_ccs': relation(SystemCc, backref='system',
                                      cascade="all, delete, delete-orphan"),
                     'reservations': relation(Reservation, backref='system',
                        order_by=[reservation_table.c.start_time.desc()]),
                     'dyn_reservations': dynamic_loader(Reservation),
                     'open_reservation': relation(Reservation, uselist=False, viewonly=True,
                        primaryjoin=and_(system_table.c.id == reservation_table.c.system_id,
                            reservation_table.c.finish_time == None)),
                     'status_durations': relation(SystemStatusDuration, backref='system',
                        cascade='all, delete, delete-orphan',
                        order_by=[system_status_duration_table.c.start_time.desc(),
                                  system_status_duration_table.c.id.desc()]),
                     'dyn_status_durations': dynamic_loader(SystemStatusDuration),
                     'hypervisor':relation(Hypervisor, uselist=False),
                     'kernel_type':relation(KernelType, uselist=False),
                     # The relationship to 'recipe' is complicated
                     # by the polymorphism of SystemResource :-(
                     'recipes': relation(Recipe, viewonly=True,
                        secondary=recipe_resource_table.join(system_resource_table),
                        secondaryjoin=and_(system_resource_table.c.id == recipe_resource_table.c.id,
                            recipe_resource_table.c.recipe_id == recipe_table.c.id)),
                     'dyn_recipes': dynamic_loader(Recipe,
                        secondary=recipe_resource_table.join(system_resource_table),
                        secondaryjoin=and_(system_resource_table.c.id == recipe_resource_table.c.id,
                            recipe_resource_table.c.recipe_id == recipe_table.c.id)),
                     })

mapper(SystemCc, system_cc_table)
mapper(SystemStatusDuration, system_status_duration_table)

Cpu.mapper = mapper(Cpu, cpu_table, properties={
    'flags': relation(CpuFlag, cascade='all, delete, delete-orphan'),
    'system': relation(System),
})
mapper(Arch, arch_table)
mapper(Provision, provision_table,
       properties = {'provision_families':relation(ProvisionFamily,
            collection_class=attribute_mapped_collection('osmajor'),
            cascade='all, delete, delete-orphan'),
                     'arch':relation(Arch)})
mapper(ProvisionFamily, provision_family_table,
       properties = {'provision_family_updates':relation(ProvisionFamilyUpdate,
            collection_class=attribute_mapped_collection('osversion'),
            cascade='all, delete, delete-orphan'),
                     'osmajor':relation(OSMajor)})
mapper(ProvisionFamilyUpdate, provision_family_update_table,
       properties = {'osversion':relation(OSVersion)})
mapper(ExcludeOSMajor, exclude_osmajor_table,
       properties = {'osmajor':relation(OSMajor, backref='excluded_osmajors'),
                     'arch':relation(Arch)})
mapper(ExcludeOSVersion, exclude_osversion_table,
       properties = {'osversion':relation(OSVersion, backref='excluded_osversions'),
                     'arch':relation(Arch)})
mapper(OSVersion, osversion_table,
       properties = {'osmajor':relation(OSMajor, uselist=False,
                                        backref='osversion'),
                     'arches':relation(Arch,secondary=osversion_arch_map),
                    }
      )
mapper(OSMajor, osmajor_table,
       properties = {'osminor':relation(OSVersion,
                                     order_by=[osversion_table.c.osminor])})
mapper(LabInfo, labinfo_table)
mapper(Watchdog, watchdog_table,
       properties = {'recipetask':relation(RecipeTask, uselist=False),
                     'recipe':relation(Recipe, uselist=False,
                                      )})
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

mapper(LabControllerDistroTree, distro_tree_lab_controller_map)
mapper(LabController, lab_controller_table,
        properties = {'_distro_trees': relation(LabControllerDistroTree,
                        backref='lab_controller', cascade='all, delete-orphan'),
                      'dyn_systems' : dynamic_loader(System),
                      'user'        : relation(User, uselist=False),
                      'write_activity': relation(LabControllerActivity, lazy='noload'),
                      'activity' : relation(LabControllerActivity,
                                            order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                                            cascade='all, delete',
                                            backref='object'),
                     }
      )
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

mapper(Visit, visits_table)

mapper(VisitIdentity, visit_identity_table, properties={
    'user': relation(User,
        primaryjoin=visit_identity_table.c.user_id == users_table.c.user_id,
        backref='visit_identity'),
    'proxied_by_user': relation(User,
        primaryjoin=visit_identity_table.c.proxied_by_user_id == users_table.c.user_id),
})

mapper(User, users_table,
        properties={
      '_password' : users_table.c.password,
      '_root_password' : users_table.c.root_password,
      'lab_controller' : relation(LabController, uselist=False),
})

mapper(Group, groups_table,
    properties=dict(users=relation(User, uselist=True, secondary=user_group_table, backref='groups'),
    ))

mapper(SystemGroup, system_group_table, properties={
    'system': relation(System, backref=backref('group_assocs', cascade='all, delete-orphan')),
    'group': relation(Group, backref=backref('system_assocs', cascade='all, delete-orphan')),
})

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))

mapper(BeakerTag, beaker_tag_table,
        polymorphic_on=beaker_tag_table.c.type, polymorphic_identity=u'tag')

mapper(RetentionTag, retention_tag_table, inherits=BeakerTag, 
        properties=dict(is_default=retention_tag_table.c.default_),
        polymorphic_identity=u'retention_tag')

mapper(Activity, activity_table,
        polymorphic_on=activity_table.c.type, polymorphic_identity=u'activity',
        properties=dict(user=relation(User, uselist=False,
                        backref='activity')))

mapper(SystemActivity, system_activity_table, inherits=Activity,
        polymorphic_identity=u'system_activity')

mapper(RecipeSetActivity, recipeset_activity_table, inherits=Activity,
       polymorphic_identity=u'recipeset_activity')

mapper(GroupActivity, group_activity_table, inherits=Activity,
        polymorphic_identity=u'group_activity',
        properties=dict(object=relation(Group, uselist=False,
                        backref=backref('activity', cascade='all, delete-orphan'))))

mapper(DistroActivity, distro_activity_table, inherits=Activity,
       polymorphic_identity=u'distro_activity')

mapper(DistroTreeActivity, distro_tree_activity_table, inherits=Activity,
       polymorphic_identity=u'distro_tree_activity')

mapper(CommandActivity, command_queue_table, inherits=Activity,
       polymorphic_identity=u'command_activity',
       properties={'status': column_property(command_queue_table.c.status,
                        extension=CallbackAttributeExtension()),
                   'system':relation(System),
                   'distro_tree': relation(DistroTree),
                  })

mapper(LabControllerActivity, lab_controller_activity_table, inherits=Activity,
    polymorphic_identity=u'lab_controller_activity')

mapper(Note, note_table,
        properties=dict(user=relation(User, uselist=False,
                        backref='notes')))

Key.mapper = mapper(Key, key_table)
           
mapper(Key_Value_Int, key_value_int_table, properties={
        'key': relation(Key, uselist=False,
            backref=backref('key_value_int', cascade='all, delete-orphan'))
        })
mapper(Key_Value_String, key_value_string_table, properties={
        'key': relation(Key, uselist=False,
            backref=backref('key_value_string', cascade='all, delete-orphan'))
        })

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

mapper(Job, job_table,
        properties = {'recipesets':relation(RecipeSet, backref='job'),
                      'owner':relation(User, uselist=False,
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
        properties = {'guests':relation(Recipe, backref='hostmachine',
                                        secondary=machine_guest_map)})

mapper(RecipeResource, recipe_resource_table,
        polymorphic_on=recipe_resource_table.c.type, polymorphic_identity=None)
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
mapper(Reservation, reservation_table, properties={
        'user': relation(User, backref=backref('reservations',
            order_by=[reservation_table.c.start_time.desc()])),
        # The relationship to 'recipe' is complicated
        # by the polymorphism of SystemResource :-(
        'recipe': relation(Recipe, uselist=False, viewonly=True,
            secondary=recipe_resource_table.join(system_resource_table),
            secondaryjoin=and_(system_resource_table.c.id == recipe_resource_table.c.id,
                recipe_resource_table.c.recipe_id == recipe_table.c.id)),
})
mapper(SSHPubKey, sshpubkey_table,
        properties=dict(user=relation(User, uselist=False, backref='sshpubkeys')))
mapper(ConfigItem, config_item_table)
mapper(ConfigValueInt, config_value_int_table,
       properties = {'config_item': relation(ConfigItem, uselist=False),
                     'user': relation(User)}
      )
mapper(ConfigValueString, config_value_string_table,
       properties = {'config_item': relation(ConfigItem, uselist=False),
                     'user': relation(User)}
      )


## Static list of device_classes -- used by master.kid
global _device_classes
_device_classes = None
def device_classes():
    global _device_classes
    if not _device_classes:
        _device_classes = DeviceClass.query.all()
    for device_class in _device_classes:
        yield device_class

# available in python 2.7+ importlib
def import_module(modname):
     __import__(modname)
     return sys.modules[modname]

def auto_cmd_handler(command, new_status):
    if not command.system.open_reservation:
        return
    recipe = command.system.open_reservation.recipe
    if new_status in (CommandStatus.failed, CommandStatus.aborted):
        recipe.abort("Command %s failed" % command.id)
    elif command.action == u'reboot':
        recipe.tasks[0].start()
