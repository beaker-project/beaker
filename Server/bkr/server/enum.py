
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This is based on Mike Bayer's declarative enum recipe:
# http://techspot.zzzeek.org/2011/01/14/the-enum-recipe/
# with the following differences:
#   - allow arbitrary attributes on EnumSymbol
#   - iteration of symbols is in the same order as they were declared
#   - for convenience str/unicode bind parameters are acceptable as well as 
#     enum symbols, so that it's possible to do things like:
#       Recipe.status == u'New'

from sqlalchemy.types import SchemaType, TypeDecorator, Enum
import re

class EnumSymbol(object):
    """Define a fixed symbol tied to a parent class."""

    def __init__(self, cls_, name, value, **kwargs):
        self.cls_ = cls_
        self.name = name # in Python land
        self.value = value # in DB land
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def __reduce__(self):
        """Allow unpickling to return the symbol
        linked to the DeclEnum class."""
        return getattr, (self.cls_, self.name)

    def __repr__(self):
        return '%s.%s' % (self.cls_.__name__, self.name)

    def __str__(self):
        return self.value.encode('utf8')

    def __unicode__(self):
        return self.value

    def __json__(self):
        return self.value

class EnumMeta(type):
    """Generate new DeclEnum classes."""

    def __init__(cls, classname, bases, dict_):
        cls._symbols = list(cls._symbols)
        cls._symbols_by_value = cls._symbols_by_value.copy()
        for name, value, attrs in dict_.get('symbols', []):
            sym = EnumSymbol(cls, name, value, **attrs)
            cls._symbols.append(sym)
            cls._symbols_by_value[value] = sym
            setattr(cls, name, sym)
        type.__init__(cls, classname, bases, dict_)

    def __iter__(cls):
        return iter(cls._symbols)

class DeclEnum(object):
    """Declarative enumeration."""

    __metaclass__ = EnumMeta
    _symbols = []
    _symbols_by_value = {}

    @classmethod
    def from_string(cls, value):
        try:
            return cls._symbols_by_value[value]
        except KeyError:
            raise ValueError(u'Invalid value for %s: %r is not one of %s'
                    % (cls.__name__, value,
                       ', '.join(value for value in cls.values())))

    @classmethod
    def values(cls):
        return [symbol.value for symbol in cls._symbols]

    @classmethod
    def db_type(cls):
        return DeclEnumType(cls)

    def __init__(self):
        raise TypeError('DeclEnum subclasses are not instantiable')

    @classmethod
    def index(cls, symbol):
        return cls._symbols.index(symbol)

    @classmethod
    def by_index(cls, index):
        return cls._symbols[index]

class DeclEnumType(SchemaType, TypeDecorator):

    def __init__(self, enum):
        self.enum = enum
        # convert CamelCase to underscore_separated
        name = re.sub('.([A-Z])', lambda m: '_' + m.group(1).lower(), enum.__name__).lower()
        self.impl = Enum(*enum.values(), name=name)

    def _set_table(self, table, column):
        self.impl._set_table(table, column)

    def copy(self):
        return DeclEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, basestring):
            return value
        if value.cls_ != self.enum:
            raise TypeError('Cannot use %r as bind parameter for column '
                    'of type %r' % (value, self.enum))
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum.from_string(value.strip())
