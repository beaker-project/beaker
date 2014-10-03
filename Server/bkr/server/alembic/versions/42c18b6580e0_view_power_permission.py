# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""New view_power permission for systems

Revision ID: 42c18b6580e0
Revises: 50bc9c21974b
Create Date: 2014-10-01 17:17:28.553310

"""

# revision identifiers, used by Alembic.
revision = '42c18b6580e0'
down_revision = '50bc9c21974b'

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Blerg... we need to find the order of the existing enum values, to make 
    # sure we preserve that when we are adding our new 'view_power' value. The 
    # order will be different depending on whether the db was originally 
    # upgraded through version 0.16 or was created after that.
    column_info, = [info for info in
            sa.inspect(op.get_bind()).get_columns('system_access_policy_rule')
            if info['name'] == 'permission']
    existing_enum_values = column_info['type'].enums
    new_enum_values = existing_enum_values + ('view_power',)
    op.alter_column('system_access_policy_rule', 'permission',
            existing_type=column_info['type'],
            type_=sa.Enum(*new_enum_values),
            nullable=False)

def downgrade():
    op.execute("DELETE FROM system_access_policy_rule WHERE permission = 'view_power'")
    # As above we need to preserve the order of enum values, just dropping 
    # view_power from the final position.
    column_info, = [info for info in
            sa.inspect(op.get_bind()).get_columns('system_access_policy_rule')
            if info['name'] == 'permission']
    existing_enum_values = column_info['type'].enums
    assert existing_enum_values[-1] == 'view_power'
    new_enum_values = existing_enum_values[:-1]
    op.alter_column('system_access_policy_rule', 'permission',
            existing_type=column_info['type'],
            type_=sa.Enum(*new_enum_values),
            nullable=True)
