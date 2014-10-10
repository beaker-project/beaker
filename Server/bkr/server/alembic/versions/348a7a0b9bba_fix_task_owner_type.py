# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix task.owner type

Revision ID: 348a7a0b9bba
Revises: 4ef4b79523e8
Create Date: 2014-10-10 14:35:12.290370

"""

# revision identifiers, used by Alembic.
revision = '348a7a0b9bba'
down_revision = '4ef4b79523e8'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('task', 'owner', type_=sa.Unicode(255))

def downgrade():
    pass # no downgrade because we are fixing a mistake in an upgrade
