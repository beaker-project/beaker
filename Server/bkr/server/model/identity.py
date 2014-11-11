
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from datetime import datetime, timedelta
import ldap, ldap.filter
import crypt
import random
import string
import re
import cracklib
from kid import Element
import passlib.context
from sqlalchemy import (Table, Column, ForeignKey, Integer, Unicode,
        UnicodeText, String, DateTime, Boolean, UniqueConstraint)
from sqlalchemy.orm import mapper, relationship, validates, synonym
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.config import get
from turbogears.database import session
from bkr.server.bexceptions import BX, NoChangeException
from bkr.server.util import convert_db_lookup_error
from .base import DeclarativeMappedObject
from .activity import Activity, ActivityMixin
from .config import ConfigItem, ConfigValueInt, ConfigValueString

log = logging.getLogger(__name__)

group_permission_table = Table('group_permission', DeclarativeMappedObject.metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True, index=True),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True, index=True),
    mysql_engine='InnoDB',
)

class GroupActivity(Activity):

    __tablename__ = 'group_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('tg_group.group_id'), nullable=False)
    object_id = synonym('group_id')
    object = relationship('Group', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'group_activity'}

    def object_name(self):
        return "Group: %s" % self.object.display_name

class UserActivity(Activity):

    __tablename__ = 'user_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    object_id = Column('user_id', Integer, ForeignKey('tg_user.user_id'), nullable=False)
    object = relationship('User', back_populates='user_activity',
            primaryjoin='UserActivity.object_id == User.user_id')
    __mapper_args__ = {'polymorphic_identity': u'user_activity'}

    def object_name(self):
        return "User: %s" % self.object.display_name

class SubmissionDelegate(DeclarativeMappedObject):

    """
    A simple N:N mapping between users and their submission delegates
    """
    __tablename__ = 'submission_delegate'
    __table_args__ = (
        UniqueConstraint('user_id', 'delegate_id'), {'mysql_engine': 'InnoDB'})

    id = Column(Integer, nullable=False, primary_key=True)
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
        name='tg_user_id_fk1'), nullable=False)
    delegate_id = Column(Integer, ForeignKey('tg_user.user_id',
        name='tg_user_id_fk2'), nullable=False)


