# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Index map tables' first columns

This is ultimately a side-effect of commit ca7c56e6 for bug 642834.

Revision ID: 2d4258bf3f16
Revises: 23c1263e8988
Create Date: 2014-10-10 11:06:31.596165

"""

# revision identifiers, used by Alembic.
revision = '2d4258bf3f16'
down_revision = '23c1263e8988'

from alembic import op
import sqlalchemy as sa

def upgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('system_group')
    if not any(index['column_names'] == ['system_id'] for index in indexes):
        op.create_index('ix_system_group_system_id', 'system_group', ['system_id'])
    indexes = sa.inspect(op.get_bind()).get_indexes('osversion_arch_map')
    if not any(index['column_names'] == ['osversion_id'] for index in indexes):
        op.create_index('ix_osversion_arch_map_osversion_id',
                'osversion_arch_map', ['osversion_id'])
    indexes = sa.inspect(op.get_bind()).get_indexes('group_permission')
    if not any(index['column_names'] == ['group_id'] for index in indexes):
        op.create_index('ix_group_permission_group_id',
                'group_permission', ['group_id'])
    indexes = sa.inspect(op.get_bind()).get_indexes('system_arch_map')
    if not any(index['column_names'] == ['system_id'] for index in indexes):
        op.create_index('ix_system_arch_map_system_id',
                'system_arch_map', ['system_id'])
    indexes = sa.inspect(op.get_bind()).get_indexes('system_device_map')
    if not any(index['column_names'] == ['system_id'] for index in indexes):
        op.create_index('ix_system_device_map_system_id',
                'system_device_map', ['system_id'])
    indexes = sa.inspect(op.get_bind()).get_indexes('user_group')
    if not any(index['column_names'] == ['user_id'] for index in indexes):
        op.create_index('ix_user_group_user_id',
                'user_group', ['user_id'])

def downgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('system_group')
    if any(index['name'] == 'ix_tg_user_email_address' for index in indexes):
        op.drop_index('ix_system_group_system_id', 'system_group')
    indexes = sa.inspect(op.get_bind()).get_indexes('osversion_arch_map')
    if any(index['name'] == 'ix_osversion_arch_map_osversion_id' for index in indexes):
        op.drop_index('ix_osversion_arch_map_osversion_id', 'osversion_arch_map')
    indexes = sa.inspect(op.get_bind()).get_indexes('group_permission')
    if any(index['name'] == 'ix_group_permission_group_id' for index in indexes):
        op.drop_index('ix_group_permission_group_id', 'group_permission')
    indexes = sa.inspect(op.get_bind()).get_indexes('system_arch_map')
    if any(index['name'] == 'ix_system_arch_map_system_id' for index in indexes):
        op.drop_index('ix_system_arch_map_system_id', 'system_arch_map')
    indexes = sa.inspect(op.get_bind()).get_indexes('system_device_map')
    if any(index['name'] == 'ix_system_device_map_system_id' for index in indexes):
        op.drop_index('ix_system_device_map_system_id', 'system_device_map')
    indexes = sa.inspect(op.get_bind()).get_indexes('user_group')
    if any(index['name'] == 'ix_user_group_user_id' for index in indexes):
        op.drop_index('ix_user_group_user_id', 'user_group')
