# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make osversion.osmajor_id non-NULLable

Revision ID: 5ab66e956c6b
Revises: 286ed23a5c1b
Create Date: 2017-12-20 15:54:38.825703
"""

# revision identifiers, used by Alembic.
revision = '5ab66e956c6b'
down_revision = '286ed23a5c1b'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('osversion', 'osmajor_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('osversion', 'osmajor_id', existing_type=Integer, nullable=True)
