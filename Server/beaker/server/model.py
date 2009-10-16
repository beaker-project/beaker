from datetime import datetime
from turbogears.database import metadata, mapper, session
from turbogears.config import get
import ldap
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relation, backref, synonym, dynamic_loader
from sqlalchemy import String, Unicode, Integer, DateTime, UnicodeText, Boolean, Float, VARCHAR, TEXT, Numeric
from sqlalchemy import or_, and_, not_, select
from sqlalchemy.exceptions import InvalidRequestError
from identity import LdapSqlAlchemyIdentityProvider
from cobbler_utils import consolidate, string_to_hash
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.util import OrderedDict
from sqlalchemy.orm.collections import MappedCollection
from sqlalchemy.ext.associationproxy import association_proxy
import socket
from xmlrpclib import ProtocolError
from sqlalchemy import case
import time
from sqlalchemy import func
from sqlalchemy.orm.collections import collection
from bexceptions import *

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

from turbogears import identity

from datetime import timedelta, date, datetime

import md5

import xml.dom.minidom
from xml.dom.minidom import Node

import logging
log = logging.getLogger(__name__)

system_table = Table('system', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn', String(255), nullable=False),
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
    Column('shared', Boolean, default=False),
    Column('private', Boolean, default=False),
    Column('deleted', Boolean, default=False),
    Column('memory', Integer),
    Column('checksum', String(32)),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id')),
    Column('mac_address',String(18)),
    Column('loan_id', Integer,
           ForeignKey('tg_user.user_id')),
)

system_device_map = Table('system_device_map', metadata,
    Column('system_id', Integer,
           ForeignKey('system.id'),
           nullable=False),
    Column('device_id', Integer,
           ForeignKey('device.id'),
           nullable=False),
)

system_type_table = Table('system_type', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('type', Unicode(100), nullable=False),
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
           nullable=False),
    Column('arch_id', Integer,
           ForeignKey('arch.id'),
           nullable=False),
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

task_exclude_table = Table('task_exclude', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('task_id', Integer, ForeignKey('task.id')),
    Column('arch_id', Integer, ForeignKey('arch.id')),
    Column('osmajor_id', Integer, ForeignKey('osmajor.id')),
    Column('osversion_id', Integer, ForeignKey('osversion.id')),
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
    Column('system_id', Integer, ForeignKey('system.id')),
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
    Column('created', DateTime, nullable=False, default=datetime.now),
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
    Column('created', DateTime, default=datetime.now)
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(255), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(40)),
    Column('created', DateTime, default=datetime.now)
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255))
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

system_group_table = Table('system_group', metadata,
    Column('system_id', Integer, ForeignKey('system.id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

# activity schema

# TODO This will require some indexes for performance.
activity_table = Table('activity', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('type', String(40), nullable=False),
    Column('field_name', String(40), nullable=False),
    Column('service', String(100), nullable=False),
    Column('action', String(40), nullable=False),
    Column('old_value', String(40)),
    Column('new_value', String(40))
)

system_activity_table = Table('system_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'))
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
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('text',TEXT, nullable=False)
)

key_table = Table('key', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('key_name', String(256), nullable=False, unique=True),
    Column('numeric', Boolean, default=False),
)

key_value_string_table = Table('key_value_string', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), index=True),
    Column('key_id', Integer, ForeignKey('key.id'), index=True),
    Column('key_value',TEXT, nullable=False)
)

