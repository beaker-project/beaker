
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Utility functions for use in Alembic migration scripts.
"""

from alembic import op
import sqlalchemy as sa

def create_fk_if_absent(source_table, dest_table, source_columns, dest_columns):
    fks = sa.inspect(op.get_bind()).get_foreign_keys(source_table)
    if not any(fk['constrained_columns'] == source_columns for fk in fks):
        op.create_foreign_key(None, source_table, dest_table,
                source_columns, dest_columns)

def find_unique(table, columns):
    """
    Returns the string name of the unique constraint which applies to the given 
    columns, or None if no matching constraint exists.
    """
    unique_info = None
    for info in sa.inspect(op.get_bind()).get_unique_constraints(table):
        if info['column_names'] == columns:
            unique_info = info
            break
    if unique_info:
        return unique_info['name']
    else:
        return None

def create_unique_if_absent(name, table, columns):
    if find_unique(table, columns) is None:
        op.create_unique_constraint(name, table, columns)

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
