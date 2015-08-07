
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import urllib
from sqlalchemy import (Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime)
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.orm.exc import NoResultFound
from .base import DeclarativeMappedObject
from .activity import Activity, ActivityMixin
from .identity import User

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
