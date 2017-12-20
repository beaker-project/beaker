# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make distro_tree_activity.distro_tree_id non-NULLable

Revision ID: 286ed23a5c1b
Revises: 47ea09370b46
Create Date: 2017-12-20 15:45:45.359156
"""

# revision identifiers, used by Alembic.
revision = '286ed23a5c1b'
down_revision = '47ea09370b46'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('distro_tree_activity', 'distro_tree_id',
                    existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('distro_tree_activity', 'distro_tree_id',
                    existing_type=Integer, nullable=True)
