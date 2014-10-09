# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make user_group.is_owner non-NULLable

Revision ID: 23c1263e8988
Revises: 38c273108088
Create Date: 2014-10-09 14:48:13.114158

"""

# revision identifiers, used by Alembic.
revision = '23c1263e8988'
down_revision = '38c273108088'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('user_group', 'is_owner',
            existing_type=sa.Boolean,
            nullable=False)

def downgrade():
    pass # no downgrade because we are fixing an upgrade
