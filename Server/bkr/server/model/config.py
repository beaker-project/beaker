
from datetime import datetime
from sqlalchemy import (Table, Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime, TEXT)
from sqlalchemy.sql import and_
from sqlalchemy.orm import mapper, relation
from turbogears.database import session, metadata
from bkr.server import identity
from bkr.server.bexceptions import BX
from .base import MappedObject

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
            except AttributeError:
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

mapper(ConfigItem, config_item_table)
mapper(ConfigValueInt, config_value_int_table,
       properties = {'config_item': relation(ConfigItem, uselist=False)})
mapper(ConfigValueString, config_value_string_table,
       properties = {'config_item': relation(ConfigItem, uselist=False)})
