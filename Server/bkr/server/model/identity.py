
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
from sqlalchemy.orm import mapper, relation, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.config import get
from turbogears.database import session, metadata
from bkr.server.bexceptions import BX, NoChangeException
from .base import DeclarativeMappedObject, MappedObject
from .activity import Activity, ActivityMixin
from .config import ConfigItem, ConfigValueInt, ConfigValueString

log = logging.getLogger(__name__)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(255), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', UnicodeText, nullable=True, default=None),
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
    Column('is_owner', Boolean, nullable=False, default=False),
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
    mysql_engine='InnoDB',
)

group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    mysql_engine='InnoDB',
)

group_activity_table = Table('group_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('tg_group.group_id'),
        nullable=False),
    mysql_engine='InnoDB',
)

user_activity_table = Table('user_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'),
        nullable=False),
    mysql_engine='InnoDB'
)

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


class User(MappedObject, ActivityMixin):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """

    # XXX we probably shouldn't be doing this!
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    @property
    def activity_type(self):
        return UserActivity

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
        ldapenabled = get('identity.ldap.enabled', False)
        autocreate = get('identity.soldapprovider.autocreate', False)
        # Presence of '/' indicates a Kerberos service principal.
        if not user and ldapenabled and autocreate and '/' not in user_name:
            filter = ldap.filter.filter_format('(uid=%s)', [user_name])
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
            user = User()
            user.user_name = user_name
            user.display_name = objects[0][1]['cn'][0].decode('utf8')
            user.email_address = objects[0][1]['mail'][0].decode('utf8')
            session.add(user)
            session.flush()
        return user

    @classmethod
    def list_by_name(cls, username,find_anywhere=False,find_ldap_users=True):
        ldap_users = []
        ldapenabled = get('identity.ldap.enabled', False)
        if ldapenabled and find_ldap_users is True:
            filter = ldap.filter.filter_format('(uid=%s*)', [username])
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
        self._password = self._password_context.encrypt(raw_password)

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

        verified, new_hash = self._password_context.verify_and_update(
                raw_password, self._password)
        if verified:
            if new_hash:
                log.info('Upgrading obsolete password hash for user %s', self)
                # replace obsolete hash with new one
                self._password = new_hash
            return True

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


class UserGroup(MappedObject):
    pass


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

class Group(DeclarativeMappedObject, ActivityMixin):
    """
    A group definition that records changes to the group
    """

    __tablename__ = 'tg_group'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    group_id = Column(Integer, primary_key=True)
    group_name = Column(Unicode(255), unique=True, nullable=False)
    display_name = Column(Unicode(255))
    _root_password = Column('root_password', String(255), nullable=True,
        default=None)
    ldap = Column(Boolean, default=False, nullable=False, index=True)
    created = Column(DateTime, default=datetime.utcnow)

    @property
    def activity_type(self):
        return GroupActivity

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(group_name=name).one()

    @classmethod
    def by_id(cls, id):
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

class SystemGroup(MappedObject):

    pass

class GroupActivity(Activity):
    def object_name(self):
        return "Group: %s" % self.object.display_name

class UserActivity(Activity):
    def object_name(self):
        return "User: %s" % self.object.display_name

class SSHPubKey(MappedObject):
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

mapper(User, users_table,
        properties={
      '_password' : users_table.c.password,
      '_root_password' : users_table.c.root_password,
      'submission_delegates': relation(User, secondary=SubmissionDelegate.__table__,
          primaryjoin=users_table.c.user_id == SubmissionDelegate.user_id,
          secondaryjoin=users_table.c.user_id == SubmissionDelegate.delegate_id),
      'activity': relation(Activity, backref='user'),
      'config_values_int': relation(ConfigValueInt, backref='user'),
      'config_values_string': relation(ConfigValueString, backref='user'),
})

mapper(UserGroup, user_group_table, properties={
        'group': relation(Group, backref=backref('user_group_assocs', cascade='all, delete-orphan')),
        'user': relation(User, backref=backref('group_user_assocs', cascade='all, delete-orphan'))
        })

mapper(SystemGroup, system_group_table, properties={
    'group': relation(Group, backref=backref('system_assocs', cascade='all, delete-orphan')),
})

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))

mapper(GroupActivity, group_activity_table, inherits=Activity,
        polymorphic_identity=u'group_activity',
        properties=dict(object=relation(Group, uselist=False,
                        backref=backref('activity', cascade='all, delete-orphan'))))

mapper(UserActivity, user_activity_table, inherits=Activity,
        polymorphic_identity=u'user_activity',
        properties=dict(object=relation(User, uselist=False, backref='user_activity')))

mapper(SSHPubKey, sshpubkey_table,
        properties=dict(user=relation(User, uselist=False, backref='sshpubkeys')))
