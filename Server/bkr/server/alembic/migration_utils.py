
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Utility functions for use in Alembic migration scripts.
"""

from alembic import op
import sqlalchemy as sa

# When altering a MySQL ENUM column to add a new value, we can only add it at 
# the end. Similarly values can only be removed from the end. The enum values 
# must not be re-ordered, otherwise it will change the data stored in the 
# column(!).
# So when adding/removing enum values, we first use SA inspect() to determine 
# the existing enum values, so that the order is preserved when we issue the 
# ALTER TABLE.

def add_enum_value(table, column, value, **kwargs):
    column_info = None
    for info in sa.inspect(op.get_bind()).get_columns(table):
        if info['name'] == column:
            column_info = info
            break
    if not column_info:
        raise AssertionError('%s.%s does not exist' % (table, column))
    column_info, = [info for info in sa.inspect(op.get_bind()).get_columns(table)
            if info['name'] == column]
    existing_enum_values = column_info['type'].enums
    new_enum_values = existing_enum_values + (value,)
    op.alter_column(table, column,
            existing_type=column_info['type'],
            type_=sa.Enum(*new_enum_values),
            **kwargs)

def drop_enum_value(table, column, value, **kwargs):
    column_info = None
    for info in sa.inspect(op.get_bind()).get_columns(table):
        if info['name'] == column:
            column_info = info
            break
    if not column_info:
        raise AssertionError('%s.%s does not exist' % (table, column))
    existing_enum_values = column_info['type'].enums
    if existing_enum_values[-1] != value:
        raise AssertionError('Expecting to drop enum value %r from %s.%s, '
                'but it is not the last value in the sequence! '
                'Enum values are: %r' % (value, table, column, existing_enum_values))
    new_enum_values = existing_enum_values[:-1]
    op.alter_column(table, column,
            existing_type=column_info['type'],
            type_=sa.Enum(*new_enum_values),
            **kwargs)
