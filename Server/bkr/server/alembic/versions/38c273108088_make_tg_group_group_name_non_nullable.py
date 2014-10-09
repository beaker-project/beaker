# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make tg_group.group_name non-NULLable

Revision ID: 38c273108088
Revises: 23cbe32ac74e
Create Date: 2014-10-09 14:40:20.050908

"""

# revision identifiers, used by Alembic.
revision = '38c273108088'
down_revision = '23cbe32ac74e'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('tg_group', 'group_name',
            existing_type=sa.Unicode(255), nullable=False)

def downgrade():
    pass # no downgrade because we are fixing an upgrade
