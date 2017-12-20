# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make distro_activity.distro_id non-NULLable

Revision ID: 47ea09370b46
Revises: 404960aab655
Create Date: 2017-12-20 15:18:46.168613
"""

# revision identifiers, used by Alembic.
revision = '47ea09370b46'
down_revision = '404960aab655'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('distro_activity', 'distro_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('distro_activity', 'distro_id', existing_type=Integer, nullable=True)
