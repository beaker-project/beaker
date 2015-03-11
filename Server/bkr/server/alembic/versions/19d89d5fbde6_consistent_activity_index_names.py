# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix index names on activity tables to be consistent

Revision ID: 19d89d5fbde6
Revises: 214c585364d9
Create Date: 2015-03-11 14:05:50.968300

"""

# revision identifiers, used by Alembic.
revision = '19d89d5fbde6'
down_revision = '214c585364d9'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import find_index

def rename_index_if_necessary(table, columns, expected_index_name):
    existing_index_name = find_index(table, columns)
    if not existing_index_name:
        raise RuntimeError('No index on %s %s' % (table, columns))
    if existing_index_name != expected_index_name:
        op.execute('ALTER TABLE %s DROP INDEX %s, ADD INDEX %s (%s)'
                % (table, existing_index_name,
                   expected_index_name, ', '.join(columns)))

def upgrade():
    rename_index_if_necessary('distro_activity', ['distro_id'],
            'ix_distro_activity_distro_id')
    rename_index_if_necessary('distro_tree_activity', ['distro_tree_id'],
            'ix_distro_tree_activity_distro_tree_id')
    rename_index_if_necessary('group_activity', ['group_id'],
            'ix_group_activity_group_id')
    rename_index_if_necessary('lab_controller_activity', ['lab_controller_id'],
            'ix_lab_controller_activity_lab_controller_id')
    rename_index_if_necessary('system_activity', ['system_id'],
            'ix_system_activity_system_id')

def downgrade():
    # No downgrade because the old index names were inconsistent, and aren't 
    # really important.
    pass
