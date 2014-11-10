
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy import (Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime)
from sqlalchemy.orm import relationship, backref, synonym
from sqlalchemy.orm.exc import NoResultFound
from turbogears.database import session
from .base import DeclarativeMappedObject
from .activity import Activity, ActivityMixin
from .identity import User

class LabControllerActivity(Activity):

    __tablename__ = 'lab_controller_activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, ForeignKey('activity.id'), primary_key=True)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id'), nullable=False)
    object_id = synonym('lab_controller_id')
    __mapper_args__ = {'polymorphic_identity': u'lab_controller_activity'}

    def object_name(self):
        return 'LabController: %s' % self.object.fqdn

class LabController(DeclarativeMappedObject, ActivityMixin):

    __tablename__ = 'lab_controller'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    fqdn = Column(Unicode(255), unique=True)
    disabled = Column(Boolean, nullable=False, default=False)
    removed = Column(DateTime, nullable=True, default=None)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'),
            nullable=False, unique=True)
    user = relationship(User, backref=backref('lab_controller', uselist=False))
    write_activity = relationship(LabControllerActivity, lazy='noload')
    activity = relationship(LabControllerActivity, backref='object',
            cascade='all, delete',
            order_by=[LabControllerActivity.created.desc(), LabControllerActivity.id.desc()])

    activity_type = LabControllerActivity

    def __repr__(self):
        return "%s" % (self.fqdn)

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
