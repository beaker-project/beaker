
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Database type definitions.
"""

import uuid
import netaddr
from sqlalchemy.types import TypeDecorator, BINARY, BigInteger
from bkr.server.enum import DeclEnum

class TaskStatus(DeclEnum):

    symbols = [
        ('new',        u'New',        dict(severity=10, finished=False, queued=True)),
        ('processed',  u'Processed',  dict(severity=20, finished=False, queued=True)),
        ('queued',     u'Queued',     dict(severity=30, finished=False, queued=True)),
        ('scheduled',  u'Scheduled',  dict(severity=40, finished=False, queued=True)),
        # Waiting, Running, and Installing are transient states.  It will never be final.
        #  But having it the lowest Severity will show a job as 
        #  Running until it finishes with either Completed, Cancelled or 
        #  Aborted.
        ('waiting',    u'Waiting',    dict(severity=7, finished=False, queued=False)),
        ('installing', u'Installing', dict(severity=6, finished=False, queued=False)),
        ('running',    u'Running',    dict(severity=5, finished=False, queued=False)),
        ('reserved',   u'Reserved',   dict(severity=45, finished=False, queued=False)),
        ('completed',  u'Completed',  dict(severity=70, finished=True, queued=False)),
        ('cancelled',  u'Cancelled',  dict(severity=60, finished=True, queued=False)),
        ('aborted',    u'Aborted',    dict(severity=50, finished=True, queued=False)),
    ]

    @classmethod
    def max(cls):
        return max(cls, key=lambda s: s.severity)

class CommandStatus(DeclEnum):

    symbols = [
        ('queued',    u'Queued',    dict(finished=False)),
        ('running',   u'Running',   dict(finished=False)),
        ('completed', u'Completed', dict(finished=True)),
        ('failed',    u'Failed',    dict(finished=True)),
        ('aborted',   u'Aborted',   dict(finished=True)),
    ]

class TaskResult(DeclEnum):

    symbols = [
        ('new',   u'New',   dict(severity=10)),
        ('pass_', u'Pass',  dict(severity=20)),
        ('warn',  u'Warn',  dict(severity=30)),
        ('fail',  u'Fail',  dict(severity=40)),
        ('panic', u'Panic', dict(severity=50)),
        ('none',  u'None',  dict(severity=15)),
        ('skip',  u'Skip',  dict(severity=16)),
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

class SystemSchedulerStatus(DeclEnum):

    symbols = [
        ('idle',     u'Idle',     dict()),
        ('pending',  u'Pending',  dict()),
        ('reserved', u'Reserved', dict()),
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

class SystemPermission(DeclEnum):

    symbols = [
        ('view',           u'view',           dict(label=_(u'View'))),
        ('view_power',     u'view_power',     dict(label=_(u'View power settings'))),
        ('edit_policy',    u'edit_policy',    dict(label=_(u'Edit this policy'))),
        ('edit_system',    u'edit_system',    dict(label=_(u'Edit system details'))),
        ('loan_any',       u'loan_any',       dict(label=_(u'Loan to anyone'))),
        ('loan_self',      u'loan_self',      dict(label=_(u'Loan to self'))),
        ('control_system', u'control_system', dict(label=_(u'Control power'))),
        ('reserve',        u'reserve',        dict(label=_(u'Reserve'))),
    ]

class GroupMembershipType(DeclEnum):

    symbols = [
        ('normal',   u'normal',   dict(label=_(u'Normal'))),
        ('ldap',     u'ldap',     dict(label=_(u'LDAP'))),
        ('inverted', u'inverted', dict(label=_(u'Inverted'))),
    ]

class RecipeReservationCondition(DeclEnum):
    symbols = [
        ('onabort', u'onabort', dict()),
        ('onfail',  u'onfail',  dict()),
        ('onwarn',  u'onwarn',  dict()),
        ('always',  u'always',  dict()),
    ]

class UUID(TypeDecorator):
    """
    Database type for storing UUIDs as BINARY(16).
    """
    impl = BINARY

    def __init__(self):
        super(UUID, self).__init__(length=16)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value.bytes
        raise TypeError('Expected UUID but got %r' % value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(bytes=value)

    def is_mutable(self):
        return False

# A netaddr "dialect" for formatting MAC addresses... this is the most common 
# format, and is expected by virt-install, so I'm not sure why netaddr doesn't 
# ship with it...
class mac_unix_padded_dialect(netaddr.mac_unix):
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
        return netaddr.EUI(value, dialect=mac_unix_padded_dialect)

class IPAddress(TypeDecorator):
    """
    Database type for IP addresses. Stores them as raw integers, which 
    lets us do arithmetic on them in the database.
    """
    impl = BigInteger

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, netaddr.IPAddress):
            return int(value)
        return int(netaddr.IPAddress(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return netaddr.IPAddress(value)
