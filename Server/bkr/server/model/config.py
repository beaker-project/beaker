
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime
from sqlalchemy import (Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime, TEXT)
from sqlalchemy.sql import and_
from sqlalchemy.orm import relationship
from turbogears.database import session
from bkr.server import identity
from bkr.server.bexceptions import BX
from .base import DeclarativeMappedObject

class ConfigItem(DeclarativeMappedObject):

    __tablename__ = 'config_item'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), unique=True)
    description = Column(Unicode(255))
    numeric = Column(Boolean, default=False)
    readonly = Column(Boolean, default=False)

    @classmethod
    def lazy_create(cls, name, description, numeric):
        return super(ConfigItem, cls).lazy_create(name=name,
                _extra_attrs=dict(description=description, numeric=numeric))

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
            except AttributeError:
                raise BX(_('Settings may not be changed anonymously'))
        if valid_from:
            if valid_from < datetime.utcnow():
                raise BX(_('%s is in the past') % valid_from)
        self.value_class(self, value, user, valid_from)

class ConfigValueString(DeclarativeMappedObject):

    __tablename__ = 'config_value_string'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    config_item_id = Column(Integer, ForeignKey('config_item.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    config_item = relationship(ConfigItem)
    modified = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'), nullable=False)
    user = relationship('User', back_populates='config_values_string')
    valid_from = Column(DateTime, default=datetime.utcnow)
    value = Column(TEXT, nullable=True)

    def __init__(self, config_item, value, user, valid_from=None):
        super(ConfigValueString, self).__init__()
        self.config_item = config_item
        self.value = value
        self.user = user
        if valid_from:
            self.valid_from = valid_from

    def __json__(self):
        return {
            'id': self.id,
            'value': self.value,
            'modified': self.modified,
            'valid_from': self.valid_from,
        }

class ConfigValueInt(DeclarativeMappedObject):

    __tablename__ = 'config_value_int'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    config_item_id = Column(Integer, ForeignKey('config_item.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    config_item = relationship(ConfigItem)
    modified = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'), nullable=False)
    user = relationship('User', back_populates='config_values_int')
    valid_from = Column(DateTime, default=datetime.utcnow)
    value = Column(Integer, nullable=True)

    def __init__(self, config_item, value, user, valid_from=None):
        super(ConfigValueInt, self).__init__()
        self.config_item = config_item
        self.value = value
        self.user = user
        if valid_from:
            self.valid_from = valid_from

    def __json__(self):
        return {
            'id': self.id,
            'value': self.value,
            'modified': self.modified,
            'valid_from': self.valid_from,
        }
