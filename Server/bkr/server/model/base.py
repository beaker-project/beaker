
import logging
import random
import time
from turbogears.database import metadata, session
from sqlalchemy.sql import and_
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import class_mapper
from sqlalchemy.ext.declarative import declarative_base
from .sql import ConditionalInsert

log = logging.getLogger(__name__)

def decl_base_constructor(self, **kwargs):
    """
    This is a cut and paste from sqlalchemy.ext.declarative._declarative_constructor
    however we are copying it here to ensure behaviour does not
    change and chain up the MRO.
    DeclBase should be used in the following manner
    DecalrativeClass(DeclBase, MappedObject) and in this
    way we avoid adding to the session in MappedObject.__init__.

    Once MappedObject.__init__ no longer calls session.add(), this
    can be removed.
    """
    cls_ = type(self)
    for k in kwargs:
        if not hasattr(cls_, k):
            raise TypeError(
                "%r is an invalid keyword argument for %s" %
                (k, cls_.__name__))
        setattr(self, k, kwargs[k])

DeclBase = declarative_base(constructor=decl_base_constructor,
                            metadata=metadata)

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
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        # XXX Calling session.add(self) here is a bad idea! We only do it 
        # because it was inherited from TurboGears 1.0 a long time ago. If 
        # something causes the session to be flushed (for example lazy_create) 
        # we could end up trying to persist an object which has not been fully 
        # populated yet. See bug 869455 for an example of this.
        # Beware that some classes are already opting out of this behaviour by 
        # not chaining up to this __init__ method. We should work towards 
        # eliminating it completely.
        session.add(self)

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
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

class SystemObject(MappedObject):
    @classmethod
    def get_tables(cls):
        tables = cls.get_dict().keys()
        tables.sort()
        return tables

    @classmethod
    def get_dict(cls):
        tables = dict( system = dict(joins=[], cls=cls))
        for property in cls.mapper.iterate_properties:
            mapper = getattr(property, 'mapper', None)
            if mapper:
                remoteTables = {}
                try:
                    remoteTables = property.mapper.class_._get_dict()
                except Exception: pass
                for key in remoteTables.keys():
                    joins = [property.key]
                    joins.extend(remoteTables[key]['joins'])
                    tables['system/%s/%s' % (property.key, key)] = dict(joins=joins, cls=remoteTables[key]['cls'])

                tables['system/%s' % property.key] = dict(joins=[property.key], cls=property.mapper.class_)
        return tables

    def _get_dict(cls):
        tables = {}
        for property in cls.mapper.iterate_properties:
            mapper = getattr(property, 'mapper', None)
            if mapper:
                remoteTables = {}
                try:
                    remoteTables = property.mapper.class_._get_dict()
                except Exception: pass
                for key in remoteTables.keys():
                    joins = [property.key]
                    joins.extend(remoteTables[key]['joins'])
                    tables['%s/%s' % (property.key, key)] = dict(joins=joins, cls=remoteTables[key]['cls'])
                tables[property.key] = dict(joins=[property.key], cls=property.mapper.class_)
        return tables
    _get_dict = classmethod(_get_dict)

    def get_fields(cls, lookup=None):
        if lookup:
            dict_lookup = cls.get_dict()
            return dict_lookup[lookup]['cls'].get_fields()
        return cls.mapper.c.keys()
    get_fields = classmethod(get_fields)