class User(DeclarativeMappedObject, ActivityMixin):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """

    __tablename__ = 'tg_user'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    user_id = Column(Integer, primary_key=True)
    id = synonym('user_id')
    user_name = Column(Unicode(255), unique=True)
    email_address = Column(Unicode(255), index=True)
    display_name = Column(Unicode(255))
    _password = Column('password', UnicodeText, nullable=True, default=None)
    _root_password = Column('root_password', String(255), nullable=True, default=None)
    rootpw_changed = Column(DateTime, nullable=True, default=None)
    openstack_username = Column(Unicode(255))
    openstack_password = Column(Unicode(2048))
    openstack_tenant_name = Column(Unicode(2048))
    created = Column(DateTime, default=datetime.utcnow)
    disabled = Column(Boolean, nullable=False, default=False)
    removed = Column(DateTime, nullable=True, default=None)
    submission_delegates = relationship('User', secondary=SubmissionDelegate.__table__,
            primaryjoin=user_id == SubmissionDelegate.user_id,
            secondaryjoin=user_id == SubmissionDelegate.delegate_id)
    activity = relationship(Activity, back_populates='user')
    config_values_int = relationship(ConfigValueInt, back_populates='user')
    config_values_string = relationship(ConfigValueString, back_populates='user')
    user_activity = relationship(UserActivity, back_populates='object',
            primaryjoin=user_id == UserActivity.object_id)
    group_user_assocs = relationship('UserGroup', back_populates='user',
            cascade='all, delete-orphan')
    sshpubkeys = relationship('SSHPubKey', back_populates='user')
    reservations = relationship('Reservation', back_populates='user',
            order_by='Reservation.start_time.desc()')
    system_access_policy_rules = relationship('SystemAccessPolicyRule',
            back_populates='user', cascade='all, delete, delete-orphan')
    notes = relationship('Note', back_populates='user')
    lab_controller = relationship('LabController', uselist=False,
            back_populates='user')
    jobs = relationship('Job', back_populates='owner', cascade_backrefs=False,
            primaryjoin='Job.owner_id == User.user_id')
    tasks = relationship('Task', back_populates='uploader')

    activity_type = UserActivity

    _unnormalized_username_pattern = re.compile(r'^\s|\s\s|\s$')
    @validates('user_name')
    def validate_user_name(self, key, value):
        if not value:
            raise ValueError('User must have a username')
        # Reject username values which would be normalized into a different 
        # value according to the LDAP normalization rules [RFC4518]. For 
        # sanity we always enforce this, even if LDAP is not being used.
        if self._unnormalized_username_pattern.search(value):
            raise ValueError('Username %r contains unnormalized whitespace')
        return value

    def __json__(self):
        return {
            'user_name': self.user_name,
            'display_name': self.display_name,
            'email_address': self.email_address,
        }

    def permissions(self):
        perms = set()
        for g in self.groups:
            perms |= set(g.permissions)
        return perms
    permissions = property(permissions)

    # XXX I would rather do this as a setter on 'submission_delegates'
    # but don't think I can with non declarative
    def add_submission_delegate(self, delegate, service=u'WEBUI'):
        if delegate.is_delegate_for(self):
            raise NoChangeException('%s is already a'
                ' submission delegate for %s' % (delegate, self))
        else:
            self.submission_delegates.append(delegate)
            self.record_activity(user=self, service=service,
                field=u'Submission delegate', action=u'Added', old=None,
                new=delegate.user_name)

    def remove_submission_delegate(self, delegate, service=u'WEBUI'):
        self.submission_delegates.remove(delegate)
        self.record_activity(user=self, service=service,
            field=u'Submission delegate', action=u'Removed',
            old=delegate.user_name, new=None)

    def is_delegate_for(self, user):
        """Return True if we can delegate jobs on behalf of user"""
        return SubmissionDelegate.query.filter_by(delegate_id=self.user_id,
            user_id=user.user_id).first() is not None

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
        ldapenabled = get('identity.ldap.enabled', False)
        autocreate = get('identity.soldapprovider.autocreate', False)
        # Presence of '/' indicates a Kerberos service principal.
        if not user and ldapenabled and autocreate and '/' not in user_name:
            filter = ldap.filter.filter_format('(uid=%s)', [user_name.encode('utf8')])
            ldapcon = ldap.initialize(get('identity.soldapprovider.uri'))
            objects = ldapcon.search_st(get('identity.soldapprovider.basedn', ''),
                    ldap.SCOPE_SUBTREE, filter,
                    timeout=get('identity.soldapprovider.timeout', 20))
            # no match
            if(len(objects) == 0):
                return None
            # need exact match
            elif(len(objects) > 1):
                return None
            attrs = objects[0][1]
            # LDAP normalization rules means that we might have found a user 
            # who doesn't actually match the username we were given.
            if attrs['uid'][0].decode('utf8') != user_name:
                return None
            user = User()
            user.user_name = attrs['uid'][0].decode('utf8')
            user.display_name = attrs['cn'][0].decode('utf8')
            user.email_address = attrs['mail'][0].decode('utf8')
            session.add(user)
            session.flush()
        return user

    @classmethod
    def list_by_name(cls, username,find_anywhere=False,find_ldap_users=True):
        ldap_users = []
        ldapenabled = get('identity.ldap.enabled', False)
        if ldapenabled and find_ldap_users is True:
            filter = ldap.filter.filter_format('(uid=%s*)', [username.encode('utf8')])
            ldapcon = ldap.initialize(get('identity.soldapprovider.uri'))
            objects = ldapcon.search_st(get('identity.soldapprovider.basedn', ''),
                    ldap.SCOPE_SUBTREE, filter,
                    timeout=get('identity.soldapprovider.timeout', 20))
            ldap_users = [(object[1]['uid'][0].decode('utf8'),
                    object[1]['cn'][0].decode('utf8'))
                    for object in objects]
        if find_anywhere:
            f = User.user_name.like('%%%s%%' % username)
        else:
            f = User.user_name.like('%s%%' % username)
        # Don't return Removed Users
        # They may still be listed in ldap though.
        db_users = [(user.user_name, user.display_name)
                for user in cls.query.filter(f).filter(User.removed==None)]
        return list(set(db_users + ldap_users))

    _password_context = passlib.context.CryptContext(
        schemes=['pbkdf2_sha512', 'hex_sha1'],
        # unsalted SHA1 was the scheme inherited from TurboGears 1.0,
        # this allows passwords to match against the old hashes but we will
        # replace it with a new hash on successful login
        deprecated=['hex_sha1'],
    )

    def _set_password(self, raw_password):
        self._password = self._password_context.encrypt(raw_password).decode('ascii')

    def _get_password(self):
        return self._password

    password = property(_get_password, _set_password)

    def can_change_password(self):
        if get('identity.ldap.enabled', False):
            filter = ldap.filter.filter_format('(uid=%s)', [self.user_name])
            ldapcon = ldap.initialize(get('identity.soldapprovider.uri'))
            objects = ldapcon.search_st(get('identity.soldapprovider.basedn', ''),
                    ldap.SCOPE_SUBTREE, filter,
                    timeout=get('identity.soldapprovider.timeout', 20))
            if len(objects) != 0:
                # LDAP user. No chance of changing password.
                return False
            else:
                # Assume non LDAP user
                return True
        else:
            return True

    def check_password(self, raw_password):
        # Empty passwords are not accepted.
        if not raw_password:
            return False

        # If the account has a password set in Beaker, try verifying it.
        if self._password:
            verified, new_hash = self._password_context.verify_and_update(
                    raw_password, self._password)
            if verified:
                if new_hash:
                    log.info('Upgrading obsolete password hash for user %s', self)
                    # replace obsolete hash with new one
                    self._password = new_hash
                return True
            else:
                return False

        # If LDAP is enabled, try an LDAP bind.
        ldapenabled = get('identity.ldap.enabled', False)
        # Presence of '/' indicates a Kerberos service principal.
        if ldapenabled and '/' not in self.user_name:
            filter = ldap.filter.filter_format('(uid=%s)', [self.user_name])
            ldapcon = ldap.initialize(get('identity.soldapprovider.uri'))
            objects = ldapcon.search_st(get('identity.soldapprovider.basedn', ''),
                    ldap.SCOPE_SUBTREE, filter,
                    timeout=get('identity.soldapprovider.timeout', 20))
            if len(objects) == 0:
                return False
            elif len(objects) > 1:
                return False
            dn = objects[0][0]
            try:
                rc = ldapcon.simple_bind(dn, raw_password)
                ldapcon.result(rc)
                return True
            except ldap.INVALID_CREDENTIALS:
                return False

        return False

    def can_log_in(self):
        if self.disabled:
            log.warning('Login attempt from disabled account %s', self.user_name)
            return False
        if self.removed:
            log.warning('Login attempt from removed account %s', self.user_name)
            return False
        return True

    def _set_root_password(self, password):
        "Set the password to be used for root on provisioned systems, hashing if necessary"
        if password:
            if len(password.split('$')) != 4:
                salt = ''.join(random.choice(string.digits + string.ascii_letters)
                                for i in range(8))
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
                salt = ''.join(random.choice(string.digits + string.ascii_letters)
                                for i in range(8))
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

    groups = association_proxy('group_user_assocs','group',
            creator=lambda group: UserGroup(group=group))

class Group(DeclarativeMappedObject, ActivityMixin):
    """
    A group definition that records changes to the group
    """

    __tablename__ = 'tg_group'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    group_id = Column(Integer, primary_key=True)
    id = synonym('group_id')
    group_name = Column(Unicode(255), unique=True, nullable=False)
    display_name = Column(Unicode(255))
    _root_password = Column('root_password', String(255), nullable=True,
        default=None)
    ldap = Column(Boolean, default=False, nullable=False, index=True)
    created = Column(DateTime, default=datetime.utcnow)
    activity = relationship(GroupActivity, back_populates='object',
            cascade='all, delete-orphan')
    permissions = relationship('Permission', back_populates='groups',
            secondary=group_permission_table)
    system_assocs = relationship('SystemGroup', back_populates='group',
            cascade='all, delete-orphan')
    user_group_assocs = relationship('UserGroup', back_populates='group',
            cascade='all, delete-orphan')
    system_access_policy_rules = relationship('SystemAccessPolicyRule',
            back_populates='group', cascade='all, delete, delete-orphan')
    jobs = relationship('Job', back_populates='group', cascade_backrefs=False)

    activity_type = GroupActivity

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(group_name=name).one()

    @classmethod
    def by_id(cls, id):
        with convert_db_lookup_error('No group with ID: %s' % id):
            return cls.query.filter_by(group_id=id).one()

    def __unicode__(self):
        return self.display_name

    def __str__(self):
        return unicode(self).encode('utf8')

    def __repr__(self):
        return 'Group(group_name=%r, display_name=%r)' % (self.group_name, self.display_name)

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

    @property
    def root_password(self):
        """
        returns password
        """
        return self._root_password

    @root_password.setter
    def root_password(self, password):
        """Set group job password

           Set the root password to be used by group jobs.

        """
        if password:
            try:
                # If you change VeryFascistCheck, please also modify
                # bkr.server.validators.StrongPassword
                cracklib.VeryFascistCheck(password)
            except ValueError, msg:
                msg = re.sub(r'^it is', 'the password is', str(msg))
                raise ValueError(msg)
            else:
                self._root_password = password
        else:
            self._root_password = None


    def owners(self):
        return UserGroup.query.filter_by(group_id=self.group_id,
                                         is_owner=True).all()

    def has_owner(self, user):
        if user is None:
            return False
        return bool(UserGroup.query.filter_by(group_id=self.group_id,
                user_id=user.user_id, is_owner=True).count())

    def can_edit(self, user):
        return self.has_owner(user) or user.is_admin()

    def can_remove_member(self, user, member_id):
        if user.is_admin():
            if self.group_name == 'admin':
                if len(self.users)==1:
                    return False
        else:
            group_owners = self.owners()
            if len(group_owners)==1 and group_owners[0].user_id == int(member_id):
                return False

        return True

    def is_protected_group(self):
        """Some group names are predefined by Beaker and cannot be modified"""
        return self.group_name in (u'admin', u'queue_admin', u'lab_controller')

    def set_root_password(self, user, service, password):
        if self.root_password != password:
            self.root_password = password
            self.record_activity(user=user, service=service,
                field=u'Root Password', old='*****', new='*****')

    def set_name(self, user, service, group_name):
        """Set a group's name and record any change as group activity

        Passing None or the empty string means "leave this value unchanged"
        """
        old_group_name = self.group_name
        if group_name and group_name != old_group_name:
            if self.is_protected_group():
                raise BX(_(u'Cannot rename protected group %r as %r'
                                              % (old_group_name, group_name)))
            self.group_name = group_name
            self.record_activity(user=user, service=service,
                                 field=u'Name',
                                 old=old_group_name, new=group_name)

    def set_display_name(self, user, service, display_name):
        """Set a group's display name and record any change as group activity

        Passing None or the empty string means "leave this value unchanged"
        """
        old_display_name = self.display_name
        if display_name and display_name != old_display_name:
            self.display_name = display_name
            self.record_activity(user=user, service=service,
                                 field=u'Display Name',
                                 old=old_display_name, new=display_name)

    def can_modify_membership(self, user):
        return not self.ldap and (self.has_owner(user) or user.is_admin())

    def refresh_ldap_members(self, ldapcon=None):
        """Refresh the group from LDAP and record changes as group activity"""
        assert self.ldap
        assert get('identity.ldap.enabled', False)
        if ldapcon is None:
            ldapcon = ldap.initialize(get('identity.soldapprovider.uri'))
        log.debug('Refreshing LDAP group %s' % self.group_name)
        existing = set(self.users)
        refreshed = set(self._ldap_members(ldapcon))
        added_members = refreshed.difference(existing)
        removed_members = existing.difference(refreshed)
        for user in removed_members:
            log.debug('Removing %r from %r', user, self)
            self.users.remove(user)
            self.activity.append(GroupActivity(user=None, service=u'LDAP',
                    action=u'Removed', field_name=u'User',
                    old_value=user.user_name, new_value=None))
        for user in added_members:
            log.debug('Adding %r to %r', user, self)
            self.users.append(user)
            self.activity.append(GroupActivity(user=None, service=u'LDAP',
                    action=u'Added', field_name=u'User', old_value=None,
                    new_value=user.user_name))

    def _ldap_members(self, ldapcon):
        # Supports only RFC2307 style, with group members listed by username in
        # the memberUid attribute.
        filter = ldap.filter.filter_format(
                '(&(cn=%s)(objectClass=posixGroup))', [self.group_name])
        result = ldapcon.search_st(get('identity.soldapprovider.basedn', ''),
                ldap.SCOPE_SUBTREE, filter,
                timeout=get('identity.soldapprovider.timeout', 20))
        if not result:
            log.warning('LDAP group %s not found in LDAP directory', self.group_name)
            return []
        dn, attrs = result[0] # should never be more than one result
        users = []
        for username in attrs.get('memberUid', []):
            log.debug('LDAP group %s has member %s', self.group_name, username)
            user = User.by_user_name(username.decode('utf8'))
            if user is not None:
                users.append(user)
        return users

    systems = association_proxy('system_assocs', 'system',
            creator=lambda system: SystemGroup(system=system))

    users = association_proxy('user_group_assocs','user',
            creator=lambda user: UserGroup(user=user))

class UserGroup(DeclarativeMappedObject):

    __tablename__ = 'user_group'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True, index=True)
    user = relationship(User, back_populates='group_user_assocs')
    group_id = Column(Integer, ForeignKey('tg_group.group_id',
            onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True, index=True)
    group = relationship(Group, back_populates='user_group_assocs')
    is_owner = Column(Boolean, nullable=False, default=False)

class Permission(DeclarativeMappedObject):
    """
    A relationship that determines what each Group can do
    """

    __tablename__ = 'permission'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    permission_id = Column(Integer, primary_key=True)
    permission_name = Column(Unicode(16), unique=True)
    description = Column(Unicode(255))
    groups = relationship(Group, back_populates='permissions',
            secondary=group_permission_table)

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

class SystemGroup(DeclarativeMappedObject):

    __tablename__ = 'system_group'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    system_id = Column(Integer, ForeignKey('system.id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True, index=True)
    system = relationship('System', back_populates='group_assocs')
    group_id = Column(Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True, index=True)
    group = relationship(Group, back_populates='system_assocs')

class SSHPubKey(DeclarativeMappedObject):

    __tablename__ = 'sshpubkey'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    user = relationship(User, back_populates='sshpubkeys')
    keytype = Column(Unicode(16), nullable=False)
    pubkey = Column(UnicodeText, nullable=False)
    ident = Column(Unicode(63), nullable=False)

    def __init__(self, keytype, pubkey, ident):
        super(SSHPubKey, self).__init__()
        self.keytype = keytype
        self.pubkey = pubkey
        self.ident = ident

    def __repr__(self):
        return "%s %s %s" % (self.keytype, self.pubkey, self.ident)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()
