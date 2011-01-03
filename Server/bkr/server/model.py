import sys 

import re
from turbogears.database import metadata, mapper, session
from turbogears.config import get
from turbogears import url
import ldap
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint,
                        String, Unicode, Integer, DateTime,
                        UnicodeText, Boolean, Float, VARCHAR, TEXT, Numeric, 
                        or_, and_, not_, select, case, func)

from sqlalchemy.orm import relation, backref, synonym, dynamic_loader,query 
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import join
from sqlalchemy.exceptions import InvalidRequestError
from identity import LdapSqlAlchemyIdentityProvider
from cobbler_utils import consolidate, string_to_hash
from sqlalchemy.orm.collections import attribute_mapped_collection, MappedCollection, collection
from sqlalchemy.util import OrderedDict
from sqlalchemy.ext.associationproxy import association_proxy
import socket
from xmlrpclib import ProtocolError
import time
from kid import Element
from bkr.server.bexceptions import BeakerException, BX, CobblerTaskFailedException
from bkr.server.helpers import *
from bkr.server.util import unicode_truncate
from bkr.server import mail
import traceback
from BasicAuthTransport import BasicAuthTransport
import xmlrpclib
import errno
import bkr.timeout_xmlrpclib
import os
import shutil
import urllib

from turbogears import identity

from datetime import timedelta, date, datetime

import md5

import xml.dom.minidom
from xml.dom.minidom import Node, parseString

import logging
log = logging.getLogger(__name__)

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
           ForeignKey('tg_user.user_id')),
    Column('user_id', Integer,
           ForeignKey('tg_user.user_id')),
    Column('type_id', Integer,
           ForeignKey('system_type.id'), nullable=False),
    Column('status_id', Integer,
           ForeignKey('system_status.id'), nullable=False),
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
    Column('release_action_id', Integer,
           ForeignKey('release_action.id')),
    Column('reprovision_distro_id', Integer,
           ForeignKey('distro.id')),
)

system_cc_table = Table('system_cc', metadata,
        Column('system_id', Integer, ForeignKey('system.id', ondelete='CASCADE',
            onupdate='CASCADE'), primary_key=True),
        Column('email_address', Unicode(255), primary_key=True, index=True),
)

system_device_map = Table('system_device_map', metadata,
    Column('system_id', Integer,
           ForeignKey('system.id'),
           primary_key=True),
    Column('device_id', Integer,
           ForeignKey('device.id'),
           primary_key=True),
)

system_type_table = Table('system_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('type', Unicode(100), nullable=False),
)

release_action_table = Table('release_action', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('action', Unicode(100), nullable=False),
)

system_status_table = Table('system_status', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('status', Unicode(100), nullable=False),
)

arch_table = Table('arch', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('arch', String(20), unique=True)
)

system_arch_map = Table('system_arch_map', metadata,
    Column('system_id', Integer,
           ForeignKey('system.id'),
           primary_key=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True),
)

osversion_arch_map = Table('osversion_arch_map', metadata,
    Column('osversion_id', Integer,
           ForeignKey('osversion.id'),
           primary_key=True),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           primary_key=True),
)

provision_table = Table('provision', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
    Column('arch_id', Integer, ForeignKey('arch.id')),
)

