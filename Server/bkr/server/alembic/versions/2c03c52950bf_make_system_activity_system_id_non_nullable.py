# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make system_activity.system_id non-NULLable

Revision ID: 2c03c52950bf
Revises: 0f76d2e424d0
Create Date: 2014-10-10 13:01:37.077408

"""

# revision identifiers, used by Alembic.
revision = '2c03c52950bf'
down_revision = '0f76d2e424d0'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import drop_fk

def upgrade():
    drop_fk('system_activity', ['system_id'])
    op.alter_column('system_activity', 'system_id',
            existing_type=sa.Integer, nullable=False)
    op.create_foreign_key(None, 'system_activity', 'system',
                ['system_id'], ['id'])

def downgrade():
    op.alter_column('system_activity', 'system_id',
            existing_type=sa.Integer, nullable=True)
