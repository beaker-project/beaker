
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Unicode
from sqlalchemy.orm import object_mapper, relationship
from turbogears.database import session
from bkr.server import identity
from .base import DeclarativeMappedObject

log = logging.getLogger(__name__)

class Activity(DeclarativeMappedObject):

    __tablename__ = 'activity'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey('tg_user.user_id'), index=True)
    user = relationship('User', back_populates='activity')
    created = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    type = Column(Unicode(40), nullable=False, index=True)
    field_name = Column(Unicode(40), nullable=False, index=True)
    service = Column(Unicode(100), nullable=False, index=True)
    action = Column(Unicode(40), nullable=False, index=True)
    old_value = Column(Unicode(60))
    new_value = Column(Unicode(60))
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': u'activity'}

    def __init__(self, user=None, service=None, action=None,
                 field_name=None, old_value=None, new_value=None, **kw):
        """
        The *service* argument should be a string such as 'Scheduler' or 
        'XMLRPC', describing the means by which the change has been made. This 
        constructor will override it with something more specific (such as the 
        name of an external service) if appropriate.
        """
        super(Activity, self).__init__(**kw)
        self.user = user
        self.service = service
        try:
            if identity.current.proxied_by_user is not None:
                self.service = identity.current.proxied_by_user.user_name
        except identity.RequestRequiredException:
            pass

        field_name_value_max_length = object_mapper(self).c.field_name.type.length
        old_value_max_length        = object_mapper(self).c.old_value.type.length
        new_value_max_length        = object_mapper(self).c.new_value.type.length
        self.field_name = field_name[:field_name_value_max_length]
        self.action = action

        if old_value is not None:
            old_value = unicode(old_value)[:old_value_max_length]
        if new_value is not None:
            new_value = unicode(new_value)[:new_value_max_length]

        self.old_value = old_value
        self.new_value = new_value

    def __json__(self):
        return {
            'id': self.id,
            'created': self.created,
            'user': self.user,
            'service': self.service,
            'action': self.action,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'type': self.type,
        }

    def __repr__(self):
        return ('%s(id=%r, object_id=%r, created=%r, user=%r, service=%r, '
                'action=%r, field_name=%r, old_value=%r, new_value=%r)'
                % (self.__class__.__name__, self.id, self.object_id,
                   self.created, self.user, self.service, self.action,
                   self.field_name, self.old_value, self.new_value))

    @classmethod
    def all(cls):
        return cls.query

    @property
    def object_id(self):
        return None

    def object_name(self):
        return None

class ActivityMixin(object):
    """Helper to create activity records and append them to an activity log

    Subclasses must have an "activity" attribute that references the relevant
    activity table, as well as an "activity_type" attribute that references
    the type of object to create for individual activities.
    """

    _fields = ('object_id', 'service', 'field', 'action', 'old', 'new', 'user')
    _field_fmt = ', '.join('{0}=%({0})r'.format(name) for name in _fields)
    _log_fmt = 'Tentative %(kind)s: ' + _field_fmt

    def record_activity(self, **kwds):
        """Helper to record object activity to the relevant history log.

        For readability at call sites, only accepts keyword arguments:

        *service* - service used to trigger the activity (required)
        *field* - which field was affected by the activity (required)
        *action* - what activity occurred (default is "Changed")
        *old* - field value before the activity (if applicable)
        *new* - field value before the activity (if applicable)
        *user* - user responsible for activity (if applicable)

        The default action is "Changed".
        Activities where the old and new values are the same are permitted
        """
        # This trick of using an inner functions lets us force the use of
        # keyword arguments without needing to do our own argument parsing
        return self._record_activity_inner(**kwds)

    def _record_activity_inner(self, service, field, action=u'Changed',
                               old=None, new=None, user=None):
        entry = self.activity_type(user, service, action=action,
                                   field_name=field,
                                   old_value=old, new_value=new, object=self)
        log_details = dict(kind=self.activity_type.__name__, user=user,
                           service=service, action=action,
                           field=field, old=old, new=new, object_id=self.id)
        log.debug(self._log_fmt, log_details)
        return entry

    @classmethod
    def record_bulk_activity(cls, query, **kwds):
        """
        Like record_activity, but pass a query of this class. The activity 
        record will be created against each row in the query.
        """
        cls._record_bulk_activity_inner(query, **kwds)

    @classmethod
    def _record_bulk_activity_inner(cls, query, service, field,
            action=u'Changed', old=None, new=None, user=None):
        for object_id, in query.values(cls.id):
            entry = cls.activity_type(user, service, action=action,
                    field_name=field, old_value=old, new_value=new,
                    object_id=object_id)
            log_details = dict(kind=cls.activity_type.__name__, user=user,
                               service=service, action=action,
                               field=field, old=old, new=new, object_id=object_id)
            log.debug(cls._log_fmt, log_details)