key_value_int_table = Table('key_value_int', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('system_id', Integer, ForeignKey('system.id'), index=True),
    Column('key_id', Integer, ForeignKey('key.id'), index=True),
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

recipe_set_table = Table('recipe_set',metadata,
        Column('id', Integer, primary_key=True),
        Column('job_id',Integer,
                ForeignKey('job.id')),
        Column('priority_id', Integer,
                ForeignKey('task_priority.id'), default=select([task_priority_table.c.id], limit=1).where(task_priority_table.c.priority==u'Normal').correlate(None)),
        Column('queue_time',DateTime, nullable=False, default=datetime.now),
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
        Column('_host_requires',Unicode()),
        Column('_distro_requires',Unicode()),
        Column('kickstart',Unicode()),
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
        Column('kernel_options', String(1024)),
        Column('kernel_options_post', String(1024)),
)

machine_recipe_table = Table('machine_recipe', metadata,
        Column('id', Integer, ForeignKey('recipe.id'), primary_key=True)
)

guest_recipe_table = Table('guest_recipe', metadata,
        Column('id', Integer, ForeignKey('recipe.id'), primary_key=True),
        Column('guestname', Unicode()),
        Column('guestargs', Unicode())
)

machine_guest_map =Table('machine_guest_map',metadata,
        Column('machine_recipe_id', Integer,
                ForeignKey('machine_recipe.id'),
                nullable=False),
        Column('guest_recipe_id', Integer,
                ForeignKey('recipe.id'),
                nullable=False)
)

system_recipe_map = Table('system_recipe_map', metadata,
        Column('system_id', Integer,
                ForeignKey('system.id'),
                nullable=False),
        Column('recipe_id', Integer,
                ForeignKey('recipe.id'),
                nullable=False),
)

recipe_tag_table = Table('recipe_tag',metadata,
        Column('id', Integer, primary_key=True),
        Column('tag', Unicode(255))
)

recipe_tag_map = Table('recipe_tag_map', metadata,
        Column('tag_id', Integer,
               ForeignKey('recipe_tag.id'),
               nullable=False),
        Column('recipe_id', Integer, 
               ForeignKey('recipe.id'),
               nullable=False),
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

recipe_task_table =Table('recipe_task',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_id',Integer,
                ForeignKey('recipe.id')),
        Column('task_id',Integer,
                ForeignKey('task.id')),
        Column('start_time',DateTime),
        Column('finish_time',DateTime),
        Column('result_id', Integer,
                ForeignKey('task_result.id')),
        Column('status_id', Integer,
                ForeignKey('task_status.id'),default=select([task_status_table.c.id], limit=1).where(task_status_table.c.status==u'New').correlate(None)),
        Column('role', Unicode(255)),
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
        Column('value',Unicode())
)

recipe_task_comment_table = Table('recipe_task_comment',metadata,
        Column('id', Integer, primary_key=True),
        Column('recipe_task_id', Integer,
                ForeignKey('recipe_task.id')),
        Column('comment', Unicode()),
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
        Column('log', Unicode()),
)

task_table = Table('task',metadata,
        Column('id', Integer, primary_key=True),
        Column('name', Unicode(2048)),
        Column('rpm', Unicode(2048)),
        Column('path', Unicode(4096)),
        Column('description', Unicode(2048)),
        Column('repo', Unicode(256)),
        Column('avg_time', Integer),
        Column('destructive', Boolean),
        Column('nda', Boolean),
        # This should be a map table
        #Column('notify', Unicode(2048)),

        Column('creation_date', DateTime, default=datetime.now),
        Column('update_date', DateTime, onupdate=datetime.now),
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
        Column('task_id', Integer,
                ForeignKey('task.id', onupdate='CASCADE',
                                      ondelete='CASCADE')),
        Column('package_id', Integer,
                ForeignKey('task_package.id',onupdate='CASCADE',
                                             ondelete='CASCADE')),
)

task_packages_required_map = Table('task_packages_required_map', metadata,
        Column('task_id', Integer,
                ForeignKey('task.id', onupdate='CASCADE',
                                      ondelete='CASCADE')),
        Column('package_id', Integer,
                ForeignKey('task_package.id',onupdate='CASCADE',
                                             ondelete='CASCADE')),
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
        Column('task_id', Integer,
                ForeignKey('task.id',onupdate='CASCADE',
                                     ondelete='CASCADE')),
        Column('task_type_id', Integer,
                ForeignKey('task_type.id', onupdate='CASCADE',
                                           ondelete='CASCADE')),
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
    def list_by_name(cls, username):
        ldap_users = []
        if cls.ldapenabled:
            filter = "(uid=%s*)" % username
            ldapcon = ldap.initialize(cls.uri)
            rc = ldapcon.search(cls.basedn, ldap.SCOPE_SUBTREE, filter)
            objects = ldapcon.result(rc)[1]
            ldap_users = [object[0].split(',')[0].split('=')[1] for object in objects]
        db_users = [user.user_name for user in cls.query().filter(User.user_name.like('%s%%' % username))]
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


class Permission(object):
    """
    A relationship that determines what each Group can do
    """
    pass


class MappedObject(object):

    doc = xml.dom.minidom.Document()

    @classmethod
    def lazy_create(cls, **kwargs):
        try:
            item = cls.query.filter_by(**kwargs).one()
        except:
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


class SystemObject(object):
    def get_tables(cls):
        tables = cls.get_dict().keys()
        tables.sort()
        return tables
    get_tables = classmethod(get_tables)

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
    get_dict = classmethod(get_dict)

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


class Group(object):
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
    def list_by_name(cls, name):
        """
        A class method that can be used to search groups
        based on the group_name
        """
        return cls.query().filter(Group.group_name.like('%s%%' % name))


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

    def remote(self):
        class CobblerAPI:
            def __init__(self, system):
                self.system = system
                url = "http://%s/cobbler_api" % system.lab_controller.fqdn
                self.remote = xmlrpclib.ServerProxy(url, allow_none=True)
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
                    profile = self.remote.get_profiles(0,
                                                       1,
                                                       self.token)[0]['name']
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
                expiredelta = datetime.now() + timedelta(minutes=5)
                while(True):
                    for line in self.get_event_log(task_id).split('\n'):
                        if line.find("### TASK COMPLETE ###") != -1:
                            return True
                        if line.find("### TASK FAILED ###") != -1:
                            raise BX(_("Cobbler Task:%s Failed" % task_id))
                    if datetime.now() > expiredelta:
                        raise BX(_('Cobbler Task:%s Timed out' % task_id))
                    time.sleep(5)

                        
            def power(self,action='reboot', wait=True):
                system_id = self.get_system()
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
                          kernel_options_post=None):
                """
                Provision the System
                make xmlrpc call to lab controller
                """
                if not distro:
                    return False

                system_id = self.get_system()
                profile = distro.install_name
                systemprofile = profile
                profile_id = self.remote.get_profile_handle(profile, self.token)
                if not profile_id:
                    raise BX(_("%s profile not found on %s" % (profile, self.system.labcontroller.fqdn)))
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
                    # Escape any $ signs or cobbler will barf
                    kickstart = kickstart.replace('$','\$')
                    # add in cobbler packages snippet...
                    # Find next line after %packages
                    packages_slot = kickstart.find("\n",kickstart.find("%packages"))
                    beforepackages = kickstart[:packages_slot]
                    afterpackages = kickstart[packages_slot:]

                    # Fill in basic requirements for RHTS
                    kicktemplate = """
url --url=$tree
%(beforepackages)s
$SNIPPET("rhts_packages")
%(afterpackages)s

%%pre
$SNIPPET("rhts_pre")

%%post
$SNIPPET("rhts_post")
                    """
                    kickstart = kicktemplate % dict(
                                                beforepackages = beforepackages,
                                                afterpackages = afterpackages)

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
    def all(cls, user=None):
        """
        Only systems that the current user has permission to see
        
        """
        query = cls.query().outerjoin(['groups','users'], aliased=True)
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

#                                  or_(User.user_id==user.user_id, 
#                                      system_group_table.c.system_id==None))))

    @classmethod
    def free(cls, user):
        """
        Builds on available.  Only systems with no users.
        """
        return System.available(user).filter(System.user==None)

    @classmethod
    def available(cls, user):
        """
        Builds on all.  Only systems which this user has permission to reserve.
          If a system is loaned then its only available for that person.
        """
        return System.all(user).filter(and_(
                                System.status==SystemStatus.by_name(u'Working'),
                                    or_(and_(System.owner==user,
                                             System.loaned==None),
                                      System.loaned==user,
                                      and_(System.shared==True,
                                           Group.systems==None,
                                           System.loaned==None
                                          ),
                                      and_(System.shared==True,
                                           System.loaned==None,
                                           User.user_id==user.user_id
                                          )
                                       )
                                           )
                                      )

    @classmethod
    def available_order(cls, user):
        return cls.available(user).order_by(case([(System.owner==user, 1),
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
        results = dict(ks_meta = string_to_hash(ks_meta), 
                       kernel_options = string_to_hash(kernel_options), 
                       kernel_options_post = string_to_hash(kernel_options_post))
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
        return results

    def provision_to_dict(self, provision):
        ks_meta = string_to_hash(provision.ks_meta)
        kernel_options = string_to_hash(provision.kernel_options)
        kernel_options_post = string_to_hash(provision.kernel_options_post)
        return dict(ks_meta = ks_meta, kernel_options = kernel_options,
                            kernel_options_post = kernel_options_post)

    def can_admin(self, user=None):
        if user:
            if user == self.owner or user.is_admin():
                return True
        return False

    def can_loan(self, user=None):
        if user and not self.loaned and not self.user:
            if user == self.owner or user.is_admin():
                return True
        return False

    def current_loan(self, user=None):
        if user and self.loaned:
            if self.loaned == user or \
               self.owner  == user or \
               user.is_admin():
                return True
        return False

    def current_user(self, user=None):
        if user and self.user:
            if self.user  == user \
               or user.is_admin():
                return True
        return False
        
    def can_share(self, user=None):
        if user and not self.user:
            # If the system is loaned its exclusive!
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
                if self.groups:
                    for group in user.groups:
                        if group in self.groups:
                            return True
                else:
                # If the system has no groups
                    return True
        return False
        
    def get_allowed_attr(self):
        attributes = ['vendor','model','memory']
        return attributes

    def get_update_method(self,obj_str):
        methods = dict ( Cpu = self.updateCpu, Arch = self.updateArch, 
                         Devices = self.updateDevices )
        return methods[obj_str]

    def update_legacy(self, inventory):
        """
        Update Key/Value pairs for legacy RHTS
        """
        #Remove any keys that will be added
        for mykey in self.key_values_int[:]:
            if mykey.key.key_name in inventory:
                self.key_values_int.remove(mykey)
        for mykey in self.key_values_string[:]:
            if mykey.key.key_name in inventory:
                self.key_values_string.remove(mykey)

        #Add the uploaded keys
        for key in inventory:
            try:
                _key = Key.by_name(key)
            except InvalidRequestError:
                continue
            if isinstance(inventory[key], list):
                for value in inventory[key]:
                    if _key.numeric:
                        self.key_values_int.append(Key_Value_Int(_key,value))
                    else:
                        self.key_values_string.append(Key_Value_String(_key,value))
            else:
                if _key.numeric:
                    self.key_values_int.append(Key_Value_Int(_key,inventory[key]))
                else:
                    self.key_values_string.append(Key_Value_String(_key,inventory[key]))
        return 0
                    

    def update(self, inventory):
        """ Update Inventory """

        # Update last checkin even if we don't change anything.
        self.date_lastcheckin = datetime.utcnow()

        md5sum = md5.new("%s" % inventory).hexdigest()
        if self.checksum == md5sum:
            return 0
        self.checksum = md5sum
        self.type_id = 1
        self.status_id = 1
        for key in inventory:
            if key in self.get_allowed_attr():
                if not getattr(self, key, None):
                    setattr(self, key, inventory[key])
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

    def updateDevices(self, deviceinfo):
        for device in deviceinfo:
            try:
                device = Device.query().filter_by(vendor_id = device['vendorID'],
                                   device_id = device['deviceID'],
                                   subsys_vendor_id = device['subsysVendorID'],
                                   subsys_device_id = device['subsysDeviceID'],
                                   bus = device['bus'],
                                   driver = device['driver'],
                                   description = device['description']).one()
                self.devices.append(device)
            except InvalidRequestError:
                new_device = Device(vendor_id       = device['vendorID'],
                                     device_id       = device['deviceID'],
                                     subsys_vendor_id = device['subsysVendorID'],
                                     subsys_device_id = device['subsysDeviceID'],
                                     bus            = device['bus'],
                                     driver         = device['driver'],
                                     device_class   = device['type'],
                                     description    = device['description'])
                session.save(new_device)
                session.flush([new_device])
                self.devices.append(new_device)

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
        if self.type.type == 'Machine':
            distros = distros.filter(distro_table.c.virt==False)
        return distros

    def action_release(self):
        self.user = None
        # Attempt to remove Netboot entry
        # and turn off machine, but don't fail if we can't
        try:
            self.remote.release()
        except:
            pass

    def action_provision(self, 
                         distro=None,
                         ks_meta=None,
                         kernel_options=None,
                         kernel_options_post=None,
                         kickstart=None):
        if not self.remote:
            return False
        self.remote.provision(distro=distro, 
                              ks_meta=ks_meta,
                              kernel_options=kernel_options,
                              kernel_options_post=kernel_options_post,
                              kickstart=kickstart)

    def action_auto_provision(self, 
                             distro=None,
                             ks_meta=None,
                             kernel_options=None,
                             kernel_options_post=None,
                             kickstart=None):
        if not self.remote:
            return False

        results = self.install_options(distro, ks_meta,
                                               kernel_options,
                                               kernel_options_post)
        self.remote.provision(distro, kickstart, **results)
        if self.power:
            self.remote.power(action="reboot")

    def action_power(self,
                     action='reboot'):
        if self.remote and self.power:
            self.remote.power(action)
        else:
            return False

    def __repr__(self):
        return self.fqdn

# for property in System.mapper.iterate_properties:
#     print property.mapper.class_.__name__
#     print property.key
#
# systems = session.query(System).join('status').join('type').join(['cpu','flags']).filter(CpuFlag.c.flag=='lm')


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
    def by_name(cls, systemtype):
        return cls.query.filter_by(type=systemtype).one()


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
    def by_name(cls, systemstatus):
        return cls.query.filter_by(status=systemstatus).one()


class Arch(SystemObject):
    def __init__(self, arch=None):
        self.arch = arch

    def __repr__(self):
        return '%s' % self.arch

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


class OSMajor(SystemObject):
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
        all = cls.query()
        return [(0,"All")] + [(major.id, major.osmajor) for major in all]

    def __repr__(self):
        return '%s' % self.osmajor


class OSVersion(SystemObject):
    def __init__(self, osmajor, osminor):
        self.osmajor = osmajor
        self.osminor = osminor

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
        return [(0,"None")] + [(lc.id, lc.fqdn) for lc in all]

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
    def by_status(cls, labcontroller, status="active"):
        """ return a list of all watchdog entries that are either active 
            or expired for this lab controller
        """

        REMAP_STATUS = {
            "active"  : "__gt__",
            "expired" : "__le__",
        }
        op = REMAP_STATUS.get(status, None)
        if op:
            return cls.query.join(['system']).filter(
                                      and_(System.lab_controller==labcontroller,
                                 getattr(Watchdog.kill_time, op)(datetime.now())
                                          )
                                                    )

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
        for cpuflag in flags:
            new_flag = CpuFlag(flag=cpuflag)
            self.flags.append(new_flag)

# systems = session.query(System).join('status').join('type').join(['cpu','flags']).filter(CpuFlag.c.flag=='lm')


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


class Distro(object):
    def __init__(self, install_name=None):
        self.install_name = install_name

    @classmethod
    def by_install_name(cls, install_name):
        return cls.query.filter_by(install_name=install_name).one()

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
            if callable(getattr(child, 'filter')):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        distros = Distro.query()
        if joins:
            distros = distros.filter(and_(*joins))
        if queries:
            distros = distros.filter(and_(*queries))
        return distros.order_by('-date_created')

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
        systems = self.systems(user)
        #FIXME Should validate XML before processing.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(filter)):
            if callable(getattr(child, 'filter')):
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
                 where(task_table.c.id==task_exclude_table.c.task_id).
                 where(task_exclude_table.c.arch_id==arch_table.c.id).
                 where(arch_table.c.id==self.arch_id)
                                      ),
                         Task.id.in_(select([task_table.c.id]).
                 where(task_table.c.id==task_exclude_table.c.task_id).
                 where(task_exclude_table.c.osmajor_id==osmajor_table.c.id).
                 where(osmajor_table.c.id==self.osversion.osmajor.id)
                                      ),
                         Task.id.in_(select([task_table.c.id]).
                 where(task_table.c.id==task_exclude_table.c.task_id).
                 where(task_exclude_table.c.osversion_id==osversion_table.c.id).
                 where(osversion_table.c.id==self.osversion.id)
                                      ),
                        )
                    )
        )

    def systems(self, user=None):
        """
        List of systems that support this distro
        Limit to what is available to user if user passed in.
        """
        if user:
            systems = System.available_order(user)
        else:
            systems = System.query()

        return systems.join(['lab_controller','_distros','distro']).filter(
             and_(Distro.install_name==self.install_name,
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


# Activity model
class Activity(object):
    def __init__(self, user=None, service=None, action=None,
                 field_name=None, old_value=None, new_value=None):
        self.user = user
        self.service = service
        self.field_name = field_name
        self.action = action
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


class Key(object):
    def __init__(self, key_name=None, numeric=False):
        self.key_name = key_name
        self.numeric = numeric

    def __repr__(self):
        return "%s" % self.key_name

    @classmethod
    def by_name(cls, key_name):
        return cls.query().filter_by(key_name=key_name).one()

    @classmethod
    def by_id(cls, id):
        return cls.query().filter_by(id=id).one()


# key_value model
class Key_Value_String(object):
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
    pass


class TaskStatus(object):
    @classmethod
    def by_name(cls, status_name):
        return cls.query().filter_by(status=status_name).one()

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
    def by_name(cls, result_name):
        return cls.query().filter_by(result=result_name).one()

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


class Job(MappedObject):
    """
    Container to hold like recipe sets.
    """

    stop_types = ['abort','cancel']

    def to_xml(self):
        job = self.doc.createElement("job")
        job.setAttribute("id", "%s" % self.id)
        job.setAttribute("owner", "%s" % self.owner.email_address)
        job.setAttribute("result", "%s" % self.result)
        job.setAttribute("status", "%s" % self.status)
        job.appendChild(self.node("whiteboard", self.whiteboard))
        for rs in self.recipesets:
            job.appendChild(rs.to_xml())
        return job

    def cancel(self, msg=None):
        """
        Method to cancel all recipesets for this job.
        """
        for recipeset in self.recipesets:
            recipeset.cancel(msg)

    def abort(self, msg=None):
        """
        Method to abort all recipesets for this job.
        """
        for recipeset in self.recipesets:
            recipeset.abort(msg)

    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = None
        max_status = None
        for recipeset in self.recipesets:
            self.ptasks += recipeset.ptasks
            self.wtasks += recipeset.wtasks
            self.ftasks += recipeset.ftasks
            self.ktasks += recipeset.ktasks
            if recipeset.status > max_status:
                max_status = recipeset.status
            if recipeset.result > max_result:
                max_result = recipeset.result
        self.status = max_status
        self.result = max_result


class RecipeSet(MappedObject):
    """
    A Collection of Recipes that must be executed at the same time.
    """
    def to_xml(self):
        recipeSet = self.doc.createElement("recipeSet")
        recipeSet.setAttribute("id", "%s" % self.id)
        for r in self.recipes:
            recipeSet.appendChild(r.to_xml())
        return recipeSet

    @classmethod
    def by_status(cls, status, query=None):
        if not query:
            query=cls.query
        return query.join('status').filter(Status.status==status)

    @classmethod
    def by_datestamp(cls, datestamp, query=None):
        if not query:
            query=cls.query
        return query.filter(RecipeSet.queue_time <= datestamp)

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
        self.status = TaskStatus.by_name(u'Cancelled')
        for recipe in self.recipes:
            recipe.cancel(msg)

    def abort(self, msg=None):
        """
        Method to abort all recipes in this recipe set.
        """
        self.status = TaskStatus.by_name(u'Aborted')
        for recipe in self.recipes:
            recipe.abort(msg)

    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        self.ptasks = 0
        self.wtasks = 0
        self.ftasks = 0
        self.ktasks = 0
        max_result = None
        max_status = None
        for recipe in self.recipes:
            self.ptasks += recipe.ptasks
            self.wtasks += recipe.wtasks
            self.ftasks += recipe.ftasks
            self.ktasks += recipe.ktasks
            if recipe.status > max_status:
                max_status = recipe.status
            if recipe.result > max_result:
                max_result = recipe.result
        self.status = max_status
        self.result = max_result
        self.job.update_status()

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


class Recipe(MappedObject):
    """
    Contains requires for host selection and distro selection.
    Also contains what tasks will be executed.
    """
    stop_types = ['abort','cancel']

    def to_xml(self, recipe):
        recipe.setAttribute("id", "%s" % self.id)
        recipe.setAttribute("job_id", "%s" % self.recipeset.job_id)
        recipe.setAttribute("recipe_set_id", "%s" % self.recipe_set_id)
        if self.result:
            recipe.setAttribute("result", "%s" % self.result)
        if self.status:
            recipe.setAttribute("status", "%s" % self.status)
        if self.distro:
            recipe.setAttribute("distro", "%s" % self.distro.name)
            recipe.setAttribute("arch", "%s" % self.distro.arch)
            recipe.setAttribute("family", "%s" % self.distro.osversion.osmajor)
            recipe.setAttribute("variant", "%s" % self.distro.variant)
        if self.system:
            recipe.setAttribute("system", "%s" % self.system)
        repos = self.doc.createElement("repos")
        repo = self.doc.createElement("repo")
        repo.setAttribute("name", "beaker-tasks")
        repo.setAttribute("url", "http://%s/rpms" % get("servername", socket.gethostname()))
        repos.appendChild(repo)
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
        for t in self.tasks:
            recipe.appendChild(t.to_xml())
        return recipe

    def _get_packages(self):
        """ return all packages for all tests
        """
        packages = []
        for task in self.tasks:
            packages.extend(task.task.required)
        return packages

    packages = property(_get_packages)

    def _get_arch(self):
        if self.distro:
            return self.distro.arch

    arch = property(_get_arch)

    def _get_host_requires(self):
        # If no system_type is specified then add defaults
        hrs = xml.dom.minidom.parseString(self._host_requires)
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
            return self._host_requires

    def _set_host_requires(self, value):
        self._host_requires = value

    host_requires = property(_get_host_requires, _set_host_requires)

    def queue(self):
        """
        Move from New -> Queued
        """
        for task in self.tasks:
            task.queue()

    def process(self):
        """
        Move from Queued -> Processed
        """
        for task in self.tasks:
            task.process()

    def schedule(self):
        """
        Move from Processed -> Scheduled
        """
        for task in self.tasks:
            task.schedule()

    def waiting(self):
        """
        Move from Scheduled to Waiting
        """
        for task in self.tasks:
            task.waiting()

    def cancel(self, msg=None):
        """
        Method to cancel all tasks in this recipe.
        """
        self.status = TaskStatus.by_name(u'Cancelled')
        for task in self.tasks:
            task.cancel(msg)

    def abort(self, msg=None):
        """
        Method to abort all tasks in this recipe.
        """
        self.status = TaskStatus.by_name(u'Aborted')
        for task in self.tasks:
            task.abort(msg)

    def update_status(self):
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
        max_status = None
        for task in self.tasks:
            if task.result == task_pass:
                self.ptasks += 1
            if task.result == task_warn:
                self.wtasks += 1
            if task.result == task_fail:
                self.ftasks += 1
            if task.result == task_panic:
                self.ktasks += 1
            if task.status > max_status:
                    max_status = task.status
            if task.result > max_result:
                    max_result = task.result
        self.status = max_status
        self.result = max_result

        # Record the start of this Recipe.
        if not self.start_time \
           and self.status == TaskStatus.by_name(u'Running'):
            self.start_time = datetime.utcnow()

        if not self.finish_time \
           and self.status != TaskStatus.by_name(u'Running') \
           and self.status != TaskStatus.by_name(u'Waiting') \
           and self.status.severity >= TaskStatus.by_name(u'Completed').severity:
            # Record the completion of this Recipe.
            self.finish_time = datetime.utcnow()

            ## FIXME Should we actually remove the watchdog?
            ##       Maybe we should set the status of the watchdog to reclaim
            ##       so that the lab controller returns the system instead.
            # Remove this recipes watchdog
            log.debug("Remove watchdog for recipe %s" % self.id)
            del(self.watchdog)

            # Return system if reserved
            if self.system:
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

        self.recipeset.update_status()

class GuestRecipe(Recipe):
    systemtype = 'Virtual'
    def to_xml(self):
        recipe = self.doc.createElement("guestrecipe")
        recipe.setAttribute("guestname", "%s" % self.guestname)
        recipe.setAttribute("guestargs", "%s" % self.guestargs)
        return Recipe.to_xml(self,recipe)


class MachineRecipe(Recipe):
    """
    Optionally can contain guest recipes which are just other recipes
      which will be executed on this system.
    """
    systemtype = 'Machine'
    def to_xml(self):
        recipe = self.doc.createElement("recipe")
        for guest in self.guests:
            recipe.appendChild(guest.to_xml())
        return Recipe.to_xml(self,recipe)

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


class RecipeTask(MappedObject):
    """
    This holds the results/status of the task being executed.
    """
    result_types = ['pass_','warn','fail','panic']
    stop_types = ['stop','abort','cancel']

    def to_xml(self):
        task = self.doc.createElement("task")
        task.setAttribute("id", "%s" % self.id)
        task.setAttribute("name", "%s" % self.task.name)
        task.setAttribute("avg_time", "%s" % self.task.avg_time)
        task.setAttribute("role", "%s" % self.role)
        task.setAttribute("result", "%s" % self.result)
        task.setAttribute("status", "%s" % self.status)
        if self.roles:
            roles = self.doc.createElement("roles")
            for role in self.roles.to_xml():
                roles.appendChild(role)
            task.appendChild(roles)
        if self.params:
            params = self.doc.createElement("params")
            for p in self.params:
                params.appendChild(p.to_xml())
            task.appendChild(params)
        rpm = self.doc.createElement("rpm")
        rpm.setAttribute("name", "%s" % self.task.rpm)
        rpm.setAttribute("path", "%s" % self.task.path)
        task.appendChild(rpm)
        return task

    def _get_duration(self):
        try:
            return self.finish_time - self.start_time
        except TypeError:
            return None
    duration = property(_get_duration)

    def set_status(self, value):
        self._status = value


    def update_status(self):
        """
        Update number of passes, failures, warns, panics..
        """
        max_result = None
        for result in self.results:
            if result.result > max_result:
                max_result = result.result
        self.result = max_result
        self.recipe.update_status()

    def queue(self):
        """
        Moved from New -> Queued
        """
        self.status = TaskStatus.by_name(u'Queued')
        self.update_status()

    def process(self):
        """
        Moved from Queued -> Processed
        """
        self.status = TaskStatus.by_name(u'Processed')
        self.update_status()

    def schedule(self):
        """
        Moved from Processed -> Scheduled
        """
        self.status = TaskStatus.by_name(u'Scheduled')
        self.update_status()

    def waiting(self):
        """
        Moved from Scheduled -> Waiting
        """
        self.status = TaskStatus.by_name(u'Waiting')
        self.update_status()

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
            self.recipe.watchdog.kill_time = datetime.now() + timedelta(
                                                    seconds=self.task.avg_time)
        self.update_status()
        return True

    def extend(self, kill_time):
        """
        Extend the watchdog by kill_time seconds
        """
        self.recipe.watchdog.kill_time = datetime.now() + timedelta(
                                                              seconds=kill_time)

    def stop(self, *args, **kwargs):
        """
        Record the completion of this task
        """
        if not self.recipe.watchdog:
            raise BX(_('No watchdog exists for recipe %s' % self.recipe.id))
        if not self.finish_time:
            self.finish_time = datetime.utcnow()
        self.status = TaskStatus.by_name(u'Completed')
        self.update_status()
        return True

    def cancel(self, msg=None):
        """
        Cancel this task
        """
        self._abort_cancel(u'Cancelled', msg)

    def abort(self, msg=None):
        """
        Abort this task
        """
        self._abort_cancel(u'Aborted', msg)
    
    def _abort_cancel(self, status, msg=None):
        """
        cancel = User instigated
        abort  = Auto instigated
        """
        # Only record an abort/cancel on tasks that are New, Queued, Scheduled 
        # or Running
        if self.status.severity < TaskStatus.by_name(u'Completed').severity \
           or self.status == TaskStatus.by_name(u'Running') \
           or self.status == TaskStatus.by_name(u'Waiting'):
            self.status = TaskStatus.by_name(status)
            self.results.append(RecipeTaskResult(recipetask=self,
                                       path=u'/',
                                       result=TaskResult.by_name(u'Warn'),
                                       score=0,
                                       log=msg))
        self.update_status()
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
        self.results.append(RecipeTaskResult(recipetask=self,
                                   path=path,
                                   result=TaskResult.by_name(result),
                                   score=score,
                                   log=summary))
        self.update_status()
        return True


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


class RecipeTaskResult(MappedObject):
    """
    Each task can report multiple results
    """
    pass


class Task(MappedObject):
    """
    Tasks that are available to schedule
    """

    @classmethod
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


class TaskExclude(MappedObject):
    """
    A task can be excluded by arch, osmajor, or osversion
                        i386, RedHatEnterpriseLinux3, RedHatEnterpriseLinux3.0
    """
    pass

class TaskType(MappedObject):
    """
    A task can be classified into serveral task types which can be used to
    select tasks for batch runs
    """
    pass


class TaskPackage(MappedObject):
    """
    A list of packages that a tasks should be run for.
    """
    def __repr__(self):
        return self.package


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
System.mapper = mapper(System, system_table,
       properties = {'devices':relation(Device,
                                        secondary=system_device_map),
                     'type':relation(SystemType, uselist=False),
                     'status':relation(SystemStatus, uselist=False),
                     'arch':relation(Arch,
                                     order_by=[arch_table.c.arch],
                                        secondary=system_arch_map,
                                        backref='systems'),
                     'watchdog':relation(Watchdog, uselist=False,
                                        backref='system'),
                     'labinfo':relation(LabInfo, uselist=False,
                                        backref='system'),
                     'cpu':relation(Cpu, uselist=False),
                     'numa':relation(Numa, uselist=False),
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
                                     order_by=[activity_table.c.created.desc()],
                                               backref='object')})
mapper(Arch, arch_table)
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
                                        backref='osversion')})
