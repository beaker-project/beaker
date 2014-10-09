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
from bkr.server.alembic.migration_utils import add_enum_value, drop_enum_value

def upgrade():
    add_enum_value('system_access_policy_rule', 'permission',
            'view_power', nullable=False)

def downgrade():
    op.execute("DELETE FROM system_access_policy_rule WHERE permission = 'view_power'")
    drop_enum_value('system_access_policy_rule', 'permission',
            'view_power', nullable=True)