provision_family_table = Table('provision_family', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('provision_id', Integer, ForeignKey('provision.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
)

provision_family_update_table = Table('provision_update_family', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('provision_family_id', Integer, ForeignKey('provision_family.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
    Column('ks_meta', String(1024)),
    Column('kernel_options', String(1024)),
    Column('kernel_options_post', String(1024)),
)

exclude_osmajor_table = Table('exclude_osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
)

exclude_osversion_table = Table('exclude_osversion', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
)

task_exclude_arch_table = Table('task_exclude_arch', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('task_id', Integer, ForeignKey('task.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
)

task_exclude_osmajor_table = Table('task_exclude_osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('task_id', Integer, ForeignKey('task.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
)

labinfo_table = Table('labinfo', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('orig_cost', Numeric(precision=16,length=2,asdecimal=True)),
    Column('curr_cost', Numeric(precision=16,length=2,asdecimal=True)),
    Column('dimensions', String(255)),
    Column('weight', Numeric(asdecimal=False)),
    Column('wattage', Numeric(asdecimal=False)),
    Column('cooling', Numeric(asdecimal=False)),
)

watchdog_table = Table('watchdog', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), nullable=False),
    Column('recipe_id', Integer, ForeignKey('recipe.id')),
    Column('recipetask_id', Integer, ForeignKey('recipe_task.id')),
    Column('subtask', Unicode(255)),
    Column('kill_time', DateTime),
)

cpu_table = Table('cpu', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
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
)

cpu_flag_table = Table('cpu_flag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('cpu_id', Integer, ForeignKey('cpu.id')),
    Column('flag', String(10))
)

numa_table = Table('numa', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('nodes',Integer),
)

device_class_table = Table('device_class', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column("device_class", VARCHAR(24)),
    Column("description", TEXT)
)

device_table = Table('device', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('vendor_id',String(255)),
    Column('device_id',String(255)),
    Column('subsys_device_id',String(255)),
    Column('subsys_vendor_id',String(255)),
    Column('bus',String(255)),
    Column('driver',String(255)),
    Column('description',String(255)),
    Column('device_class_id', Integer,
           ForeignKey('device_class.id'), nullable=False),
    Column('date_added', DateTime, 
           default=datetime.utcnow, nullable=False)
)

locked_table = Table('locked', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

power_type_table = Table('power_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('name', String(255), nullable=False),
)

power_table = Table('power', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('power_type_id', Integer, ForeignKey('power_type.id'),
           nullable=False),
    Column('system_id', Integer, ForeignKey('system.id')),
    Column('power_address', String(255), nullable=False),
    Column('power_user', String(255)),
    Column('power_passwd', String(255)),
    Column('power_id', String(255)),
)

serial_table = Table('serial', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

serial_type_table = Table('serial_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

install_table = Table('install', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
)

#RHEL4-U8-re20081015.nightly_http-AS-x86_64   	redhat 	x86_64
#RHEL4-U8-re20081015.nightly_http-AS-x86_64   	redhat 	x86_64
#RHEL4-U8-re20081015.nightly_nfs-AS-xen-x86_64 	redhat 	x86_64
#RHEL4-U8-re20081015.nightly_nfs-AS-xen-x86_64 	redhat 	x86_64
#RHEL5.3-Client-20081013.nightly_http-i386 	redhat 	i386
#RHEL5.3-Client-20081013.nightly_http-x86_64 	redhat 	x86_64
#RHEL5.3-Client-20081013.nightly_nfs-i386 	redhat 	i386
#RHEL5.3-Client-20081013.nightly_nfs-x86_64 	redhat 	x86_64

distro_table = Table('distro', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('install_name',Unicode(255), unique=True, nullable=False),
    Column('name',Unicode(255)),
    Column('breed_id', Integer, ForeignKey('breed.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('variant',Unicode(25)),
    Column('method',Unicode(25)),
    Column('virt',Boolean),
    Column('date_created',DateTime),
)

lab_controller_distro_map = Table('distro_lab_controller_map', metadata,
    Column('distro_id', Integer, ForeignKey('distro.id'), primary_key=True),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id'), primary_key=True),
    Column('tree_path', String(1024)),
)

lab_controller_table = Table('lab_controller', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn',Unicode(255), unique=True),
    Column('username',Unicode(255)),
    Column('password',Unicode(255)),
    Column('distros_md5', String(40)),
    Column('systems_md5', String(40)),
)

osmajor_table = Table('osmajor', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor', Unicode(255), unique=True),
    Column('alias', Unicode(25), unique=True),
)

osversion_table = Table('osversion', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    Column('osminor',Unicode(255)),
)

breed_table = Table('breed', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('breed',Unicode(255), unique=True),
)

distro_tag_table = Table('distro_tag', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('tag', Unicode(255), unique=True),
)

distro_tag_map = Table('distro_tag_map', metadata,
    Column('distro_id', Integer, ForeignKey('distro.id'), 
                                         primary_key=True),
    Column('distro_tag_id', Integer, ForeignKey('distro_tag.id'), 
                                         primary_key=True),
)

# the identity schema

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    Column('expiry', DateTime)
)


visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True)
)

groups_table = Table('tg_group', metadata,
    Column('group_id', Integer, primary_key=True),
    Column('group_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.utcnow)
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(255), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(40)),
    Column('created', DateTime, default=datetime.utcnow)
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255))
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

system_group_table = Table('system_group', metadata,
    Column('system_id', Integer, ForeignKey('system.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

system_admin_map_table = Table('system_admin_map', metadata, 
    Column('system_id', Integer, ForeignKey('system.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

recipe_set_nacked_table = Table('recipe_set_nacked', metadata,
    Column('recipe_set_id', Integer, ForeignKey('recipe_set.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True,nullable=False), 
    Column('response_id', Integer, ForeignKey('response.id', 
        onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('comment', Unicode(255),nullable=True),
    Column('created',DateTime,nullable=False,default=datetime.utcnow)
)

beaker_tag_table = Table('beaker_tag', metadata,
    Column('id', Integer, primary_key=True, nullable = False),
    Column('tag', Unicode(20), primary_key=True, nullable = False),
    Column('type', Unicode(40), nullable=False)
)

retention_tag_table = Table('retention_tag', metadata,
    Column('id', Integer, ForeignKey('beaker_tag.id', onupdate='CASCADE', ondelete='CASCADE'),nullable=False, primary_key=True),
    Column('default_', Boolean),
    Column('needs_product', Boolean)
)

product_table = Table('product', metadata,
    Column('id', Integer, autoincrement=True, nullable=False,
        primary_key=True),
    Column('name', Unicode(100),unique=True, index=True, nullable=False),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
)

response_table = Table('response', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True, nullable=False),
    Column('response',Unicode(50), nullable=False)
)


group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

# activity schema

# TODO This will require some indexes for performance.
activity_table = Table('activity', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    Column('type', Unicode(40), nullable=False),
    Column('field_name', Unicode(40), nullable=False),
    Column('service', Unicode(100), nullable=False),
    Column('action', Unicode(40), nullable=False),
    Column('old_value', Unicode(60)),
    Column('new_value', Unicode(60))
)

system_activity_table = Table('system_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'))
)

recipeset_activity_table = Table('recipeset_activity', metadata,
    Column('id', Integer,ForeignKey('activity.id'), primary_key=True),
    Column('recipeset_id', Integer, ForeignKey('recipe_set.id'))
)

group_activity_table = Table('group_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id'))
)

distro_activity_table = Table('distro_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('distro_id', Integer, ForeignKey('distro.id'))
)

# note schema
note_table = Table('note', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), index=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    Column('text',TEXT, nullable=False)
)

key_table = Table('key_', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('key_name', String(50), nullable=False, unique=True),
    Column('numeric', Boolean, default=False),
)

key_value_string_table = Table('key_value_string', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
            onupdate='CASCADE', ondelete='CASCADE'), index=True),
    Column('key_id', Integer, ForeignKey('key_.id',
            onupdate='CASCADE', ondelete='CASCADE'), index=True),
    Column('key_value',TEXT, nullable=False)
)

key_value_int_table = Table('key_value_int', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id',
            onupdate='CASCADE', ondelete='CASCADE'), index=True),
    Column('key_id', Integer, ForeignKey('key_.id',
            onupdate='CASCADE', ondelete='CASCADE'), index=True),
    Column('key_value',Integer, nullable=False)
)

task_status_table = Table('task_status',metadata,
        Column('id', Integer, primary_key=True),
        Column('status', Unicode(20)),
        Column('severity', Integer)
)

task_result_table = Table('task_result',metadata,
        Column('id', Integer, primary_key=True),
        Column('result', Unicode(20)),
        Column('severity', Integer)
)

task_priority_table = Table('task_priority',metadata,
        Column('id', Integer, primary_key=True),
        Column('priority', Unicode(20))
)

job_table = Table('job',metadata,
        Column('id', Integer, primary_key=True),
        Column('owner_id', Integer,
                ForeignKey('tg_user.user_id'), index=True),
        Column('whiteboard',Unicode(2000)),
        Column('retention_tag_id', Integer, ForeignKey('retention_tag.id'), nullable=False),
        Column('product_id', Integer, ForeignKey('product.id'),nullable=True),
        Column('result_id', Integer,
                ForeignKey('task_result.id')),
        Column('status_id', Integer,
                ForeignKey('task_status.id'), default=select([task_status_table.c.id], limit=1).where(task_status_table.c.status==u'New').correlate(None)),
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
)

job_cc_table = Table('job_cc', metadata,
        Column('job_id', Integer, ForeignKey('job.id', ondelete='CASCADE',
            onupdate='CASCADE'), primary_key=True),
        Column('email_address', Unicode(255), primary_key=True, index=True),
)

recipe_set_table = Table('recipe_set',metadata,
        Column('id', Integer, primary_key=True),
        Column('job_id', Integer,
                ForeignKey('job.id')),
        Column('priority_id', Integer,
                ForeignKey('task_priority.id'), default=select([task_priority_table.c.id], limit=1).where(task_priority_table.c.priority==u'Normal').correlate(None)),
        Column('queue_time',DateTime, nullable=False, default=datetime.utcnow),
        Column('delete_time', DateTime, nullable=True),
        Column('result_id', Integer,
                ForeignKey('task_result.id')),
        Column('status_id', Integer,
                ForeignKey('task_status.id'), default=select([task_status_table.c.id], limit=1).where(task_status_table.c.status==u'New').correlate(None)),
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
)

log_recipe_table = Table('log_recipe', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id')),
        Column('path', UnicodeText()),
        Column('filename', UnicodeText(), nullable=False),
        Column('start_time',DateTime, default=datetime.utcnow),
	Column('server', UnicodeText()),
	Column('basepath', UnicodeText()),
)

log_recipe_task_table = Table('log_recipe_task', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('path', UnicodeText()),
        Column('filename', UnicodeText(), nullable=False),
        Column('start_time',DateTime, default=datetime.utcnow),
	Column('server', UnicodeText()),
	Column('basepath', UnicodeText()),
)

log_recipe_task_result_table = Table('log_recipe_task_result', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_result_id', Integer,
                ForeignKey('recipe_task_result.id')),
        Column('path', UnicodeText()),
        Column('filename', UnicodeText(), nullable=False),
        Column('start_time',DateTime, default=datetime.utcnow),
	Column('server', UnicodeText()),
	Column('basepath', UnicodeText()),
)

recipe_table = Table('recipe',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_set_id', Integer,
                ForeignKey('recipe_set.id')),
        Column('distro_id', Integer,
                ForeignKey('distro.id')),
        Column('system_id', Integer,
                ForeignKey('system.id')),
        Column('result_id', Integer,
                ForeignKey('task_result.id')),
        Column('status_id', Integer,
                ForeignKey('task_status.id'),default=select([task_status_table.c.id], limit=1).where(task_status_table.c.status==u'New').correlate(None)),
        Column('start_time',DateTime),
        Column('finish_time',DateTime),
        Column('_host_requires',UnicodeText()),
        Column('_distro_requires',UnicodeText()),
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
)

machine_recipe_table = Table('machine_recipe', metadata,
        Column('id', Integer, ForeignKey('recipe.id'), primary_key=True)
)

guest_recipe_table = Table('guest_recipe', metadata,
        Column('id', Integer, ForeignKey('recipe.id'), primary_key=True),
        Column('guestname', UnicodeText()),
        Column('guestargs', UnicodeText())
)

machine_guest_map =Table('machine_guest_map',metadata,
        Column('machine_recipe_id', Integer,
                ForeignKey('machine_recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('guest_recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
)

system_recipe_map = Table('system_recipe_map', metadata,
        Column('system_id', Integer,
                ForeignKey('system.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True),
)

recipe_tag_table = Table('recipe_tag',metadata,
        Column('id', Integer, primary_key=True),
        Column('tag', Unicode(255))
)

recipe_tag_map = Table('recipe_tag_map', metadata,
        Column('tag_id', Integer,
               ForeignKey('recipe_tag.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('recipe_id', Integer, 
               ForeignKey('recipe.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
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
        Column('running_kernel', Boolean)
)

recipe_repo_table =Table('recipe_repo',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id'), nullable=False),
        Column('name',Unicode(255)),
        Column('url',Unicode(1024))
)

recipe_ksappend_table = Table('recipe_ksappend', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id'), nullable=False),
        Column('ks_append',UnicodeText()),
)

recipe_task_table =Table('recipe_task',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer, ForeignKey('recipe.id'), nullable=False),
        Column('task_id', Integer, ForeignKey('task.id'), nullable=False),
        Column('start_time',DateTime),
        Column('finish_time',DateTime),
        Column('result_id', Integer,
                ForeignKey('task_result.id')),
        Column('status_id', Integer,
                ForeignKey('task_status.id'),default=select([task_status_table.c.id], limit=1).where(task_status_table.c.status==u'New').correlate(None)),
        Column('role', Unicode(255)),
)

recipe_role_table = Table('recipe_role', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id')),
        Column('role',Unicode(255)),
        Column('system_id', Integer,
                ForeignKey('system.id')),
)

recipe_task_role_table = Table('recipe_task_role', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('role',Unicode(255)),
        Column('system_id', Integer,
                ForeignKey('system.id')),
)
        
recipe_task_param_table = Table('recipe_task_param', metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('name',Unicode(255)),
        Column('value',UnicodeText())
)

recipe_task_comment_table = Table('recipe_task_comment',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('comment', UnicodeText()),
        Column('created', DateTime),
        Column('user_id', Integer,
                ForeignKey('tg_user.user_id'), index=True)
)

recipe_task_bugzilla_table = Table('recipe_task_bugzilla',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('bugzilla_id', Integer)
)

recipe_task_rpm_table =Table('recipe_task_rpm',metadata,
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id'), primary_key=True),
        Column('package',Unicode(255)),
        Column('version',Unicode(255)),
        Column('release',Unicode(255)),
        Column('epoch',Integer),
        Column('arch',Unicode(255)),
        Column('running_kernel', Boolean)
)

recipe_task_result_table = Table('recipe_task_result',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('path', Unicode(2048)),
        Column('result_id', Integer,
                ForeignKey('task_result.id')),
        Column('score', Numeric(10)),
        Column('log', UnicodeText()),
        Column('start_time',DateTime, default=datetime.utcnow),
)

task_table = Table('task',metadata,
        Column('id', Integer, primary_key=True),
        Column('name', Unicode(2048)),
        Column('rpm', Unicode(2048)),
        Column('oldrpm', Unicode(2048)),
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
        Column('owner_id', Integer,
                ForeignKey('tg_user.user_id')),
        Column('version', Unicode(256)),
        Column('license', Unicode(256)),
        Column('valid', Boolean)
)

task_bugzilla_table = Table('task_bugzilla',metadata,
        Column('id', Integer, primary_key=True),
        Column('bugzilla_id', Integer),
        Column('task_id', Integer,
                ForeignKey('task.id')),
)

task_packages_runfor_map = Table('task_packages_runfor_map', metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

task_packages_required_map = Table('task_packages_required_map', metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

task_packages_custom_map = Table('task_packages_custom_map', metadata,
    Column('recipe_id', Integer, ForeignKey('recipe.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('package_id', Integer, ForeignKey('task_package.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

task_property_needed_table = Table('task_property_needed', metadata,
        Column('id', Integer, primary_key=True),
        Column('task_id', Integer,
                ForeignKey('task.id')),
        Column('property', Unicode(2048))
)

task_package_table = Table('task_package',metadata,
        Column('id', Integer, primary_key=True),
        Column('package', Unicode(2048))
)

task_type_table = Table('task_type',metadata,
        Column('id', Integer, primary_key=True),
        Column('type', Unicode(256))
)

task_type_map = Table('task_type_map',metadata,
    Column('task_id', Integer, ForeignKey('task.id', onupdate='CASCADE',
        ondelete='CASCADE'), primary_key=True),
    Column('task_type_id', Integer, ForeignKey('task_type.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
)

# the identity model
class Visit(object):
    """
    A visit to your site
    """
    def lookup_visit(cls, visit_key):
        return cls.query.get(visit_key)
    lookup_visit = classmethod(lookup_visit)


class VisitIdentity(object):
    """
    A Visit that is link to a User object
    """
    pass


class User(object):
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
        if user:
            return user
        # If user doesn't exist in DB check ldap if enabled.
        if cls.ldapenabled:
            filter = "(uid=%s)" % user_name
            ldapcon = ldap.initialize(cls.uri)
            rc = ldapcon.search(cls.basedn, ldap.SCOPE_SUBTREE, filter)
            objects = ldapcon.result(rc)[1]
            if(len(objects) == 0):
                return None
            elif(len(objects) > 1):
                return None
            if cls.autocreate:
                user = User()
                user.user_name = user_name
                user.display_name = objects[0][1]['cn'][0]
	        user.email_address = objects[0][1]['mail'][0]
                session.save(user)
                session.flush([user])
            else:
                return None
        else:
            return None
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
        db_users = [user.user_name for user in cls.query().filter(f)]
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

class Permission(object):
    """
    A relationship that determines what each Group can do
    """

    @classmethod
    @cache
    def by_name(cls, permission_name):
        return cls.query.filter(cls.permission_name == permission_name).one()

    def __init__(self, permission_name):
        self.permission_name = permission_name

class MappedObject(object):

    doc = xml.dom.minidom.Document()

    @classmethod
    def lazy_create(cls, **kwargs):
        item = None
        try:
            item = cls.query.filter_by(**kwargs).one()
        except InvalidRequestError, e:
            if '%s' % e == 'Multiple rows returned for one()':
                log.error('Mutlitple rows returned for %s' % kwargs)
            elif '%s' % e == 'No rows returned for one()':
                item = cls(**kwargs)
                session.save(item)
                session.flush([item])
        return item

    def node(self, element, value):
        node = self.doc.createElement(element)
        node.appendChild(self.doc.createTextNode(value))
        return node

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
        #return "%s()" % (self.__class__.__name__)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()


class SystemObject(MappedObject):
    @classmethod
    def get_tables(cls):
        tables = cls.get_dict().keys()
        tables.sort()
        return tables
   
    @classmethod
    def get_allowable_dict(cls, allowable_properties):
        tables = dict( system = dict( joins=[], cls=cls)) 
        for property in allowable_properties:      
            try:

                property_got = cls.mapper.get_property(property)
	    except InvalidRequestError: pass 
            try:
                remoteTables = property_got.mapper.class_._get_dict()          
            except: pass
             
            for key in remoteTables.keys():             
                joins=[property_got.key]
                joins.extend(remoteTables[key]['joins'])     
                tables['%s/%s' % (property_got.key,key)] = dict( joins=joins, cls=remoteTables[key]['cls'])
            
            tables['system/%s' % property_got.key] = dict(joins=[property_got.key], cls=property_got.mapper.class_)
        
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
                except: pass
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
                except: pass
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

class SystemAdmin(MappedObject):
    pass

class Group(object):
    """
    An ultra-simple group definition.
    """
    @classmethod
    @cache
    def by_name(cls, name):
        return cls.query.filter_by(group_name=name).one()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(group_id=id).one()

    def can_admin_system(self,system_id=None,*args,**kw):
        if system_id is None:
            log.debug('can_admin_system called with no system_id')
            return False
        try:
            self.query().join(['admin_systems']).filter(and_(SystemAdmin.system_id == system_id,SystemAdmin.group_id == self.group_id)).one() 
            return True 
        except InvalidRequestError,e: 
            return False

    def __repr__(self):
        return self.display_name

    @classmethod
    def list_by_name(cls, name, find_anywhere=False):
        """
        A class method that can be used to search groups
        based on the group_name
        """
        if find_anywhere:
            q = cls.query().filter(Group.group_name.like('%%%s%%' % name))
        else:
            q = cls.query().filter(Group.group_name.like('%s%%' % name))
        return q

    @classmethod
    def by_user(cls,user):
        try:
            groups = Group.query().join('users').filter(User.user_id == user.user_id)
            return groups
        except Exception, e: 
            log.error(e)
            return

class System(SystemObject):

    def __init__(self, fqdn=None, status=None, contact=None, location=None,
                       model=None, type=None, serial=None, vendor=None,
                       owner=None):
        self.fqdn = fqdn
        self.status = status
        self.contact = contact
        self.location = location
        self.model = model
        self.type = type
        self.serial = serial
        self.vendor = vendor
        self.owner = owner
    
    def to_xml(self, clone=False):
        """ Return xml describing this system """
        fields = dict(
                      hostname    = 'fqdn',
                      system_type = ['type','type'],
                     )
                      
        host_requires = self.doc.createElement('hostRequires')
        xmland = self.doc.createElement('and')
        for key in fields.keys():
            require = self.doc.createElement(key)
            require.setAttribute('op', '=')
            if isinstance(fields[key], list):
                obj = self
                for field in fields[key]:
                    obj = getattr(obj, field, None)
                require.setAttribute('value', obj or '')
            else:
                require.setAttribute('value', getattr(self, fields[key], None) or '')
            xmland.appendChild(require)
        host_requires.appendChild(xmland)
        return host_requires

    def remote(self):
        class CobblerAPI:
            def __init__(self, system):
                self.system = system
                url = "http://%s/cobbler_api" % system.lab_controller.fqdn
                self.remote = bkr.timeout_xmlrpclib.ServerProxy(url, allow_none=True)
                self.token = self.remote.login(system.lab_controller.username,
                                               system.lab_controller.password)

            def version(self):
                return self.remote.version()

            def get_system(self):
                try:
                    system_id = self.remote.get_system_handle(self.system.fqdn, 
                                                                self.token)
                except xmlrpclib.Fault, msg:
                    system_id = self.remote.new_system(self.token)
                    try:
                        ipaddress = socket.gethostbyname_ex(self.system.fqdn)[2][0]
                    except socket.gaierror:
                        raise BX(_('%s does not resolve to an ip address' %
                                                              self.system.fqdn))
                    self.remote.modify_system(system_id, 
                                              'name', 
                                              self.system.fqdn, 
                                              self.token)
                    self.remote.modify_system(system_id, 
                                              'modify_interface',
                                              {'ipaddress-eth0': ipaddress}, 
                                              self.token)
                    profile = self.remote.get_item_names('profile')[0]
                    self.remote.modify_system(system_id, 
                                              'profile', 
                                              profile,
                                              self.token)
                    self.remote.modify_system(system_id, 
                                              'netboot-enabled', 
                                              False, 
                                              self.token)
                    self.remote.save_system(system_id, 
                                            self.token)
                return system_id

            def get_event_log(self, task_id):
                return self.remote.get_event_log(task_id)

            def wait_for_event(self, task_id):
                """ Wait for cobbler task to finish, return True on success
                    raise an exception if it fails.
                    raise an exception if it takes more then 5 minutes
                """
                try:
                    expiredelta = datetime.utcnow() + timedelta(minutes=10)
                    while(True): 
                        for line in self.get_event_log(task_id).split('\n'):
                            if line.find("### TASK COMPLETE ###") != -1:
                                return True
                            if line.find("### TASK FAILED ###") != -1:
                                raise CobblerTaskFailedException(_("Cobbler Task:%s Failed" % task_id))
                        if datetime.utcnow() > expiredelta:
                            raise CobblerTaskFailedException(_('Cobbler Task:%s Timed out' % task_id))
    
                        time.sleep(5)
                except CobblerTaskFailedException, e:
                    self.system.activity.append(SystemActivity(self.system.user,service='Cobbler API',action='Task',field_name='', new_value='Fail: %s' % e))
                    raise


                        
            def power(self,action='reboot', wait=False, clear_netboot=False):
                system_id = self.get_system()
                if clear_netboot:
                    self.remote.modify_system(system_id,
                            'netboot-enabled', False, self.token)
                self.remote.modify_system(system_id, 'power_type', 
                                              self.system.power.power_type.name,
                                                   self.token)
                self.remote.modify_system(system_id, 'power_address', 
                                                self.system.power.power_address,
                                                   self.token)
                self.remote.modify_system(system_id, 'power_user', 
                                                   self.system.power.power_user,
                                                   self.token)
                self.remote.modify_system(system_id, 'power_pass', 
                                                 self.system.power.power_passwd,
                                                   self.token)
                self.remote.modify_system(system_id, 'power_id', 
                                                   self.system.power.power_id,
                                                   self.token)
                self.remote.save_system(system_id, self.token)
                if '%f' % self.version() >= '%f' % 1.7:
                    try:
                        task_id = self.remote.background_power_system(
                                  dict(systems=[self.system.fqdn],power=action),
                                                                     self.token)
                        if wait:
                            return self.wait_for_event(task_id)
                        else:
                            return True
                    except xmlrpclib.Fault, msg:
                        raise BX(_('Failed to %s system %s' % (action,self.system.fqdn)))
                else:
                    try:
                        return self.remote.power_system(system_id, action, self.token)
                    except xmlrpclib.Fault, msg:
                        raise BX(_('Failed to %s system %s' % (action,self.system.fqdn)))
                return False

            def provision(self, 
                          distro=None, 
                          kickstart=None,
                          ks_meta=None,
                          kernel_options=None,
                          kernel_options_post=None,
                          ks_appends=None):
                """
                Provision the System
                make xmlrpc call to lab controller
                """
                if not distro:
                    return False

                system_id = self.get_system()
                profile = distro.install_name
                systemprofile = profile
                try:
                    profile_id = self.remote.get_profile_handle(profile, self.token)
                except xmlrpclib.Fault, fault:
                    raise BX(_("%s profile not found on %s" % (profile, self.system.lab_controller.fqdn)))
                if not profile_id:
                    raise BX(_("%s profile not found on %s" % (profile, self.system.lab_controller.fqdn)))
                if ks_appends:
                    ks_appends_text = '#raw\n%s\n#end raw' % '\n'.join([ks.ks_append for ks in ks_appends])
                    ks_file = '/var/lib/cobbler/snippets/per_system/ks_appends/%s' % self.system.fqdn
                    if self.remote.read_or_write_snippet(ks_file,
                                                         False,
                                                         ks_appends_text,
                                                         self.token):
                        ks_meta['ks_appends'] = True
                    else:
                        raise BX(_("Failed to save ks_appends"))

                self.remote.modify_system(system_id, 
                                          'ksmeta',
                                           ks_meta,
                                           self.token)
                self.remote.modify_system(system_id,
                                           'kopts',
                                           kernel_options,
                                           self.token)
                self.remote.modify_system(system_id,
                                           'kopts_post',
                                           kernel_options_post,
                                           self.token)
                if kickstart:
                    # We always wrap the user-supplied kickstart with #raw/#end raw, 
                    # so that users don't need to worry about escaping their 
                    # kickstarts from Cobbler's cheetah. If a user really does 
                    # want to do fancy Cobbler template stuff, they can put 
                    # #end raw and #raw lines in the appropriate place in their 
                    # kickstart.
                    kickstart = 'url --url=$tree\n#raw\n%s\n#end raw' % kickstart

                    kickfile = '/var/lib/cobbler/kickstarts/%s.ks' % self.system.fqdn
        
                    systemprofile = self.system.fqdn
                    try:
                        pid = self.remote.get_profile_handle(self.system.fqdn, 
                                                             self.token)
                    except:
                        pid = self.remote.new_subprofile(self.token)
                        self.remote.modify_profile(pid, 
                                              "name",
                                              self.system.fqdn,
                                              self.token)
                    if self.remote.read_or_write_kickstart_template(kickfile,
                                                               False,
                                                               kickstart,
                                                               self.token):
                        self.remote.modify_profile(pid, 
                                              'kickstart', 
                                              kickfile, 
                                              self.token)
                        self.remote.modify_profile(pid, 
                                              'parent', 
                                              profile, 
                                              self.token)
                        self.remote.save_profile(pid, 
                                              self.token)
                    else:
                        raise BX(_("Failed to save kickstart"))
                self.remote.modify_system(system_id, 
                                     'profile', 
                                     systemprofile, 
                                     self.token)
                self.remote.modify_system(system_id, 
                                     'netboot-enabled', 
                                     True, 
                                     self.token)
                try:
                    self.remote.save_system(system_id, self.token)
                except xmlrpclib.Fault, msg:
                    raise BX(_("Failed to provision system %s" % self.system.fqdn))
                try:
                    self.remote.clear_system_logs(system_id, self.token)
                except xmlrpclib.Fault, msg:
                    raise BX(_("Failed to clear %s logs" % self.system.fqdn))

            def release(self, power=True):
                """ Turn off netboot and turn off system by default
                """
                system_id = self.get_system()
                self.remote.modify_system(system_id, 
                                          'netboot-enabled', 
                                          False, 
                                          self.token)
                self.remote.save_system(system_id, 
                                        self.token)
                if self.system.power and power:
                    self.power(action="off", wait=False)

        # remote methods are only available if we have a lab controller
        #  Here is where we would add other types of lab controllers
        #  right now we only support cobbler
        if self.lab_controller:
            return CobblerAPI(self)

    remote = property(remote)

    @classmethod
    def all(cls, user=None,system = None): 
        """
        Only systems that the current user has permission to see
        
        """
        if system is None:
            query = cls.query().outerjoin(['groups','users'], aliased=True)
        else:
            try: 
                query = system.outerjoin(['groups','users'], aliased=True)
            except AttributeError, (e):
                log.error('A non Query object has been passed into the all method, using default query instead: %s' % e)        
                query = cls.query().outerjoin(['groups','users'], aliased=True)

        return cls.permissable_systems(query,user)

    @classmethod
    def permissable_systems(cls, query, user=None, *arg, **kw):

        if user is None:
            try:
                user = identity.current.user
            except AttributeError, e:
                user = None

        if user:
            if not user.is_admin():
                query = query.filter(
                            or_(System.private==False,
                              and_(System.private==True,
                                   or_(User.user_id==user.user_id,
                                       System.owner==user,
                                        System.user==user))))
        else:
            query = query.filter(System.private==False)
         
        return query


    @classmethod
    def free(cls, user, systems=None):
        """
        Builds on available.  Only systems with no users.
        """
        return System.available(user,systems).filter(System.user==None)

    @classmethod
    def available_for_schedule(cls, user, systems=None):
        """ 
        Will return systems that are available to user for scheduling
        """
        return cls._available(user, systems=systems, system_status=SystemStatus.by_name(u'Automated'))

    @classmethod
    def _available(self, user, system_status=None, systems=None):
        """
        Builds on all.  Only systems which this user has permission to reserve.
          If a system is loaned then its only available for that person. Can take varying system_status' as args as well
        """
        if systems:
            try:
                query = systems.outerjoin(['groups','users'], aliased=True)
            except AttributeError, (e):
                log.error('A non Query object has been passed into the available method, using default query instead: %s' % e)
                query = cls.query().outerjoin(['groups','users'], aliased=True)
        else:
            query = System.all(user)

        if type(system_status) is list:
            whereclause_items = [System.status==k for k in system_status]
            system_status_whereclause = or_(*whereclause_items)
        elif type(system_status) is SystemStatus: 
            system_status_whereclause = System.status==system_status 
        else: #Possibly we are none or somthing else...
            system_status_whereclause = or_(System.status==SystemStatus.by_name(u'Automated'),System.status==SystemStatus.by_name(u'Manual'))
 
        query = query.filter(and_(system_status_whereclause,
                                or_(and_(System.owner==user,
                                        System.loaned==None), 
                                    System.loaned==user,
                                    and_(System.shared==True, 
                                         System.groups==None,
                                         System.loaned==None
                                        ),
                                    and_(System.shared==True,
                                         System.loaned==None,
                                         User.user_id==user.user_id
                                        )
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
    def available_order(cls, user):
        return cls.available_for_schedule(user).order_by(case([(System.owner==user, 1),
                          (System.owner!=user and Group.systems==None, 2)],
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
        return System.query().join(['groups']).filter(Group.group_id == group_id)
    
    @classmethod
    def by_type(cls,type,user=None,systems=None):
        if systems:
            query = systems
        else:
            if user:
                query = System.all(user)
            else:
                query = System.all()
        return query.filter(System.type.has(SystemType.type == type))

    @classmethod
    def by_arch(cls,arch,query=None):
        if query:
            return query.filter(System.arch.any(Arch.arch == arch))
        else:
            return System.query().filter(System.arch.any(Arch.arch == arch))

    @classmethod
    def reserved_via(cls, service='WEBUI'): 
        activity_ids = cls._latest_reserved()
        taken = []
        for id in activity_ids:
            try: 
                take_activity = SystemActivity.query().join('object').filter(and_(SystemActivity.id==id,SystemActivity.service == service)).one()
                taken.append(take_activity)
            except InvalidRequestError,e:
                pass
        return taken
   
    @classmethod
    def _latest_reserved(cls): 
        f_obj= system_table.join(system_activity_table).join(activity_table)
        s = select([func.max(system_activity_table.c.id)],from_obj=f_obj,whereclause=and_(activity_table.c.action == 'Reserved',System.user != None)).group_by(system_table.c.id)
        log.debug(s)
        result = s.execute()
        ids = [row[0] for row in result.fetchall()] 
        log.debug(ids) 
        return ids

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

    def install_options(self, distro, ks_meta = '', kernel_options = '',
                           kernel_options_post = ''):
        """
        Return install options based on distro selected.
        Inherit options from Arch -> Family -> Update
        """
        override = dict(ks_meta = string_to_hash(ks_meta), 
                       kernel_options = string_to_hash(kernel_options), 
                       kernel_options_post = string_to_hash(kernel_options_post))
        results = dict(ks_meta = {},
                       kernel_options = {},
                       kernel_options_post = {})
        if distro.arch in self.provisions:
            pa = self.provisions[distro.arch]
            node = self.provision_to_dict(pa)
            consolidate(node,results)
            if distro.osversion.osmajor in pa.provision_families:
                pf = pa.provision_families[distro.osversion.osmajor]
                node = self.provision_to_dict(pf)
                consolidate(node,results)
                if distro.osversion in pf.provision_family_updates:
                    pfu = pf.provision_family_updates[distro.osversion]
                    node = self.provision_to_dict(pfu)
                    consolidate(node,results)
        consolidate(override,results)
        return results

    def provision_to_dict(self, provision):
        ks_meta = string_to_hash(provision.ks_meta)
        kernel_options = string_to_hash(provision.kernel_options)
        kernel_options_post = string_to_hash(provision.kernel_options_post)
        return dict(ks_meta = ks_meta, kernel_options = kernel_options,
                            kernel_options_post = kernel_options_post)

    def is_free(self):
        if not self.user:
            return True
        else:
            return False

    def is_admin(self,group_id=None,user_id=None,groups=None,*args,**kw):
        try:
            if identity.in_group('admin'): #first let's see if we are an _admin_
                return True
        except AttributeError,e: pass #We may not be logged in...
        
        #If we are the owner.... 
        if self.owner == User.by_id(user_id):
            return True

        if group_id: #Let's try this next as this will be the quicker query
            try:
                if self.admins.query().filter(SystemAdmin.group_id==group_id).one():
                    return True
            except InvalidRequestError, e:
                return False

        if user_id: 
                group_q = Group.query().join('users').filter_by(user_id=user_id)
                g_ids = [e.group_id for e in group_q] 
                admin_q = self.query().join(['admins']).filter(and_(SystemAdmin.group_id.in_(g_ids),SystemAdmin.system_id == self.id))
             
                if admin_q.count() > 0: 
                    log.debug('We have a count of more than 1!!')
                    return True
                else:
                    return False 

        #let's try the currently logged in user
        groups = identity.current.user.groups
        for group in groups:
            if group.can_admin_system(self.id):
                return True 
        return False

    def can_admin(self,user=None,group_id=None): 
        if user:
            if user == self.owner or user.is_admin() or self.is_admin(group_id=group_id,user_id=user.user_id): 
                return True
        return False

    def can_provision_now(self,user=None): 
        if user is not None and self.is_admin(user_id=user.user_id):
            return True
        elif user is not None and self.loaned == user:
            return True
        elif user is not None and self._user_in_systemgroup(user):
            return True
        elif user is None:
            return False

        if self.status==SystemStatus.by_name('Manual'): #If it's manual then we us our original perm system.
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
            if self.loaned and self.loaned == user:
                return True
            if self.shared:
                # If the user is in the Systems groups
                if self.groups:
                    if self._user_in_systemgroup(user):
                        return True
                else: 
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
        try:
            if identity.in_group('admin'):
                return True
        except AttributeError, e: #not logged in ?
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

        
    def get_allowed_attr(self):
        attributes = ['vendor','model','memory']
        return attributes

    def get_update_method(self,obj_str):
        methods = dict ( Cpu = self.updateCpu, Arch = self.updateArch, 
                         Devices = self.updateDevices, Numa = self.updateNuma )
        return methods[obj_str]

    def update_legacy(self, inventory):
        """
        Update Key/Value pairs for legacy RHTS
        """
        new_int_kvs = set()
        new_string_kvs = set()
        for key_name, values in inventory.items():
            try:
                key = Key.by_name(key_name)
            except InvalidRequestError:
                continue
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
            if (kv.key, kv.key_value) in new_int_kvs:
                new_int_kvs.remove((kv.key, kv.key_value))
            else:
                self.key_values_int.remove(kv)
                self.activity.append(SystemActivity(user=identity.current.user,
                        service=u'XMLRPC', action=u'Removed', field_name=u'Key/Value',
                        old_value=u'%s/%s' % (kv.key.key_name, kv.key_value),
                        new_value=None))
        for kv in list(self.key_values_string):
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

        md5sum = md5.new("%s" % inventory).hexdigest()
        if self.checksum == md5sum:
            return 0
        self.activity.append(SystemActivity(user=identity.current.user,
                service=u'XMLRPC', action=u'Changed', field_name=u'checksum',
                old_value=self.checksum, new_value=md5sum))
        self.checksum = md5sum
        for key in inventory:
            if key in self.get_allowed_attr():
                if not getattr(self, key, None):
                    setattr(self, key, inventory[key])
                    self.activity.append(SystemActivity(
                            user=identity.current.user,
                            service=u'XMLRPC', action=u'Changed',
                            field_name=key, old_value=None,
                            new_value=inventory[key]))
            else:
                try:
                    method = self.get_update_method(key)
                    method(inventory[key])
                except:
                   raise
        self.date_modified = datetime.utcnow()
        return 0

    def updateArch(self, archinfo):
        for arch in archinfo:
            try:
                new_arch = Arch.by_name(arch)
            except:
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
            try:
                mydevice = Device.query().filter_by(vendor_id = device['vendorID'],
                                   device_id = device['deviceID'],
                                   subsys_vendor_id = device['subsysVendorID'],
                                   subsys_device_id = device['subsysDeviceID'],
                                   bus = device['bus'],
                                   driver = device['driver'],
                                   description = device['description']).one()
            except InvalidRequestError:
                mydevice = Device(vendor_id       = device['vendorID'],
                                     device_id       = device['deviceID'],
                                     subsys_vendor_id = device['subsysVendorID'],
                                     subsys_device_id = device['subsysDeviceID'],
                                     bus            = device['bus'],
                                     driver         = device['driver'],
                                     device_class   = device['type'],
                                     description    = device['description'])
                session.save(mydevice)
                session.flush([mydevice])
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
        excluded = ExcludeOSMajor.query().join('system').\
                    join('arch').filter(and_(System.id==self.id,
                                             Arch.id==arch.id))
        return excluded

    def excluded_osversion_byarch(self, arch):
        """
        List excluded osversion for system by arch
        """
        excluded = ExcludeOSVersion.query().join('system').\
                    join('arch').filter(and_(System.id==self.id,
                                             Arch.id==arch.id))
        return excluded

    def distros(self):
        """
        List of distros that support this system
        """
        distros = Distro.query().join(['arch','systems']).filter(
              and_(System.id==self.id,
                   System.lab_controller_id==LabController.id,
                   lab_controller_distro_map.c.distro_id==Distro.id,
                   lab_controller_distro_map.c.lab_controller_id==LabController.id,
                not_(or_(Distro.id.in_(select([distro_table.c.id]).
                  where(distro_table.c.arch_id==arch_table.c.id).
                  where(arch_table.c.id==exclude_osmajor_table.c.arch_id).
                  where(distro_table.c.osversion_id==osversion_table.c.id).
                  where(osversion_table.c.osmajor_id==osmajor_table.c.id).
                  where(osmajor_table.c.id==exclude_osmajor_table.c.osmajor_id).
                  where(exclude_osmajor_table.c.system_id==system_table.c.id)
                                      ),
                         Distro.id.in_(select([distro_table.c.id]).
                  where(distro_table.c.arch_id==arch_table.c.id).
                  where(arch_table.c.id==exclude_osversion_table.c.arch_id).
                  where(distro_table.c.osversion_id==osversion_table.c.id).
                  where(osversion_table.c.id==
                                        exclude_osversion_table.c.osversion_id).
                  where(exclude_osversion_table.c.system_id==system_table.c.id)
                                      )
                        )
                    )
                  )
        )
        if self.type.type != 'Virtual':
            distros = distros.filter(distro_table.c.virt==False)
        return distros

    def action_release(self):
        # Attempt to remove Netboot entry
        # and turn off machine, but don't fail if we can't
        if self.release_action:
            try:
                self.remote.release(power=False)
                self.release_action.do(self)
            except BX, error:
                pass
            except xmlrpclib.Fault:
                pass
        else:
            try:
                self.remote.release()
            except:
                pass
        self.user = None

    def action_provision(self, 
                         distro=None,
                         ks_meta=None,
                         kernel_options=None,
                         kernel_options_post=None,
                         kickstart=None,
                         ks_appends=None):
        try:
            if not self.can_provision_now(identity.current.user): #Needs to be an authorised user to do this
                return False
        except AttributeError, e: #Anonymous can't provision now
            return False

        if not self.remote:
            return False
        self.remote.provision(distro=distro, 
                              ks_meta=ks_meta,
                              kernel_options=kernel_options,
                              kernel_options_post=kernel_options_post,
                              kickstart=kickstart,
                              ks_appends=None)

    def action_auto_provision(self, 
                             distro=None,
                             ks_meta=None,
                             kernel_options=None,
                             kernel_options_post=None,
                             kickstart=None,
                             ks_appends=None,
                             wait=False):
        if not self.remote:
            return False

        results = self.install_options(distro, ks_meta,
                                               kernel_options,
                                               kernel_options_post)

        if kickstart:
            # Newer Kickstarts need %end after each section.
            if distro.osversion.osmajor.osmajor.startswith("Fedora"):
                end = "%end"
            else:
                end = ""
            # add in cobbler packages snippet...
            packages_slot = 0
            nopackages = True
            for line in kickstart.split('\n'):
                # Add the length of line + newline
                packages_slot += len(line) + 1
                if line.find('%packages') == 0:
                    nopackages = False
                    break
            beforepackages = kickstart[:packages_slot-1]
            afterpackages = kickstart[packages_slot:]
            # if no %packages section then add it
            if nopackages:
                beforepackages = "%s\n%%packages --ignoremissing" % beforepackages
                if end:
                    afterpackages = "%%end\n%s" % afterpackages
            # Fill in basic requirements for RHTS
            kicktemplate = """
%(beforepackages)s
#end raw
$SNIPPET("rhts_packages")
#raw
%(afterpackages)s
#end raw

%%pre
$SNIPPET("rhts_pre")
%(end)s

%%post
$SNIPPET("rhts_post")
%(end)s
#raw
           """
            kickstart = kicktemplate % dict(
                                        beforepackages = beforepackages,
                                        afterpackages = afterpackages,
                                        end = end)

        self.remote.provision(distro=distro,
                              kickstart=kickstart,
                              ks_appends=ks_appends,
                              **results)
        if self.power:
            self.remote.power(action="reboot", wait=wait)

    def action_power(self, action='reboot', wait=False, clear_netboot=False):
        if self.remote and self.power:
            self.remote.power(action, wait=wait, clear_netboot=clear_netboot)
        else:
            return False

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

    def mark_broken(self, reason, recipe=None):
        """Sets the system status to Broken and notifies its owner."""
        log.warning('Marking system %s as broken' % self.fqdn)
        self.status = SystemStatus.by_name(u'Broken')
        self.date_modified = datetime.utcnow()
        mail.broken_system_notify(self, reason, recipe)

    def suspicious_abort(self):
        if self.status == SystemStatus.by_name(u'Broken'):
            return # nothing to do
        if self.type != SystemType.by_name(u'Machine'):
            return # prototypes get more leeway, and virtual machines can't really "break"...
        reliable_distro_tag = get('beaker.reliable_distro_tag', None)
        if not reliable_distro_tag:
            return
        # Since its last status change, has this system had an 
        # uninterrupted run of aborted recipes leading up to this one, with 
        # at least two different STABLE distros?
        # XXX this query is stupidly big, I need to do something about it
        status_change_subquery = select([func.max(activity_table.c.created)],
            from_obj=activity_table.join(system_activity_table))\
            .where(and_(
                system_activity_table.c.system_id == self.id,
                activity_table.c.field_name == u'Status',
                activity_table.c.action == u'Changed'))
        system_added_subquery = select([system_table.c.date_added])\
            .where(system_table.c.id == self.id)
        nonaborted_recipe_subquery = select([func.max(recipe_table.c.finish_time)],
            from_obj=recipe_table.join(system_table))\
            .where(and_(
                recipe_table.c.status_id != TaskStatus.by_name(u'Aborted').id,
                recipe_table.c.system_id == self.id))
        query = select([func.count(recipe_table.c.distro_id.distinct())],
            from_obj=recipe_table.join(distro_table).join(distro_tag_map)
                .join(system_table, onclause=recipe_table.c.system_id == system_table.c.id))\
            .where(and_(
                system_table.c.id == self.id,
                distro_tag_map.c.distro_tag_id ==
                    DistroTag.by_tag(reliable_distro_tag.decode('utf8')).id,
                recipe_table.c.start_time >
                    func.ifnull(status_change_subquery, system_added_subquery),
                recipe_table.c.finish_time > nonaborted_recipe_subquery))
        if session.execute(query).scalar() >= 2:
            # Broken!
            reason = unicode(_(u'System has a run of aborted recipes '
                    'with reliable distros'))
            log.warn(reason)
            old_status = self.status
            self.mark_broken(reason=reason)
            self.activity.append(
                    SystemActivity(service=u'Scheduler',
                    action=u'Changed', field_name=u'Status',
                    old_value=old_status,
                    new_value=self.status))

    def reserve(self, service):
        if self.user is not None and self.user == identity.current.user:
            raise BX(_(u'User %s has already reserved system %s')
                    % (identity.current.user, self))
        if not self.can_share(identity.current.user):
            raise BX(_(u'User %s cannot reserve system %s')
                    % (identity.current.user, self))
        # Atomic operation to reserve the system
        if session.connection(System).execute(system_table.update(
                and_(system_table.c.id == self.id,
                     system_table.c.user_id == None)),
                user_id=identity.current.user.user_id).rowcount == 1:
            self.activity.append(SystemActivity(user=identity.current.user,
                    service=service, action=u'Reserved', field_name=u'User',
                    old_value=u'', new_value=identity.current.user))
        else:
            raise BX(_(u'System is already reserved'))

    def unreserve(self, service):
        if self.user is None:
            raise BX(_(u'System is not reserved'))
        if not self.current_user(identity.current.user):
            raise BX(_(u'System is reserved by a different user'))
        # Don't return a system with an active watchdog
        if self.watchdog:
            # This won't really happen anymore since the Manual/Automated split
            raise BX(_(u'System has active recipe %s') % self.watchdog.recipe_id)
        activity = SystemActivity(user=identity.current.user,
                service=service, action=u'Returned', field_name=u'User',
                old_value=self.user.user_name, new_value=u'')
        try:
            self.action_release()
        except BX, e:
            msg = "Error: %s Action: %s" % (error_msg,self.release_action)
            self.activity.append(SystemActivity(user=identity.current.user,
                    service=service, action=unicode(self.release_action),
                    field_name=u'Return', old_value=u'', new_value=msg))
            raise e
        self.activity.append(activity)

    cc = association_proxy('_system_ccs', 'email_address')

class SystemCc(SystemObject):

    def __init__(self, email_address):
        self.email_address = email_address
  
class SystemType(SystemObject):

    def __init__(self, type=None):
        self.type = type

    def __repr__(self):
        return self.type

    @classmethod
    def get_all_types(cls):
        """
        Desktop, Server, Virtual
        """
        all_types = cls.query()
        return [(type.id, type.type) for type in all_types]
    @classmethod
    def get_all_type_names(cls):
        all_types = cls.query()
        return [type.type for type in all_types]

    @classmethod
    @cache
    def by_name(cls, systemtype):
        return cls.query.filter_by(type=systemtype).one()


class ReleaseAction(SystemObject):

    def __init__(self, action=None):
        self.action = action

    def __repr__(self):
        return self.action

    @classmethod
    def get_all(cls):
        """
        PowerOff, LeaveOn or ReProvision
        """
        all_actions = cls.query()
        return [(raction.id, raction.action) for raction in all_actions]

    @classmethod
    def by_id(cls, id):
        """ 
        Look up ReleaseAction by id.
        """
        return cls.query.filter_by(id=id).one()

    def do(self, *args, **kwargs):
        try:
            getattr(self, self.action)(*args, **kwargs)
        except Exception ,msg:
            raise BX(_('%s' % msg))

    def PowerOff(self, system):
        """ Turn off system
        """
        system.remote.power(action='off')

    def LeaveOn(self, system):
        """ Leave system running
        """
        system.remote.power(action='on')

    def ReProvision(self, system):
        """ re-provision the system 
        """
        if system.reprovision_distro:
            system.action_auto_provision(distro=system.reprovision_distro)


class SystemStatus(SystemObject):

    def __init__(self, status=None):
        self.status = status

    def __repr__(self):
        return self.status

    @classmethod
    def get_all_status(cls):
        """
        Available, InUse, Offline
        """
        all_status = cls.query()
        return [(status.id, status.status) for status in all_status]

    @classmethod
    def get_all_status_name(cls):
       all_status_name = cls.query()
       return [status_name.status for status_name in all_status_name]      


    @classmethod
    @cache
    def by_name(cls, systemstatus):
        return cls.query.filter_by(status=systemstatus).one()
 
    @classmethod
    def by_id(cls,status_id):
        return cls.query.filter_by(id=status_id).one()



class Arch(MappedObject):
    def __init__(self, arch=None):
        self.arch = arch

    def __repr__(self):
        return '%s' % self.arch

    @classmethod
    def get_all(cls):
        return [(0,"All")] + [(arch.id, arch.arch) for arch in cls.query()]

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
        return cls.query().filter(Arch.arch.like('%s%%' % name))


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


class Breed(SystemObject):
    def __init__(self, breed):
        self.breed = breed

    @classmethod
    def by_name(cls, breed):
        return cls.query.filter_by(breed=breed).one()

    def __repr__(self):
        return self.breed


class OSMajor(MappedObject):
    def __init__(self, osmajor):
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
    def get_all(cls):
        return [(0,"All")] + [(major.id, major.osmajor) for major in cls.query()]

    def __repr__(self):
        return '%s' % self.osmajor


class OSVersion(MappedObject):
    def __init__(self, osmajor, osminor, arches=None):
        self.osmajor = osmajor
        self.osminor = osminor
        self.arches = arches

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, osmajor, osminor):
        return cls.query.filter_by(osmajor=osmajor, osminor=osminor).one()

    @classmethod
    def get_all(cls):
        all = cls.query()
        return [(0,"All")] + [(version.id, version.osminor) for version in all]

    @classmethod
    def list_osmajor_by_name(cls,name,find_anywhere=False):
        if find_anywhere:
            q = cls.query().join(['osmajor']).filter(OSMajor.osmajor.like('%%%s%%' % name))
        else:
            q = cls.query().join(['osmajor']).filter(OSMajor.osmajor.like('%s%%' % name))
        return q
    

    def __repr__(self):
        return "%s.%s" % (self.osmajor,self.osminor)

    


class LabControllerDistro(SystemObject):
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
    def get_all(cls):
        """
        Desktop, Server, Virtual
        """
        all = cls.query()
        return [(lc.id, lc.fqdn) for lc in all]

    distros = association_proxy('_distros', 'distro')


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
        """ return a list of all watchdog entries that are either active 
            or expired for this lab controller
            All recipes in a recipeset have to expire.
        """
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
        
        if labcontroller is None: 
            my_filter = and_(RecipeSet.id.in_(select([recipe_set_table.c.id], 
                                from_obj=[watchdog_table.join(recipe_table).join(recipe_set_table)]
                            ).group_by(RecipeSet.id).having(
                                getattr(func, fop)(getattr(Watchdog.kill_time, op)(datetime.utcnow()))
                                                        )
                                )
                )
        else:
            my_filter = and_(System.lab_controller==labcontroller,
                RecipeSet.id.in_(select([recipe_set_table.c.id], 
                            from_obj=[watchdog_table.join(recipe_table).join(recipe_set_table)]
                            ).group_by(RecipeSet.id).having(
                                getattr(func, fop)(getattr(Watchdog.kill_time, op)(datetime.utcnow()))
                                                        )
                                )
                )

        if op and fop:
            return cls.query().join('system').join(['recipe','recipeset']).filter(my_filter)
                                                                                 

class LabInfo(SystemObject):
    fields = ['orig_cost', 'curr_cost', 'dimensions', 'weight', 'wattage', 'cooling']


class Cpu(SystemObject):
    def __init__(self, vendor=None, model=None, model_name=None, family=None, stepping=None,speed=None,processors=None,cores=None,sockets=None,flags=None):
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
        self.flag = flag

    def __repr__(self):
        return self.flag

    def by_flag(cls, flag):
        return cls.query.filter_by(flag=flag)

    by_flag = classmethod(by_flag)


class Numa(SystemObject):
    def __init__(self, nodes=None):
        self.nodes = nodes

    def __repr__(self):
        return self.nodes


class DeviceClass(SystemObject):
    def __init__(self, device_class=None, description=None):
        if not device_class:
            device_class = "NONE"
        self.device_class = device_class
        self.description = description

    def __repr__(self):
        return self.device_class


class Device(SystemObject):
    def __init__(self, vendor_id=None, device_id=None, subsys_device_id=None, subsys_vendor_id=None, bus=None, driver=None, device_class=None, description=None):
        if not device_class:
            device_class = "NONE"
        try:
            dc = DeviceClass.query.filter_by(device_class = device_class).one()
        except InvalidRequestError:
            dc = DeviceClass(device_class = device_class)
            session.save(dc)
            session.flush([dc])
        self.vendor_id = vendor_id
        self.device_id = device_id
        self.subsys_vendor_id = subsys_vendor_id
        self.subsys_device_id = subsys_device_id
        self.bus = bus
        self.driver = driver
        self.description = description
        self.device_class = dc


class Locked(object):
    def __init__(self, name=None):
        self.name = name


class PowerType(object):

    def __init__(self, name=None):
        self.name = name

    @classmethod
    def get_all(cls):
        """
        Apc, wti, etc..
        """
        all_types = cls.query()
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
            q = cls.query().filter(PowerType.name.like('%%%s%%' % name))
        else:
            q = cls.query().filter(PowerType.name.like('%s%%' % name))
        return q

class Power(SystemObject):
    pass


class Serial(object):
    def __init__(self, name=None):
        self.name = name


class SerialType(object):
    def __init__(self, name=None):
        self.name = name


class Install(object):
    def __init__(self, name=None):
        self.name = name


def _create_tag(tag):
    """A creator function."""
    try:
        tag = DistroTag.by_tag(tag)
    except InvalidRequestError:
        tag = DistroTag(tag=tag)
        session.save(tag)
        session.flush([tag])
    return tag


class Distro(MappedObject): 
    # EXCLUDE_OVER_MULTIPLE_ARCHES holds text that we do not want in a multi arch install. We have PAE here,
    # because  a PAE and non PAE i386 distro is indutinguishable from another, so it will return a PAE distro, if we are searching on
    # i386 and say x86_64, even though clearly, it's not applicable to the later. This only applies to multiple arches 
    _EXCLUDE_OVER_MULTIPLE_ARCHES = 'PAE'

    def __init__(self, install_name=None):
        self.install_name = install_name
 
    @classmethod
    def all_methods(cls):
        methods = [elem[0] for elem in select([distro_table.c.method],whereclause=distro_table.c.method != None,from_obj=distro_table,distinct=True).execute()]
        return methods 

    @classmethod
    def by_install_name(cls, install_name):
        return cls.query.filter_by(install_name=install_name).one()

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    tags = association_proxy('_tags', 'tag', creator=_create_tag)

    @classmethod
    def by_filter(cls, filter):
        """
        <distro>
         <And>
           <Require name='ARCH' operator='=' value='i386'/>
           <Require name='FAMILY' operator='=' value='rhelserver5'/>
           <Require name='TAG' operator='=' value='released'/>
         </And>
        </distro>
        """
        from needpropertyxml import ElementWrapper
        import xmltramp
        #FIXME Should validate XML before proceeding.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(filter)):
            if callable(getattr(child, 'filter', None)):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        # Join on lab_controller_assocs or we may get a distro that is not on any 
        # lab controller anymore.
        distros = Distro.query().join('lab_controller_assocs')
        if joins:
            distros = distros.filter(and_(*joins))
        if queries:
            distros = distros.filter(and_(*queries))
        return distros.order_by('-date_created')

    def to_xml(self, clone=False):
        """ Return xml describing this distro """
        fields = dict(
                      distro_name    = 'name',
                      distro_arch    = ['arch','arch'],
                      distro_method  = 'method',
                      distro_variant = 'variant',
                      distro_virt    = 'virt',
                      distro_family  = ['osversion','osmajor','osmajor'],
                     )
                      
        distro_requires = self.doc.createElement('distroRequires')
        xmland = self.doc.createElement('and')
        for key in fields.keys():
            require = self.doc.createElement(key)
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

    def systems_filter(self, user, filter):
        """
        Return Systems that match the following filter
        <host>
         <And>
           <Require name='MACHINE' operator='!=' value='dell-pe700-01.rhts.bos.redhat.com'/>
           <Require name='ARCH' operator='=' value='i386'/>
           <Require name='MEMORY' operator='>=' value='2048'/>
           <Require name='POWER' operator='=' value='True'/>
         </And>
        </host>
        System.query.\
           join('key_values',aliased=True).\ 
                filter_by(key_name='MEMORY').\
                filter(key_value_table.c.key_value > 2048).\
           join('key_values',aliased=True).\
                filter_by(key_name='CPUFLAGS').\
                filter(key_value_table.c.key_value == 'lm').\
              all()
        [hp-xw8600-02.rhts.bos.redhat.com]
        """
        from needpropertyxml import ElementWrapper
        import xmltramp
        systems = self.all_systems(user)
        #FIXME Should validate XML before processing.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(filter)):
            if callable(getattr(child, 'filter', None)):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        if joins:
            systems = systems.filter(and_(*joins))
        if queries:
            systems = systems.filter(and_(*queries))
        return systems

    def tasks(self):
        """
        List of tasks that support this distro
        """
        return Task.query().filter(
                not_(or_(Task.id.in_(select([task_table.c.id]).
                 where(task_table.c.id==task_exclude_arch_table.c.task_id).
                 where(task_exclude_arch_table.c.arch_id==arch_table.c.id).
                 where(arch_table.c.id==self.arch_id)
                                      ),
                         Task.id.in_(select([task_table.c.id]).
                 where(task_table.c.id==task_exclude_osmajor_table.c.task_id).
                 where(task_exclude_osmajor_table.c.osmajor_id==osmajor_table.c.id).
                 where(osmajor_table.c.id==self.osversion.osmajor.id)
                                      ),
                        )
                    )
        )
    @classmethod
    def _create_arch_distro_map(cls,*args,**kw):
        """
        multiple_distro_systems() will return a list of distro's that are applicable for a certain criteria.
        The criteria can be
        *method
        *arch
        *osmajor
        """
        method = kw.get('method')
        arch = kw.get('arch')
        osmajor = kw.get('osmajor')
        tag = kw.get('tag')

        if method is None and arch is None and osmajor is None:
            log.error('Nothing has been passed into mulitple_distro_systems')
            return
         
        if isinstance(arch,list):
            local_arches = arch 
        elif isinstance(arch,str):
            local_arches = [arch]
        
        cache_locator = []
        my_from = distro_table
        my_and = [not_(distro_table.c.install_name.like('%%%s%%' % Distro._EXCLUDE_OVER_MULTIPLE_ARCHES))]
        if arch:
            my_from = my_from.join(arch_table)
        if osmajor:
            my_from = my_from.join(osversion_table). \
                                join(osmajor_table) 
            my_and.append(osmajor_table.c.osmajor == osmajor)
        if tag: 
            my_from = my_from.join(distro_tag_map).join(distro_tag_table)
            my_and.append(distro_tag_table.c.tag == tag) 
        for var in (osmajor,method,tag) + tuple(sorted(local_arches)):
            if var:
                cache_locator.append(var)

        #FIXME: It was probably silly of me to be creating class vars on the fly and caching values in them
        # I should really create a more throughly thought out caching system
        cache_location = "_".join(cache_locator)
        the_cache = getattr(Distro,cache_location,None)
        if the_cache: #phew, we don't have to do that big ugly slow query 
            log.debug('Returning our cached items for %s' % cache_location)
            return the_cache
        current_derived = None
        future_arch_cache = {}
        for local_arch in local_arches:
            my_derived = select([distro_table.c.name,distro_table.c.install_name,distro_table.c.id.label('distro_id'),distro_table.c.date_created],
                                whereclause= and_(*my_and + [arch_table.c.arch == local_arch,distro_table.c.method == method] ),
                                from_obj=my_from).alias(local_arch)
            
            if current_derived is None:
                current_derived = my_derived
                first_derived = my_derived
                s = select([my_derived.c.distro_id,my_derived.c.install_name,my_derived.c.date_created],from_obj=my_derived) 
            else:
                try:
                    current_derived = current_derived.join(my_derived,current_derived.c.name == my_derived.c.name)
                except AttributeError:
                    current_derived = current_derived.join(my_derived,first_derived.c.name == my_derived.c.name)
            future_arch_cache[local_arch] = {} 
     
        s = current_derived.select(use_labels=True)     
        result = s.execute() 
        #The following dict should look something like this (for example only)
        #
        #{ 'i386' => { 'RHEL5.5-Server-20100318.nightly_nfs' : [125,date_create],
        #              'RHEL5.5-Server-20100315.nightly_nfs' : [128,date_create] },
        #  'x86_64' => { 'RHEL5.5-Server-20100318.nightly_nfs' : 126,
        #                'RHEL5.5-Server-20100315.nightly_nfs' : 127},
        #}
        #        
        for res in result:
            for arch in local_arches:
                cacheable_distro_install_name = res[current_derived.c['%s_install_name' % arch]]
                if not  future_arch_cache[arch].get(cacheable_distro_install_name):#below we remove the arch from the end of the distro isntall_name, it's redundant
                    future_arch_cache[arch][re.sub(r'^(.+)\-(.+?)$',r'\1',cacheable_distro_install_name)]  \
                        =  [res[current_derived.c['%s_distro_id' % arch]],res[current_derived.c['%s_date_created' % arch]]]
                else:
                    continue

        if future_arch_cache:
            setattr(Distro,cache_location,future_arch_cache)
        return getattr(Distro,cache_location,None)

    @classmethod
    def multiple_systems_distro(self,*args,**kw):
        _date_created_index = 1
        _install_name_index = 0
        arch_distro_map = self._create_arch_distro_map(**kw)
        
        try: 
            arch_results = [[]] * len(arch_distro_map.keys()) #creates our initial 2D array
        except AttributeError: #hmm, perhaps we don't have an arch_distros_map
            log.debug('We have no entries for mutiple system distros')
            return []
       
        for index,(arch,distro_ref) in enumerate(arch_distro_map.iteritems()): 
            #sort it
            arch_results[index] = sorted(distro_ref.keys(), 
                                        lambda a,b: distro_ref[a][_date_created_index] > distro_ref[b][_date_created_index] and -1 or 1 ) 
            if index > 0:
                if arch_results[index-1] != arch_results[index]: #just a sanity check
                    log.error('Not all arches have the same distros')
        try:
            results_to_return = arch_results.pop()
            return results_to_return
        except IndexError,e:
            return []

    def systems(self, user=None): 
        """
        List of systems that support this distro
        Limit to only lab controllers which have the distro.
        Limit to what is available to user if user passed in.
        """
        return self.all_systems(user, join=['lab_controller','_distros','distro']).filter( \
                    Distro.install_name==self.install_name)

    def all_systems(self, user=None, join=['lab_controller']):
        """
        List of systems that support this distro
        Will return all possible systems even if the distro is not on the lab controller yet.
        Limit to what is available to user if user passed in.
        """
        if user:
            systems = System.available_order(user)
        else:
            systems = System.query()
        
        return systems.join(join).filter(
             and_(
                  System.arch.contains(self.arch),
                not_(or_(System.id.in_(select([system_table.c.id]).
                  where(system_table.c.id==system_arch_map.c.system_id).
                  where(arch_table.c.id==system_arch_map.c.arch_id).
                  where(system_table.c.id==exclude_osmajor_table.c.system_id).
                  where(arch_table.c.id==exclude_osmajor_table.c.arch_id).
                  where(ExcludeOSMajor.osmajor==self.osversion.osmajor).
                  where(ExcludeOSMajor.arch==self.arch)
                                      ),
                         System.id.in_(select([system_table.c.id]).
                  where(system_table.c.id==system_arch_map.c.system_id).
                  where(arch_table.c.id==system_arch_map.c.arch_id).
                  where(system_table.c.id==exclude_osversion_table.c.system_id).
                  where(arch_table.c.id==exclude_osversion_table.c.arch_id).
                  where(ExcludeOSVersion.osversion==self.osversion).
                  where(ExcludeOSVersion.arch==self.arch)
                                      )
                        )
                    )
                 )
        )

    def link(self):
        """ Returns a hyper link to this distro
        """ 
        return make_link(url = '/distros/view?id=%s' % self.id,
                         text = self.install_name)

    link = property(link)

    def __repr__(self):
        return "%s" % self.name

    lab_controllers = association_proxy('lab_controller_assocs', 'lab_controller')


class DistroTag(object):
    def __init__(self, tag=None):
        self.tag = tag

    def __repr__(self):
        return "%s" % self.tag

    @classmethod
    def by_tag(cls, tag):
        """
        A class method to lookup tags
        """
        return cls.query().filter(DistroTag.tag == tag).one()

    @classmethod
    def list_by_tag(cls, tag):
        """
        A class method that can be used to search tags
        """
        return cls.query().filter(DistroTag.tag.like('%s%%' % tag))

class Admin(object):
    def __init__(self,system_id,group_id):
        self.system_id = system_id
        self.group_id = group_id

# Activity model
class Activity(object):
    def __init__(self, user=None, service=None, action=None,
                 field_name=None, old_value=None, new_value=None):
        self.user = user
        self.service = service
        self.field_name = field_name
        self.action = action
        # These values are likely to be truncated by MySQL, so let's make sure 
        # we don't end up with invalid UTF-8 chars at the end
        if old_value and isinstance(old_value, unicode):
            old_value = unicode_truncate(old_value,
                bytes_length=self.c.old_value.type.length)
        if new_value and isinstance(new_value, unicode):
            new_value = unicode_truncate(new_value,
                bytes_length=self.c.new_value.type.length)
        self.old_value = old_value
        self.new_value = new_value

    @classmethod
    def all(cls):
        return cls.query()

    def object_name(self):
        return None


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
        return "Distro: %s" % self.object.install_name


# note model
class Note(object):
    def __init__(self, user=None, text=None):
        self.user = user
        self.text = text

    @classmethod
    def all(cls):
        return cls.query()


class Key(SystemObject):
    @classmethod
    def get_all_keys(cls):
       all_keys = cls.query()     
       return [key.key_name for key in all_keys]

    @classmethod
    def by_name(cls, key_name):
        return cls.query().filter_by(key_name=key_name).one()


    @classmethod
    def list_by_name(cls, name, find_anywhere=False):
        """
        A class method that can be used to search keys
        based on the key_name
        """
        if find_anywhere:
            q = cls.query().filter(Key.key_name.like('%%%s%%' % name))
        else:
            q = cls.query().filter(Key.key_name.like('%s%%' % name))
        return q

    @classmethod
    def by_id(cls, id):
        return cls.query().filter_by(id=id).one()

    def __init__(self, key_name=None, numeric=False):
        self.key_name = key_name
        self.numeric = numeric

    def __repr__(self):
        return "%s" % self.key_name


# key_value model
class Key_Value_String(object):

    key_type = 'string'

    def __init__(self, key, key_value, system=None):
        self.system = system
        self.key = key
        self.key_value = key_value

    def __repr__(self):
        return "%s %s" % (self.key, self.key_value)

    @classmethod
    def by_key_value(cls, system, key, value):
        return cls.query().filter(and_(Key_Value_String.key==key, 
                                  Key_Value_String.key_value==value,
                                  Key_Value_String.system==system)).one()


class Key_Value_Int(object):

    key_type = 'int'

    def __init__(self, key, key_value, system=None):
        self.system = system
        self.key = key
        self.key_value = key_value

    def __repr__(self):
        return "%s %s" % (self.key, self.key_value)

    @classmethod
    def by_key_value(cls, system, key, value):
        return cls.query().filter(and_(Key_Value_Int.key==key, 
                                  Key_Value_Int.key_value==value,
                                  Key_Value_Int.system==system)).one()



class TaskPriority(object):   

    @classmethod
    def default_priority(cls):
        return cls.query().filter_by(id=3).one()

    @classmethod
    def by_id(cls,id):
      return cls.query().filter_by(id=id).one()

class TaskStatus(object):

    @classmethod
    def max(cls):
        return cls.query().order_by(TaskStatus.severity.desc()).first()

    @classmethod
    @cache
    def by_name(cls, status_name):
        return cls.query().filter_by(status=status_name).one()

    @classmethod
    def get_all(cls):
        return [(0,"All")] + [(status.id, status.status) for status in cls.query()]

    @classmethod
    def get_all_status(cls):
        all = cls.query()
        return [elem.status for elem in all]

    def __cmp__(self, other):
        if hasattr(other,'severity'):
            other = other.severity
        if self.severity < other:
            return -1
        if self.severity == other:
            return 0
        if self.severity > other:
            return 1

    def __repr__(self):
        return "%s" % (self.status)


class TaskResult(object):
    @classmethod
    @cache
    def by_name(cls, result_name):
        return cls.query().filter_by(result=result_name).one()

    @classmethod
    def get_results(cls):
        return [(result.id,result.result) for result in cls.query()] 

    @classmethod
    def get_all(cls):
        return [(0,"All")] + [(result.id, result.result) for result in cls.query()]

    @classmethod
    def get_all_results(cls):
        return [elem.result for elem in cls.query()]

    def __cmp__(self, other):
        if hasattr(other,'severity'):
            other = other.severity
        if self.severity < other:
            return -1
        if self.severity == other:
            return 0
        if self.severity > other:
            return 1

    def __repr__(self):
        return "%s" % (self.result)

class Log(MappedObject):

    MAX_ENTRIES_PER_DIRECTORY = 100

    def __init__(self, path=None, filename=None, server=None, basepath=None):
        self.path = path
        self.filename = filename
        self.server = server
        self.basepath = basepath

    def result(self):
        return self.parent.result

    result = property(result)

    def link(self):
        """ Return a link to this Log
        """
        text = "%s/%s" % (self.path != '/' and self.path or '', self.filename)
        text = text[-50:]
        # if server is defined then the logs are stored elsewhere.
        if self.server:
            url = '%s/%s/%s' % (self.server, self.path, self.filename)
        else:
            url = '/logs/%s/%s/%s' % (self.parent.filepath,
                                                   self.path, 
                                                   self.filename)
        return make_link(url = url,
                         text = text)
    link = property(link)

    @property
    def dict(self):
        """ Return a dict describing this log
        """
        return dict(server   = self.server,
                    path     = self.path,
                    filename = self.filename,
                    tid      = '%s:%s' % (self.type, self.id),
                    filepath = self.parent.filepath,
                    basepath = self.basepath,
                   )

    @classmethod 
    def by_id(cls,id): 
       return cls.query().filter_by(id=id).one()

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

    def is_finished(self):
        """
        Simply state if the task is finished or not
        """
        if self.status in [TaskStatus.by_name(u'Completed'),
                           TaskStatus.by_name(u'Cancelled'),
                           TaskStatus.by_name(u'Aborted')]:
            return True
        else:
            return False

    def is_queued(self):
        """
        State if the task is queued
        """ 
        if self.status in [TaskStatus.by_name(u'New'),
                           TaskStatus.by_name(u'Processed'),
                           TaskStatus.by_name(u'Queued'),
                           TaskStatus.by_name(u'Scheduled')]:
            return True
        else:
            return False 

           
        

    def is_failed(self):
        """ 
        Return True if the task has failed
        """
        if self.result in [TaskResult.by_name(u'Warn'),
                           TaskResult.by_name(u'Fail'),
                           TaskResult.by_name(u'Panic')]:
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
        div.tail = "%s%%" % percentCompleted
        return div
    progress_bar = property(progress_bar)
    
    @property
    def action_link(self):
        """
        Return action links depending on status
        """
        div = Element('div')
        div.append(make_link(url = self.clone_link(),
                        text = "Clone"))
        if not self.is_finished():
            div.append(Element('br'))
            div.append(make_link(url = self.cancel_link(),
                            text = "Cancel"))
        return div

    def access_rights(self,user):
        if not user:
            return
        try:
            if self.owner == user or (user.in_group(['admin','queue_admin'])):
                return True
        except:
            return

class Job(TaskBase):
    """
    Container to hold like recipe sets.
    """

    stop_types = ['abort','cancel']

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
    def by_whiteboard(cls,desc):
        res = Job.query().filter_by(whiteboard = desc)
        return res

    @classmethod
    def provision_system_job(cls, distro_id, **kw):
        """ Create a new reserve job, if system_id is defined schedule it too """
        job = Job(ttasks=0, owner=identity.current.user, retention_tag=RetentionTag.get_default())
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard') 
        if not isinstance(distro_id,list):
            distro_id = [distro_id]

        for id in distro_id: 
            try:
                distro = Distro.by_id(id)
            except InvalidRequestError:
                raise BX(u'Invalid Distro ID %s' % id)
            recipeSet = RecipeSet(ttasks=2)
            recipe = MachineRecipe(ttasks=2)
            # Inlcude the XML definition so that cloning this job will act as expected.
            recipe.distro_requires = distro.to_xml().toxml()
            recipe.distro = distro
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
        session.save(job)
        session.flush()
        return job

    def requires_product(self):
        return self.retention_tag.requires_product()

    def delete(self,dryrun, *args, **kw):
        paths = []
        errors = []
        for rs in self.recipesets:
            paths_to_del, new_errors = rs.delete(dryrun)
            paths.extend(paths_to_del)
            errors.extend(new_errors)
        return paths, errors

    def clone_link(self):
        """ return link to clone this job
        """
        return "/jobs/clone?job_id=%s" % self.id

    def cancel_link(self):
        """ return link to cancel this job
        """
        return "/jobs/cancel?id=%s" % self.id

    def priority_settings(self, prefix, colspan='1'):
        span = Element('span')
        title = Element('td')
        title.attrib['class']='title' 
        title.text = "Set all RecipeSet priorities"        
        content = Element('td')
        content.attrib['colspan'] = colspan
        priorities = TaskPriority.query().all()
        for p in priorities:
            id = '%s%s' % (prefix, self.id)
            a_href = make_fake_link(unicode(p.id), id, p.priority)
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
        tags = RetentionTag.query().all()
        for t in tags:
            id = '%s%s' % (u'retentiontag_job_', self.id)
            a_href = make_fake_link(unicode(t.id), id, t.tag)
            content.append(a_href)
        span.append(title)
        span.append(content)
        return span

    def _create_job_elem(self,clone=False, *args, **kw):
        job = self.doc.createElement("job")
        if not clone:
            job.setAttribute("id", "%s" % self.id)
            job.setAttribute("owner", "%s" % self.owner.email_address)
            job.setAttribute("result", "%s" % self.result)
            job.setAttribute("status", "%s" % self.status)
        if self.cc:
            notify = self.doc.createElement('notify')
            for email_address in self.cc:
                notify.appendChild(self.node('cc', email_address))
            job.appendChild(notify)
        job.setAttribute("retention_tag", "%s" % self.retention_tag.tag)
        if self.product:
            job.setAttribute("product", "%s" % self.product.name)
        job.appendChild(self.node("whiteboard", self.whiteboard or ''))
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
                    state           = self.status.id,
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
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = None
        min_status = TaskStatus.max()
        for recipeset in self.recipesets:
            recipeset._update_status()
            self.ptasks += recipeset.ptasks
            self.wtasks += recipeset.wtasks
            self.ftasks += recipeset.ftasks
            self.ktasks += recipeset.ktasks
            if recipeset.status < min_status:
                min_status = recipeset.status
            if recipeset.result > max_result:
                max_result = recipeset.result
        self.status = min_status
        self.result = max_result
        if self.is_finished():
            # Send email notification
            mail.job_notify(self)

    def t_id(self):
        return "J:%s" % self.id
    t_id = property(t_id)

    def can_admin(self, user=None):
        """Returns True iff the given user can administer this Job."""
        return bool(user) and (self.owner == user or user.is_admin())

    cc = association_proxy('_job_ccs', 'email_address')

class JobCc(MappedObject):

    def __init__(self, email_address):
        self.email_address = email_address


class Product(object):

    def __init__(self, name):
        self.name = name

    @classmethod
    def by_id(cls, id):
        return cls.query().filter(cls.id == id).one()

    @classmethod
    @cache
    def by_name(cls, name):
        return cls.query().filter(cls.name == name).one()

class BeakerTag(object):

    def __init__(self, tag, *args, **kw):
        self.tag = tag

    @classmethod
    def by_id(cls, id, *args, **kw):
        return cls.query().filter(cls.id==id).one()

    @classmethod
    def by_tag(cls, tag, *args, **kw):
        return cls.query().filter(cls.tag==tag).one()

    @classmethod
    def get_all(cls, *args, **kw):
        return cls.query()


class RetentionTag(BeakerTag):

    def __init__(self, tag, is_default=False, needs_product=False, *args, **kw):
        self.needs_product = needs_product
        self.set_default_val(is_default)
        super(RetentionTag, self).__init__(tag, **kw)
        session.flush()

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
        return cls.query().filter(cls.is_default==True).one()

    @classmethod
    def list_by_requires_product(cls, requires=True, *args, **kw):
        return cls.query().filter(cls.needs_product == requires).all()

    @classmethod
    def list_by_tag(cls, tag, anywhere=True, *args, **kw):
        if anywhere is True:
            q = cls.query().filter(cls.tag.like('%%%s%%' % tag))
        else:
            q = cls.query().filter(cls.tag.like('%s%%' % tag))
        return q 
        
    def __repr__(self, *args, **kw):
        return self.tag

class Response(MappedObject):

    @classmethod
    def get_all(cls,*args,**kw):
        return cls.query()

    @classmethod
    def by_response(cls,response,*args,**kw):
        return cls.query().filter_by(response = response).one()

    def __repr__(self):
        return self.response

class RecipeSetResponse(MappedObject):
    """
    An acknowledgment of a RecipeSet's results. Can be used for filtering reports
    """
    
    def __init__(self,type=None,response_id=None,comment=None):
        if response_id is not None:
            res = Response.by_id(response_id)
        elif type is not None:
            res = Response.by_response(type)
        self.response = res
        self.comment = comment

    @classmethod 
    def by_id(cls,id): 
       return cls.query().filter_by(recipe_set_id=id).one()

    @classmethod
    def by_jobs(cls,job_ids):
        try:
            job_ids_type = type(job_ids)
            if job_ids_type == type(list()):
                clause = Job.id.in_(job_ids)
            elif job_ids_type == int:
                clause = Job.id == job_id
            else:
                raise BeakerException('job_ids needs to be either type \'int\' or \'list\'. Found %s' % job_ids_type)
            queri = cls.query().outerjoin(['recipesets','job']).filter(clause)
            results = {}
            for elem in queri:
                results[elem.recipe_set_id] = elem.comment
            return results
     
        except: raise

class RecipeSet(TaskBase):
    """
    A Collection of Recipes that must be executed at the same time.
    """

    def __init__(self, ttasks=0, priority=None):
        self.ttasks = ttasks
        self.priority = priority

    stop_types = ['abort','cancel']
    def is_owner(self,user):
        if self.job.owner == user:
            return True
        return False

    def to_xml(self, clone=False, from_job=True, *args, **kw):
        recipeSet = self.doc.createElement("recipeSet")
        return_node = recipeSet 

        if not clone:
            response = self.get_response()
            if response:
                recipeSet.setAttribute('response','%s' % str(response))

        if not clone:
            recipeSet.setAttribute("id", "%s" % self.id)

        for r in self.recipes:
            if not isinstance(r,GuestRecipe):
                recipeSet.appendChild(r.to_xml(clone, from_recipeset=True))
        if not from_job:
            job = self.job._create_job_elem(clone)
            job.appendChild(recipeSet)
            return_node = job
        return return_node

    def delete(self, dryrun, *args, **kw):
        errors = []
        paths = []
        def _del_recipes():
            for r in self.recipes:
                try:
                    recipe_to_del = Recipe.by_id(r.id)
                    new_path = recipe_to_del.delete(dryrun)
                    if new_path is not None:
                        paths.append(new_path)
                except Exception,  e:
                   errors.append('%s:  %s' % (self.t_id,unicode(e)))

        if self.deleted is not None:
            return paths,errors

        if not dryrun:
            session.begin()
            try:
                _del_recipes()
                if len(errors) == 0:
                    self.deleted = datetime.utcnow()
                    session.commit()
                else:
                    session.rollback()
            except:
                session.rollback()
        else:
            _del_recipes()

        return paths,errors

    @classmethod
    def allowed_priorities_initial(cls,user):
        if not user:
            return
        if user.in_group(['admin','queue_admin']):
            return TaskPriority.query().all()
        default_id = TaskPriority.default_priority().id
        return TaskPriority.query().filter(TaskPriority.id < default_id)
        
    @classmethod
    def by_status(cls, status, query=None):
        if not query:
            query=cls.query
        return query.join('status').filter(Status.status==status)

    @classmethod
    def by_tag(cls, tag, query=None):
        if query is None:
            query = cls.query()
        if type(tag) is list:
            tag_query = cls.retention_tag_id.in_([RetentionTag.by_tag(unicode(t)).id for t in tag])
        else:
            tag_query = cls.retention_tag==RetentionTag.by_tag(unicode(tag))
        
        return query.filter(tag_query)

    @classmethod
    def by_product(cls, product, query=None):
        if query is None:
            query=cls.query()
        return query.join('product').filter(Product.name==product)

    @classmethod
    def has_family(cls,family,query=None, **kw):
        if query is None:
            query = cls.query()
        query = query.join(['recipes','distro','osversion','osmajor']).filter(OSMajor.osmajor == family).reset_joinpoint()
        return query

    @classmethod
    def complete_delta(cls,delta):
        delta = timedelta(**delta)
        query = cls.query().join('recipes').filter(and_(Recipe.finish_time < datetime.utcnow() - delta,
            cls.status_id.in_(TaskStatus.by_name(u'Completed').id,TaskStatus.by_name(u'Aborted').id,TaskStatus.by_name(u'Cancelled').id)))
        return query

    @classmethod
    def by_datestamp(cls, datestamp, query=None):
        if not query:
            query=cls.query
        return query.filter(RecipeSet.queue_time <= datestamp)

    @classmethod 
    def by_id(cls,id): 
       return cls.query().filter_by(id=id).one()

    @classmethod
    def by_job_id(cls,job_id):
        try:
            queri = RecipeSet.query().outerjoin(['job']).filter(Job.id == job_id)
            return queri
        except: raise 
     
    @classmethod
    def iter_recipeSets(self, status=u'Assigned'):
        self.recipeSets = []
        while True:
            recipeSet = RecipeSet.by_status(status).join('priority')\
                            .order_by(priority.c.priority)\
                            .filter(not_(RecipeSet.id.in_(self.recipeSets)))\
                            .first()
            if recipeSet:
                self.recipeSets.append(recipeSet.id)
            else:
                return
            yield recipeSet

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
        self.status = TaskStatus.by_name(u'Cancelled')
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
        self.status = TaskStatus.by_name(u'Aborted')
        for recipe in self.recipes:
            recipe._abort(msg)

    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.job.update_status()

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = None
        min_status = TaskStatus.max()
        for recipe in self.recipes:
            recipe._update_status()
            self.ptasks += recipe.ptasks
            self.wtasks += recipe.wtasks
            self.ftasks += recipe.ftasks
            self.ktasks += recipe.ktasks
            if recipe.status < min_status:
                min_status = recipe.status
            if recipe.result > max_result:
                max_result = recipe.result
        self.status = min_status
        self.result = max_result

        # Return systems if recipeSet finished
        if self.is_finished():
            for recipe in self.recipes:
                recipe.release_system()

    def recipes_orderby(self, labcontroller):
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
        return map(lambda x: Recipe.query().filter_by(id=x[0]).first(), session.connection(RecipeSet).execute(query).fetchall())

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
                    state           = self.status.id,
                    method          = None,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
                    #subtask_id_list = ["R:%s" % r.id for r in self.recipes]
                   )

    def t_id(self):
        return "RS:%s" % self.id
    t_id = property(t_id)
 
    def allowed_priorities(self,user):
        if not user:
            return [] 
        if user.in_group(['admin','queue_admin']):
            return TaskPriority.query().all()
        elif user == self.job.owner: 
            return TaskPriority.query.filter(TaskPriority.id <= self.priority.id)

    @property
    def action_link(self):
        """
        Return action links depending on status
        """
        div = Element('div')
        div.append(make_link(url = self.clone_link(),
                        text = "Clone"))
        return div

    def clone_link(self):
        """ return link to clone this recipe
        """
        return "/jobs/clone?recipeset_id=%s" % self.id


class Recipe(TaskBase):
    """
    Contains requires for host selection and distro selection.
    Also contains what tasks will be executed.
    """
    stop_types = ['abort','cancel']
    servername = get("servername",socket.gethostname())
    logspath = get("basepath.logs", "/var/www/beaker/logs")
    harnesspath = get("basepath.harness", "/var/www/beaker/harness")
    rpmspath = get("basepath.rpms", "/var/www/beaker/rpms")
    repopath = get("basepath.repos", "/var/www/beaker/repos")

    def clone_link(self):
        """ return link to clone this recipe
        """
        return "/jobs/clone?recipe_id=%s" % self.id

    def cancel_link(self):
        """ return link to cancel this recipe
        """
        return "/recipes/cancel?id=%s" % self.id

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

    def delete(self, dryrun, *args, **kw):
        """
        How we delete a Recipe.
        At the moment only unlinking log files and deleting log table rows
        """
        full_recipe_logpath = '%s/%s' % (self.logspath, self.filepath)
        if dryrun is True:
            if not (os.access(full_recipe_logpath,os.R_OK)): #See if it exists
                return None
            elif not (os.access(full_recipe_logpath,os.W_OK)): #See if we can write it
                raise BX(_(u'Incorrect perms to delete %s:' % full_recipe_logpath))
            else:
                return full_recipe_logpath #success
        else:
            try:
                shutil.rmtree(full_recipe_logpath)
                return_val = full_recipe_logpath
            except OSError, e:
                if e.errno == errno.ENOENT: #File/Dir does not exist
                    pass #Maybe the logs don't exist?? Carry on...
                    return_val = None
                elif e.errno == errno.EACCES: #Incorrect perms
                    raise BX(_(u'Incorrect perms to delete %s:' % full_recipe_logpath))
                else:
                    raise BX(_(u'Received unexpected error: %s' % e.errstr))

            self.logs = []

            for task in self.tasks:
                task_to_delete = RecipeTask.by_id(task.id)
                task_to_delete.delete()
            return return_val

    def harness_repos(self):
        """
        return repos needed for harness and task install
        """
        repos = []
        if self.distro:
            if os.path.exists("%s/%s/%s" % (self.harnesspath,
                                            self.distro.osversion.osmajor,
                                            self.distro.arch)):
                repo = dict(name = "beaker-harness",
                             url  = "http://%s/harness/%s/%s" % (self.servername,
                                                                      self.distro.osversion.osmajor,
                                                                      self.distro.arch))
                repos.append(repo)
            repo = dict(name = "beaker-tasks",
                        url  = "http://%s/repos/%s" % (self.servername, self.id))
            repos.append(repo)
        return repos

    def to_xml(self, recipe, clone=False, from_recipeset=False, from_machine=False):
        if not clone:
            recipe.setAttribute("id", "%s" % self.id)
            recipe.setAttribute("job_id", "%s" % self.recipeset.job_id)
            recipe.setAttribute("recipe_set_id", "%s" % self.recipe_set_id)
        autopick = self.doc.createElement("autopick")
        autopick.setAttribute("random", "%s" % unicode(self.autopick_random).lower())
        recipe.appendChild(autopick)
        recipe.setAttribute("whiteboard", "%s" % self.whiteboard and self.whiteboard or '')
        recipe.setAttribute("role", "%s" % self.role and self.role or 'RECIPE_MEMBERS')
        if self.kickstart:
            kickstart = self.doc.createElement("kickstart")
            text = self.doc.createCDATASection('%s' % self.kickstart)
            kickstart.appendChild(text)
            recipe.appendChild(kickstart)
        recipe.setAttribute("ks_meta", "%s" % self.ks_meta and self.ks_meta or '')
        recipe.setAttribute("kernel_options", "%s" % self.kernel_options and self.kernel_options or '')
        recipe.setAttribute("kernel_options_post", "%s" % self.kernel_options_post and self.kernel_options_post or '')
        if self.duration and not clone:
            recipe.setAttribute("duration", "%s" % self.duration)
        if self.result and not clone:
            recipe.setAttribute("result", "%s" % self.result)
        if self.status and not clone:
            recipe.setAttribute("status", "%s" % self.status)
        if self.distro and not clone:
            recipe.setAttribute("distro", "%s" % self.distro.name)
            recipe.setAttribute("install_name", "%s" % self.distro.install_name)
            recipe.setAttribute("arch", "%s" % self.distro.arch)
            recipe.setAttribute("family", "%s" % self.distro.osversion.osmajor)
            recipe.setAttribute("variant", "%s" % self.distro.variant)
        watchdog = self.doc.createElement("watchdog")
        if self.panic:
            watchdog.setAttribute("panic", "%s" % self.panic)
        recipe.appendChild(watchdog)
        if self.system and not clone:
            recipe.setAttribute("system", "%s" % self.system)
        packages = self.doc.createElement("packages")
        if self.custom_packages:
            for package in self.custom_packages:
                packages.appendChild(package.to_xml())
        recipe.appendChild(packages)

        ks_appends = self.doc.createElement("ks_appends")
        if self.ks_appends:
            for ks_append in self.ks_appends:
                ks_appends.appendChild(ks_append.to_xml())
        recipe.appendChild(ks_appends)
            
        if self.roles and not clone:
            roles = self.doc.createElement("roles")
            for role in self.roles.to_xml():
                roles.appendChild(role)
            recipe.appendChild(roles)
        repos = self.doc.createElement("repos")
        for repo in self.repos:
            repos.appendChild(repo.to_xml())
        recipe.appendChild(repos)
        drs = xml.dom.minidom.parseString(self.distro_requires)
        hrs = xml.dom.minidom.parseString(self.host_requires)
        for dr in drs.getElementsByTagName("distroRequires"):
            recipe.appendChild(dr)
        hostRequires = self.doc.createElement("hostRequires")
        for hr in hrs.getElementsByTagName("hostRequires"):
            for child in hr.childNodes:
                hostRequires.appendChild(child)
        recipe.appendChild(hostRequires)
        prs = xml.dom.minidom.parseString(self.partitions)
        partitions = self.doc.createElement("partitions")
        for pr in prs.getElementsByTagName("partitions"):
            for child in pr.childNodes:
                partitions.appendChild(child)
        recipe.appendChild(partitions)
        for t in self.tasks:
            recipe.appendChild(t.to_xml(clone))
        if not from_recipeset and not from_machine:
            recipeSet = self.doc.createElement("recipeSet")
            recipeSet.appendChild(recipe)
            job = self.doc.createElement("job")
            if not clone:
                job.setAttribute("owner", "%s" % self.recipeset.job.owner.email_address)
            job.appendChild(self.node("whiteboard", self.recipeset.job.whiteboard or ''))
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
        for task in self.tasks:
            packages.extend(task.task.required)
        packages.extend(self.custom_packages)
        return packages

    packages = property(_get_packages)

    def _get_arch(self):
        if self.distro:
            return self.distro.arch

    arch = property(_get_arch)

    def _get_host_requires(self):
        # If no system_type is specified then add defaults
        try:
            hrs = xml.dom.minidom.parseString(self._host_requires)
        except TypeError:
            hrs = self.doc.createElement("hostRequires")
        except xml.parsers.expat.ExpatError:
            hrs = self.doc.createElement("hostRequires")
        if not hrs.getElementsByTagName("system_type"):
            hostRequires = self.doc.createElement("hostRequires")
            for hr in hrs.getElementsByTagName("hostRequires"):
                for child in hr.childNodes[:]:
                    hostRequires.appendChild(child)
            system_type = self.doc.createElement("system_type")
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
            prs = self.doc.createElement("partitions")
        except xml.parsers.expat.ExpatError:
            prs = self.doc.createElement("partitions")
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
            prs = self.doc.createElement("partitions")
        except xml.parsers.expat.ExpatError:
            prs = self.doc.createElement("partitions")
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
               recipe_table.c.status_id==TaskStatus.by_name(u'Processed').id)),
          status_id=TaskStatus.by_name(u'Queued').id).rowcount == 1:
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
               recipe_table.c.status_id==TaskStatus.by_name(u'New').id)),
          status_id=TaskStatus.by_name(u'Processed').id).rowcount == 1:
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

    def createRepo(self):
        """
        Create Recipe specific task repo based on the tasks requested.
        """
        directory = '%s/%s' % (self.repopath, self.id)
        try:
            os.makedirs(directory)
        except OSError:
            #thrown when dir already exists (could happen in a race)
            if not os.path.isdir(directory):
                #something else must have gone wrong
                raise
        if not os.path.isdir('%s/repodata' % (directory)):
            cwd = os.getcwd()
            os.chdir(self.rpmspath)
            # update base repo, specifying -o and baseurl allow us to copy the repo and have it
            # still reference the rpms in another directory.
            os.system("createrepo -q --update -o . --baseurl http://%s/rpms ." % (self.servername))
            # Copy updated repo to recipe specific repo
            shutil.copytree('%s/repodata' % (self.rpmspath), '%s/repodata' % (directory))
            os.chdir(cwd)
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
               recipe_table.c.status_id==TaskStatus.by_name(u'Queued').id)),
          status_id=TaskStatus.by_name(u'Scheduled').id).rowcount == 1:
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
               recipe_table.c.status_id==TaskStatus.by_name(u'Scheduled').id)),
          status_id=TaskStatus.by_name(u'Waiting').id).rowcount == 1:
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
        self.status = TaskStatus.by_name(u'Cancelled')
        for task in self.tasks:
            task._cancel(msg)

    def abort(self, msg=None):
        """
        Method to abort all tasks in this recipe.
        """
        self._abort(msg)
        self.update_status()
        session.flush() # XXX bad
        if self.system is not None and \
                get('beaker.reliable_distro_tag', None) in self.distro.tags:
            self.system.suspicious_abort()

    def _abort(self, msg=None):
        """
        Method to abort all tasks in this recipe.
        """
        self.status = TaskStatus.by_name(u'Aborted')
        for task in self.tasks:
            task._abort(msg)

    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.recipeset.job.update_status()

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        task_pass = TaskResult.by_name(u'Pass')
        self.wtasks = 0
        task_warn = TaskResult.by_name(u'Warn')
        self.ftasks = 0
        task_fail = TaskResult.by_name(u'Fail')
        self.ktasks = 0
        task_panic = TaskResult.by_name(u'Panic')

        max_result = None
        min_status = TaskStatus.max()
        for task in self.tasks:
            task._update_status()
            if task.is_finished():
                if task.result == task_pass:
                    self.ptasks += 1
                if task.result == task_warn:
                    self.wtasks += 1
                if task.result == task_fail:
                    self.ftasks += 1
                if task.result == task_panic:
                    self.ktasks += 1
            if task.status < min_status:
                min_status = task.status
            if task.result > max_result:
                max_result = task.result
        self.status = min_status
        self.result = max_result

        # Record the start of this Recipe.
        if not self.start_time \
           and self.status == TaskStatus.by_name(u'Running'):
            self.start_time = datetime.utcnow()

        if self.start_time and not self.finish_time and self.is_finished():
            # Record the completion of this Recipe.
            self.finish_time = datetime.utcnow()

    def release_system(self):
        """ Release the system and remove the watchdog
        """
        if self.system and self.watchdog:
            self.destroyRepo()
            ## FIXME Should we actually remove the watchdog?
            ##       Maybe we should set the status of the watchdog to reclaim
            ##       so that the lab controller returns the system instead.
            # Remove this recipes watchdog
            log.debug("Remove watchdog for recipe %s" % self.id)
            if self.watchdog.system == self.system:
                try:
                    self.system.action_release()
                    log.debug("Return system %s for recipe %s" % (self.system, self.id))
                    self.system.activity.append(
                        SystemActivity(self.recipeset.job.owner, 
                                       'Scheduler', 
                                       'Returned', 
                                       'User', 
                                       '%s' % self.recipeset.job.owner, 
                                       ''))
                except socket.gaierror, error:
                    #FIXME
                    pass
                except xmlrpclib.Fault, error:
                    #FIXME
                    pass
                except AttributeError, error:
                    pass
            del(self.watchdog)

    def task_info(self):
        """
        Method for exporting Recipe status for TaskWatcher
        """
        return dict(
                    id              = "R:%s" % self.id,
                    worker          = dict(name = "%s" % self.system),
                    state_label     = "%s" % self.status,
                    state           = self.status.id,
                    method          = "%s" % self.whiteboard,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
# Disable tasks status, TaskWatcher needs to do this differently.  its very resource intesive to make
# so many xmlrpc calls.
#                    subtask_id_list = ["T:%s" % t.id for t in self.tasks],
                   )

    def t_id(self):
        return "R:%s" % self.id
    t_id = property(t_id)

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
        for mylog in self.logs:
            yield mylog.dict
        for task in self.tasks:
            for mylog in task.logs:
                yield mylog.dict
            for result in task.results:
                for mylog in result.logs:
                    yield mylog.dict

    def is_task_applicable(self, task):
        """ Does the given task apply to this recipe?
            ie: not excluded for this distro family or arch.
        """
        if self.distro.arch in [arch.arch for arch in task.excluded_arch]:
            return False
        if self.distro.osversion.osmajor in [osmajor.osmajor for osmajor in task.excluded_osmajor]:
            return False
        return True

    @classmethod
    def mine(cls, owner):
        """
        A class method that can be used to search for Jobs that belong to a user
        """
        return cls.query.join(['recipeset','job','owner']).filter(Job.owner==owner)

    @property
    def action_link(self):
        """
        Return action links depending on status
        """
        div = Element('div')
        if not self.is_finished(): 
            div.append(make_link(url = self.cancel_link(),
                            text = "Cancel"))
            div.append(Element('br'))
        if self.system:
            a = Element('a', {'class': 'list'},
                    href=self.system.report_problem_href(recipe_id=self.id))
            a.text = _(u'Report problem with system')
            div.append(a)
            div.append(Element('br'))
        return div


class RecipeRoleListAdapter(object):
    def __init__(self, parent, role):
        self.__parent = parent
        self.__role = role

    def __cached(self):
        try:
            return self.__cached_systems
        except AttributeError:
            self.__cached_systems = [item.system for item in self.__parent._roles if item.role == self.__role]
            return self.__cached_systems
    __cached = property(__cached)

    def __delcached(self):
        try:
            del self.__cached_systems
        except AttributeError:
            pass

    def __iter__(self):
        return iter(self.__cached)

    def __eq__(self, other):
        return list(self) == list(other)

    def __repr__(self):
        return repr(list(self))

    def append(self, item):
        self.__delcached()
        self.__parent._roles.append(RecipeRole(self.__role, item))

    def __getitem__(self, index):
        return self.__cached[index]

    def __setitem__(self, index, value):
        self.__delcached()
        [item for item in self.__parent._roles if item.role == self.__role][index].roles = value
        self.__cached[index] = value


class RecipeRoleDictAdapterAttribute(object):
    def __get__(self, instance, owner):
        if instance is None:
            return self
        class RecipeRoleDictAdapter(MappedObject):
            def __getitem__(self, role):
                return RecipeRoleListAdapter(instance, role)
            def keys(self):
                return iter(set([item.role for item in instance._roles]))
            def __eq__(self, other):
                return dict(self) == dict(other)
            def __repr__(self):
                return repr(dict(self))
            def to_xml(self):
                """ For each key return an xml dom
                """
                for key in self.keys():
                    role = self.doc.createElement("role")
                    role.setAttribute("value", "%s" % key)
                    for s in RecipeRoleListAdapter(instance, key):
                        system = self.doc.createElement("system")
                        system.setAttribute("value", "%s" % s)
                        role.appendChild(system)
                    yield(role)

            # other dict like methods

        return RecipeRoleDictAdapter()

    def __set__(self, instance, somedict):
        l =[]
        for key, somelist in somedict.items():
            for item in somelist:
                l.append(RecipeRole(key, item))
                instance._roles = l


Recipe.roles = RecipeRoleDictAdapterAttribute()

class RecipeRole(MappedObject):
    """ Holds the roles for every Recipe
    """
    def __init__(self, role, system):
        self.role = role
        self.system = system

class GuestRecipe(Recipe):
    systemtype = 'Virtual'
    def to_xml(self, clone=False, from_recipeset=False, from_machine=False):
        recipe = self.doc.createElement("guestrecipe")
        recipe.setAttribute("guestname", "%s" % self.guestname)
        recipe.setAttribute("guestargs", "%s" % self.guestargs)
        if self.system and not clone:
            recipe.setAttribute("mac_address", "%s" % self.system.mac_address)
        if self.distro and self.system and not clone:
            location = LabControllerDistro.query().filter(
                            and_(
                               LabControllerDistro.distro == self.distro,
                               LabControllerDistro.lab_controller == self.system.lab_controller
                                )
                                                         ).first()
            if location:
                recipe.setAttribute("location", "%s" % location.tree_path)
        return Recipe.to_xml(self, recipe, clone, from_recipeset, from_machine)

    def _get_distro_requires(self):
        try:
            drs = xml.dom.minidom.parseString(self._distro_requires)
        except TypeError:
            drs = self.doc.createElement("distroRequires")
        except xml.parsers.expat.ExpatError:
            drs = self.doc.createElement("distroRequires")
        # If no distro_virt is asked for default to Virt
        if not drs.getElementsByTagName("distro_virt"):
            distroRequires = self.doc.createElement("distroRequires")
            for dr in drs.getElementsByTagName("distroRequires"):
                for child in dr.childNodes[:]:
                    distroRequires.appendChild(child)
            distro_virt = self.doc.createElement("distro_virt")
            distro_virt.setAttribute("op", "=")
            distro_virt.setAttribute("value", "")
            distroRequires.appendChild(distro_virt)
            return distroRequires.toxml()
        else:
            return drs.toxml()

    def _set_distro_requires(self, value):
        self._distro_requires = value

    distro_requires = property(_get_distro_requires, _set_distro_requires)

class MachineRecipe(Recipe):
    """
    Optionally can contain guest recipes which are just other recipes
      which will be executed on this system.
    """
    systemtype = 'Machine'
    def to_xml(self, clone=False, from_recipeset=False):
        recipe = self.doc.createElement("recipe")
        for guest in self.guests:
            recipe.appendChild(guest.to_xml(clone, from_machine=True))
        return Recipe.to_xml(self, recipe, clone, from_recipeset)

    def _get_distro_requires(self):
        drs = xml.dom.minidom.parseString(self._distro_requires)
        # If no distro_virt is asked for default to No Virt
        if not drs.getElementsByTagName("distro_virt"):
            distroRequires = self.doc.createElement("distroRequires")
            for dr in drs.getElementsByTagName("distroRequires"):
                for child in dr.childNodes[:]:
                    distroRequires.appendChild(child)
            distro_virt = self.doc.createElement("distro_virt")
            distro_virt.setAttribute("op", "=")
            distro_virt.setAttribute("value", "")
            distroRequires.appendChild(distro_virt)
            return distroRequires.toxml()
        else:
            return self._distro_requires

    def _set_distro_requires(self, value):
        self._distro_requires = value

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

    def to_xml(self, clone=False, *args, **kw):
        task = self.doc.createElement("task")
        task.setAttribute("name", "%s" % self.task.name)
        task.setAttribute("role", "%s" % self.role and self.role or 'STANDALONE')
        if not clone:
            task.setAttribute("id", "%s" % self.id)
            task.setAttribute("avg_time", "%s" % self.task.avg_time)
            task.setAttribute("result", "%s" % self.result)
            task.setAttribute("status", "%s" % self.status)
            rpm = self.doc.createElement("rpm")
            rpm.setAttribute("name", "%s" % self.task.rpm)
            rpm.setAttribute("path", "%s" % self.task.path)
            task.appendChild(rpm)
        if self.duration and not clone:
            task.setAttribute("duration", "%s" % self.duration)
        if self.roles and not clone:
            roles = self.doc.createElement("roles")
            for role in self.roles.to_xml():
                roles.appendChild(role)
            task.appendChild(roles)
        params = self.doc.createElement("params")
        for p in self.params:
            params.appendChild(p.to_xml())
        task.appendChild(params)
        if self.results and not clone:
            results = self.doc.createElement("results")
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

    def set_status(self, value):
        self._status = value


    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.recipe.recipeset.job.update_status()

    def _update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        max_result = None
        for result in self.results:
            if result.result > max_result:
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
        self.status = TaskStatus.by_name(u'Queued')

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
        self.status = TaskStatus.by_name(u'Processed')

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
        self.status = TaskStatus.by_name(u'Scheduled')

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
        self.status = TaskStatus.by_name(u'Waiting')

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
        self.status = TaskStatus.by_name(u'Running')

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
        self.status = TaskStatus.by_name(u'Completed')
        self.update_status()
        return True

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
        return self._abort_cancel(u'Cancelled', msg)

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
        return self._abort_cancel(u'Aborted', msg)
    
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
            self.status = TaskStatus.by_name(status)
            self.results.append(RecipeTaskResult(recipetask=self,
                                       path=u'/',
                                       result=TaskResult.by_name(u'Warn'),
                                       score=0,
                                       log=msg))
        return True

    def pass_(self, path, score, summary):
        """
        Record a pass result 
        """
        return self._result(u'Pass', path, score, summary)

    def fail(self, path, score, summary):
        """
        Record a fail result 
        """
        return self._result(u'Fail', path, score, summary)

    def warn(self, path, score, summary):
        """
        Record a warn result 
        """
        return self._result(u'Warn', path, score, summary)

    def panic(self, path, score, summary):
        """
        Record a panic result 
        """
        return self._result(u'Panic', path, score, summary)

    def _result(self, result, path, score, summary):
        """
        Record a result 
        """
        if not self.recipe.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.recipe.id))
        recipeTaskResult = RecipeTaskResult(recipetask=self,
                                   path=path,
                                   result=TaskResult.by_name(result),
                                   score=score,
                                   log=summary)
        self.results.append(recipeTaskResult)
        # Flush the result to the DB so we can return the id.
        session.save(recipeTaskResult)
        session.flush([recipeTaskResult])
        self.update_status()
        return recipeTaskResult.id

    def task_info(self):
        """
        Method for exporting Task status for TaskWatcher
        """
        return dict(
                    id              = "T:%s" % self.id,
                    worker          = dict(name = "%s" % self.recipe.system),
                    state_label     = "%s" % self.status,
                    state           = self.status.id,
                    method          = "%s" % self.task.name,
                    result          = "%s" % self.result,
                    is_finished     = self.is_finished(),
                    is_failed       = self.is_failed(),
                    #subtask_id_list = ["TR:%s" % tr.id for tr in self.results]
                   )

    def t_id(self):
        return "T:%s" % self.id
    t_id = property(t_id)

    def no_value(self):
        return None
   
    score = property(no_value)

class RecipeTaskRoleListAdapter(object):
    def __init__(self, parent, role):
        self.__parent = parent
        self.__role = role

    def __cached(self):
        try:
            return self.__cached_systems
        except AttributeError:
            self.__cached_systems = [item.system for item in self.__parent._roles if item.role == self.__role]
            return self.__cached_systems
    __cached = property(__cached)

    def __delcached(self):
        try:
            del self.__cached_systems
        except AttributeError:
            pass

    def __iter__(self):
        return iter(self.__cached)

    def __eq__(self, other):
        return list(self) == list(other)

    def __repr__(self):
        return repr(list(self))

    def append(self, item):
        self.__delcached()
        self.__parent._roles.append(RecipeTaskRole(self.__role, item))

    def __getitem__(self, index):
        return self.__cached[index]

    def __setitem__(self, index, value):
        self.__delcached()
        [item for item in self.__parent._roles if item.role == self.__role][index].roles = value
        self.__cached[index] = value


class RecipeTaskRoleDictAdapterAttribute(object):
    def __get__(self, instance, owner):
        if instance is None:
            return self
        class RecipeTaskRoleDictAdapter(MappedObject):
            def __getitem__(self, role):
                return RecipeTaskRoleListAdapter(instance, role)
            def keys(self):
                return iter(set([item.role for item in instance._roles]))
            def __eq__(self, other):
                return dict(self) == dict(other)
            def __repr__(self):
                return repr(dict(self))
            def to_xml(self):
                """ For each key return an xml dom
                """
                for key in self.keys():
                    role = self.doc.createElement("role")
                    role.setAttribute("value", "%s" % key)
                    for s in RecipeTaskRoleListAdapter(instance, key):
                        system = self.doc.createElement("system")
                        system.setAttribute("value", "%s" % s)
                        role.appendChild(system)
                    yield(role)

            # other dict like methods

        return RecipeTaskRoleDictAdapter()

    def __set__(self, instance, somedict):
        l =[]
        for key, somelist in somedict.items():
            for item in somelist:
                l.append(RecipeTaskRole(key, item))
                instance._roles = l


RecipeTask.roles = RecipeTaskRoleDictAdapterAttribute()

class RecipeTaskRole(MappedObject):
    """ Holds the roles for every task
    """
    def __init__(self, role, system):
        self.role = role
        self.system = system

class RecipeTaskParam(MappedObject):
    """
    Parameters for task execution.
    """
    def to_xml(self):
        param = self.doc.createElement("param")
        param.setAttribute("name", "%s" % self.name)
        param.setAttribute("value", "%s" % self.value)
        return param


class RecipeRepo(MappedObject):
    """
    Custom repos 
    """
    def to_xml(self):
        repo = self.doc.createElement("repo")
        repo.setAttribute("name", "%s" % self.name)
        repo.setAttribute("url", "%s" % self.url)
        return repo


class RecipeKSAppend(MappedObject):
    """
    Kickstart appends
    """
    def to_xml(self):
        ks_append = self.doc.createElement("ks_append")
        text = self.doc.createCDATASection('%s' % self.ks_append)
        ks_append.appendChild(text)
        return ks_append


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

    def to_xml(self):
        """
        Return result in xml
        """
        result = self.doc.createElement("result")
        result.setAttribute("id", "%s" % self.id)
        result.setAttribute("path", "%s" % self.path)
        result.setAttribute("result", "%s" % self.result)
        result.setAttribute("score", "%s" % self.score)
        result.appendChild(self.doc.createTextNode("%s" % self.log))
        #FIXME Append any binary logs as URI's
        return result

    def task_info(self):
        """
        Method for exporting RecipeTaskResult status for TaskWatcher
        """
        return dict(
                    id              = "TR:%s" % self.id,
                    worker          = dict(name = "%s" % None),
                    state_label     = "%s" % self.result,
                    state           = self.result.id,
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


class Task(MappedObject):
    """
    Tasks that are available to schedule
    """

    @classmethod
    @cache
    def by_name(cls, name):
        return cls.query.filter_by(name=name).one()

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

    def to_dict(self):
        """ return a dict of this object """
        return dict(id = self.id,
                    name = self.name,
                    rpm = self.rpm,
                    oldrpm = self.oldrpm,
                    path = self.path,
                    description = self.description,
                    repo = self.repo,
                    max_time = self.avg_time,
                    destructive = self.destructive,
                    nda = self.nda,
                    creation_date = '%s' % self.creation_date,
                    update_date = '%s' % self.update_date,
                    uploader = '%s' % self.owner,
                    version = self.version,
                    license = self.license,
                    valid = self.valid,
                    types = ['%s' % type.type for type in self.types],
                    excluded_osmajor = ['%s' % osmajor.osmajor for osmajor in self.excluded_osmajor],
                    excluded_arch = ['%s' % arch.arch for arch in self.excluded_arch],
                    runfor = ['%s' % package for package in self.runfor],
                    required = ['%s' % package for package in self.required],
                    bugzillas = ['%s' % bug.bugzilla_id for bug in self.bugzillas],
                   )

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
    @cache
    def by_name(cls, type):
        return cls.query.filter_by(type=type).one()


class TaskPackage(MappedObject):
    """
    A list of packages that a tasks should be run for.
    """

    @classmethod
    @cache
    def by_name(cls, package):
        return cls.query.filter_by(package=package).one()

    def __repr__(self):
        return self.package

    def to_xml(self):
        package = self.doc.createElement("package")
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

# set up mappers between identity tables and classes
SystemType.mapper = mapper(SystemType, system_type_table)
SystemStatus.mapper = mapper(SystemStatus, system_status_table)
mapper(ReleaseAction, release_action_table)
System.mapper = mapper(System, system_table,
                   properties = {
                     'status':relation(SystemStatus,uselist=False),
                     'devices':relation(Device,
                                        secondary=system_device_map,backref='systems'),
                     'type':relation(SystemType, uselist=False),
                    
                     'arch':relation(Arch,
                                     order_by=[arch_table.c.arch],
                                        secondary=system_arch_map,
                                        backref='systems'),
                     'watchdog':relation(Watchdog, uselist=False,
                                        backref='system'),
                     'labinfo':relation(LabInfo, uselist=False,
                                        backref='system'),
                     'cpu':relation(Cpu, uselist=False,backref='systems'),
                     'numa':relation(Numa, uselist=False, backref='system'),
                     'power':relation(Power, uselist=False,
                                         backref='system'),
                     'excluded_osmajor':relation(ExcludeOSMajor,
                                                 backref='system'),
                     'excluded_osversion':relation(ExcludeOSVersion,
                                                 backref='system'),
                     'provisions':relation(Provision, collection_class=attribute_mapped_collection('arch'),
                                                 backref='system'),
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
                        backref='object'),
                     'release_action':relation(ReleaseAction, uselist=False),
                     'reprovision_distro':relation(Distro, uselist=False),
                      '_system_ccs': relation(SystemCc, backref='system',
                                      cascade="all, delete, delete-orphan"),
                     })

mapper(SystemCc, system_cc_table)

Cpu.mapper = mapper(Cpu,cpu_table,properties = {
                                                
                                                 'flags':relation(CpuFlag), 
                                                 'system':relation(System) } )
mapper(Arch, arch_table)
mapper(SystemAdmin,system_admin_map_table,primary_key=[system_admin_map_table.c.system_id,system_admin_map_table.c.group_id])
mapper(Provision, provision_table,
       properties = {'provision_families':relation(ProvisionFamily, collection_class=attribute_mapped_collection('osmajor')),
                     'arch':relation(Arch)})
mapper(ProvisionFamily, provision_family_table,
       properties = {'provision_family_updates':relation(ProvisionFamilyUpdate, collection_class=attribute_mapped_collection('osversion')),
                     'osmajor':relation(OSMajor)})
mapper(ProvisionFamilyUpdate, provision_family_update_table,
       properties = {'osversion':relation(OSVersion)})
mapper(ExcludeOSMajor, exclude_osmajor_table,
       properties = {'osmajor':relation(OSMajor, backref='excluded_osmajors'),
                     'arch':relation(Arch)})
mapper(ExcludeOSVersion, exclude_osversion_table,
       properties = {'osversion':relation(OSVersion),
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
mapper(LabControllerDistro, lab_controller_distro_map , properties={
    'distro':relation(Distro, backref='lab_controller_assocs')
})
mapper(LabController, lab_controller_table,
        properties = {'_distros':relation(LabControllerDistro,
                                          backref='lab_controller'),
    })

mapper(Distro, distro_table,
        properties = {'osversion':relation(OSVersion, uselist=False,
                                           backref='distros'),
                      'breed':relation(Breed, backref='distros'),
                      'arch':relation(Arch, backref='distros'),
                      '_tags':relation(DistroTag,
                                       secondary=distro_tag_map,
                                       backref='distros'),
    })
mapper(Breed, breed_table)
mapper(DistroTag, distro_tag_table)

mapper(Visit, visits_table)

mapper(VisitIdentity, visit_identity_table,
        properties=dict(users=relation(User, backref='visit_identity')))

mapper(User, users_table,
        properties=dict(_password=users_table.c.password))

Group.mapper = mapper(Group, groups_table,
        properties=dict(users=relation(User,uselist=True, secondary=user_group_table, backref='groups'),
                        systems=relation(System,secondary=system_group_table, backref='groups'),
                        admin_systems=relation(System,secondary=system_admin_map_table,backref='admins')))
                        

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))

mapper(BeakerTag, beaker_tag_table,
        polymorphic_on=beaker_tag_table.c.type, polymorphic_identity=u'tag')

mapper(RetentionTag, retention_tag_table, inherits=BeakerTag, 
        properties=dict(is_default=retention_tag_table.c.default_),
        polymorphic_identity=u'retention_tag')

mapper(Activity, activity_table,
        polymorphic_on=activity_table.c.type, polymorphic_identity='activity',
        properties=dict(user=relation(User, uselist=False,
                        backref='activity')))

mapper(SystemActivity, system_activity_table, inherits=Activity,
        polymorphic_identity='system_activity')

mapper(RecipeSetActivity, recipeset_activity_table, inherits=Activity,
       polymorphic_identity='recipeset_activity')

mapper(GroupActivity, group_activity_table, inherits=Activity,
        polymorphic_identity='group_activity',
        properties=dict(object=relation(Group, uselist=False,
                         backref='activity')))

mapper(DistroActivity, distro_activity_table, inherits=Activity,
       polymorphic_identity='distro_activity',
       properties=dict(object=relation(Distro, uselist=False,
                         backref='activity')))

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
                                        secondary=task_packages_required_map),
                      'needs':relation(TaskPropertyNeeded),
                      'bugzillas':relation(TaskBugzilla, backref='task',
                                            cascade='all, delete-orphan'),
                      'owner':relation(User, uselist=False, backref='tasks'),
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
                      'owner':relation(User, uselist=False, backref='jobs'),
                      'result':relation(TaskResult, uselist=False),
                      'retention_tag':relation(RetentionTag, uselist=False,backref='jobs'),
                      'product':relation(Product, uselist=False, backref='jobs'),
                      'status':relation(TaskStatus, uselist=False),
                      '_job_ccs': relation(JobCc, backref='job')})

mapper(JobCc, job_cc_table)

mapper(Product, product_table)

mapper(RecipeSetResponse,recipe_set_nacked_table,
        properties = { 'recipesets':relation(RecipeSet),
                        'response' : relation(Response,uselist=False)})

mapper(Response,response_table)

mapper(RecipeSet, recipe_set_table,
        properties = {'recipes':relation(Recipe, backref='recipeset'),
                      'priority':relation(TaskPriority, uselist=False),
                      'result':relation(TaskResult, uselist=False),
                      'status':relation(TaskStatus, uselist=False),
                      'activity':relation(RecipeSetActivity,
                        order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                        backref='object'),
                      'lab_controller':relation(LabController, uselist=False),
                      'nacked':relation(RecipeSetResponse,cascade="all, delete-orphan",uselist=False),
                      'deleted':recipe_set_table.c.delete_time
                     })

mapper(LogRecipe, log_recipe_table)

mapper(LogRecipeTask, log_recipe_task_table)

mapper(LogRecipeTaskResult, log_recipe_task_result_table)

mapper(Recipe, recipe_table,
        polymorphic_on=recipe_table.c.type, polymorphic_identity='recipe',
        properties = {'distro':relation(Distro, uselist=False,
                                        backref='recipes'),
                      'system':relation(System, uselist=False,
                                        backref='recipes'),
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
                      'result':relation(TaskResult, uselist=False),
                      'status':relation(TaskStatus, uselist=False),
                      'logs':relation(LogRecipe, backref='parent'),
                      '_roles':relation(RecipeRole),
                      'custom_packages':relation(TaskPackage,
                                        secondary=task_packages_custom_map),
                      'ks_appends':relation(RecipeKSAppend),
                     }
      )
mapper(GuestRecipe, guest_recipe_table, inherits=Recipe,
        polymorphic_identity='guest_recipe')
mapper(MachineRecipe, machine_recipe_table, inherits=Recipe,
        polymorphic_identity='machine_recipe',
        properties = {'guests':relation(Recipe, backref='hostmachine',
                                        secondary=machine_guest_map)})

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
                      'task':relation(Task, uselist=False, backref='runs'),
                      'result':relation(TaskResult, uselist=False),
                      'status':relation(TaskStatus, uselist=False),
                      '_roles':relation(RecipeTaskRole),
                      'logs':relation(LogRecipeTask, backref='parent'),
                      'watchdog':relation(Watchdog, uselist=False),
                     }
      )