mapper(OSMajor, osmajor_table,
       properties = {'osminor':relation(OSVersion,
                                     order_by=[osversion_table.c.osminor])})
Cpu.mapper = mapper(Cpu, cpu_table,
       properties = {'flags':relation(CpuFlag)})
mapper(LabInfo, labinfo_table)
mapper(Watchdog, watchdog_table,
       properties = {'recipetask':relation(RecipeTask, uselist=False,
                                           backref='watchdog'),
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
        properties=dict(users=relation(User,
                secondary=user_group_table, backref='groups'),
                        systems=relation(System,
                secondary=system_group_table, backref='groups')))

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))

mapper(Activity, activity_table,
        polymorphic_on=activity_table.c.type, polymorphic_identity='activity',
        properties=dict(user=relation(User, uselist=False,
                        backref='activity')))

mapper(SystemActivity, system_activity_table, inherits=Activity,
        polymorphic_identity='system_activity')

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

mapper(Key, key_table)
mapper(Key_Value_Int, key_value_int_table,
        properties=dict(key=relation(Key, uselist=False,
                        backref='key_value_int')))
mapper(Key_Value_String, key_value_string_table,
        properties=dict(key=relation(Key, uselist=False,
                        backref='key_value_string')))

mapper(Task, task_table,
        properties = {'types':relation(TaskType,
                                        secondary=task_type_map,
                                        backref='tasks'),
                      'excluded':relation(TaskExclude,
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

mapper(TaskExclude, task_exclude_table,
       properties = {'arch':relation(Arch),
                     'osmajor':relation(OSMajor),
                     'osversion':relation(OSVersion),
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
                      'status':relation(TaskStatus, uselist=False)})
mapper(RecipeSet, recipe_set_table,
        properties = {'recipes':relation(Recipe, backref='recipeset'),
                      'priority':relation(TaskPriority, uselist=False),
                      'result':relation(TaskResult, uselist=False),
                      'status':relation(TaskStatus, uselist=False),
                      'lab_controller':relation(LabController, uselist=False),
                     })

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
                      'status':relation(TaskStatus, uselist=False)})
mapper(GuestRecipe, guest_recipe_table, inherits=Recipe,
        polymorphic_identity='guest_recipe')
mapper(MachineRecipe, machine_recipe_table, inherits=Recipe,
        polymorphic_identity='machine_recipe',
        properties = {'guests':relation(Recipe, backref='hostmachine',
                                        secondary=machine_guest_map)})

mapper(RecipeTag, recipe_tag_table)
mapper(RecipeRpm, recipe_rpm_table)
mapper(RecipeRepo, recipe_repo_table)

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
        properties = {'result':relation(TaskResult, uselist=False)})

mapper(TaskPriority, task_priority_table)
mapper(TaskStatus, task_status_table)
mapper(TaskResult, task_result_table)

#                     Column("comments"), MultipleJoin('Comment')

#    tags          = MultipleJoin("distroTag")

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
