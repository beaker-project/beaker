
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import random
import time
from turbogears.database import metadata, session
from sqlalchemy import util
from sqlalchemy.sql import and_
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import class_mapper, object_mapper, ColumnProperty
from sqlalchemy.ext.declarative import declarative_base
from .sql import ConditionalInsert

log = logging.getLogger(__name__)

class MappedObject(object):

    query = session.query_property()

    @classmethod
    def lazy_create(cls, _extra_attrs={}, **kwargs):
        """
        Returns the instance identified by the given uniquely-identifying 
        attributes. If it doesn't exist yet, it is inserted first.

        _extra_attrs is for attributes which do not make up the unique 
        identity, but which need to be specified during creation because they 
        are not NULLable. Subclasses should override this and pass attributes 
        up in _extra_attrs if needed.

        BEWARE: this method bypasses SQLAlchemy's ORM machinery. Pass column 
        properties instead of relationship properties (for example, osmajor_id 
        not osmajor).
        """
        # scan the class for any validators that need triggering
        for key, method in util.iterate_attributes(cls):
            if hasattr(method, '__sa_validators__'):
                for arg_key, arg_val in kwargs.iteritems():
                    if arg_key in method.__sa_validators__:
                        method(cls, arg_key, arg_val)

        # We do a conditional INSERT, which will always succeed or
        # silently have no effect.
        # http://stackoverflow.com/a/6527838/120202
        # Note that (contrary to that StackOverflow answer) on InnoDB the 
        # INSERT must come before the UPDATE to avoid deadlocks.
        unique_params = {}
        extra_params = {}
        assert len(class_mapper(cls).tables) == 1
        table = class_mapper(cls).tables[0]
        for k, v in kwargs.iteritems():
            unique_params[table.c[k]] = v
        for k, v in _extra_attrs.iteritems():
            extra_params[table.c[k]] = v
        succeeded = False
        for attempt in range(1, 7):
            if attempt > 1:
                delay = random.uniform(0.001, 0.1)
                log.debug('Backing off %0.3f seconds for insertion into table %s' % (delay, table))
                time.sleep(delay)
            try:
                session.connection(cls).execute(ConditionalInsert(table,
                    unique_params, extra_params))
                succeeded = True
                break
            except OperationalError, e:
                # This seems like a reasonable way to check the string.
                # We could use a regex, but this is more straightforward.
                # XXX MySQL-specific
                if '(OperationalError) (1213' not in unicode(e):
                    raise
        if not succeeded:
            log.debug('Exhausted maximum attempts of conditional insert')
            raise e

        if extra_params:
            session.connection(cls).execute(table.update()
                    .values(extra_params)
                    .where(and_(*[col == value for col, value in unique_params.iteritems()])))

        return cls.query.with_lockmode('update').filter_by(**kwargs).one()

    def __init__(self, **kwargs):
        for prop in object_mapper(self).iterate_properties:
            if not isinstance(prop, ColumnProperty):
                continue # not sure what to do with it
            default = prop.columns[0].default
            if default is None:
                continue
            if default.is_callable:
                # We only use nullary default callables, which don't accept an 
                # ExecutionContext instance, but SQLAlchemy wraps them all to 
                # accept (and ignore) an ExecutionContext for consistency. We 
                # can just pass None.
                default_value = default.arg(None)
            else:
                default_value = default.arg
            setattr(self, prop.key, default_value)
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

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

    @classmethod
    def by_id(cls, id, lockmode=False):
        return cls.query.filter_by(id=id).with_lockmode(lockmode).one()

DeclarativeMappedObject = declarative_base(cls=MappedObject, metadata=metadata, constructor=None)
