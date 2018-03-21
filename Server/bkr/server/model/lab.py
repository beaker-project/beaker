
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import urllib
from sqlalchemy import (Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime, event)
from sqlalchemy.orm import relationship, synonym, validates
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.util import is_valid_fqdn
from .base import DeclarativeMappedObject
from .types import SystemSchedulerStatus
from .activity import Activity, ActivityMixin
from .identity import User

log = logging.getLogger(__name__)

class LabControllerActivity(Activity):

    __tablename__ = 'lab_controller_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id'),
            nullable=False, index=True)
    object_id = synonym('lab_controller_id')
    object = relationship('LabController', back_populates='activity')
    __mapper_args__ = {'polymorphic_identity': u'lab_controller_activity'}

    def object_name(self):
        return 'LabController: %s' % self.object.fqdn

    def __json__(self):
        result = super(LabControllerActivity, self).__json__()
        result['lab_controller'] = {'fqdn': self.object.fqdn}
        return result

class LabController(DeclarativeMappedObject, ActivityMixin):

    __tablename__ = 'lab_controller'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    fqdn = Column(Unicode(255), unique=True)
    disabled = Column(Boolean, nullable=False, default=False)
    removed = Column(DateTime, nullable=True, default=None)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'),
            nullable=False, unique=True)
    user = relationship(User, back_populates='lab_controller')
    write_activity = relationship(LabControllerActivity, lazy='noload')
    activity = relationship(LabControllerActivity, back_populates='object',
            cascade='all, delete',
            order_by=[LabControllerActivity.created.desc(), LabControllerActivity.id.desc()])
    _distro_trees = relationship('LabControllerDistroTree',
            cascade='all, delete-orphan', back_populates='lab_controller')
    systems = relationship('System', back_populates='lab_controller')
    openstack_regions = relationship('OpenStackRegion', back_populates='lab_controller')

    activity_type = LabControllerActivity

    def __repr__(self):
        return "%s" % (self.fqdn)

    def __json__(self):
        return {
            'id': self.id,
            'fqdn': self.fqdn,
            'disabled': bool(self.disabled),
            'is_removed': bool(self.removed),
            'removed': self.removed,
            'user_name': self.user.user_name,
            'email_address': self.user.email_address,
            'display_name': self.user.display_name,
        }

    @classmethod
    def by_id(cls, id):
        try:
            return cls.query.filter_by(id=id).one()
        except NoResultFound:
            raise ValueError('No lab controller with id %r' % id)

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

    def can_edit(self, user):
        return user.is_admin()

    @property
    def href(self):
        """Returns a relative URL."""
        return urllib.quote((u'/labcontrollers/%s' % self.fqdn).encode('utf8'))

    @validates('fqdn')
    def validate_fqdn(self, key, fqdn):
        if not fqdn:
            raise ValueError('Lab controller FQDN must not be empty')
        if not is_valid_fqdn(fqdn):
            raise ValueError('Invalid FQDN for lab controller: %s' % fqdn)
        return fqdn

@event.listens_for(LabController.disabled, 'set')
def mark_systems_pending_when_enabled(labcontroller, new_value, old_value, initiator):
    if new_value is True:
        for system in labcontroller.systems:
            if system.scheduler_status == SystemSchedulerStatus.idle:
                log.debug('Idle system %s is in newly enabled lab %s, flagging it for scheduling',
                          system, labcontroller)
                system.scheduler_status = SystemSchedulerStatus.pending