mapper(RecipeRole, recipe_role_table,
        properties = {'system':relation(System, uselist=False),
                     }
      )
mapper(RecipeTaskRole, recipe_task_role_table,
        properties = {'system':relation(System, uselist=False),
                     }
      )
mapper(RecipeTaskParam, recipe_task_param_table)
mapper(RecipeTaskComment, recipe_task_comment_table,
        properties = {'user':relation(User, uselist=False, backref='comments')})
mapper(RecipeTaskBugzilla, recipe_task_bugzilla_table)
mapper(RecipeTaskRpm, recipe_task_rpm_table)
mapper(RecipeTaskResult, recipe_task_result_table,
        properties = {'result':relation(TaskResult, uselist=False),
                      'logs':relation(LogRecipeTaskResult, backref='parent'),
                     }
      )
mapper(TaskPriority, task_priority_table)
mapper(TaskStatus, task_status_table)
mapper(TaskResult, task_result_table)

## Static list of device_classes -- used by master.kid
global _device_classes
_device_classes = None
def device_classes():
    global _device_classes
    if not _device_classes:
        _device_classes = DeviceClass.query.all()
    for device_class in _device_classes:
        yield device_class

global _system_types
_system_types = None
def system_types():
    global _system_types
    if not _system_types:
        _system_types = SystemType.query.all()
    for system_type in _system_types:
        yield system_type
