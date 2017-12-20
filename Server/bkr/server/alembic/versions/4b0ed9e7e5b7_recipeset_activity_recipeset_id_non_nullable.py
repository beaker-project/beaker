# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make recipeset_activity.recipeset_id non-NULLable

Revision ID: 4b0ed9e7e5b7
Revises: 4957d4804ba
Create Date: 2017-12-20 16:12:08.406121
"""

# revision identifiers, used by Alembic.
revision = '4b0ed9e7e5b7'
down_revision = '4957d4804ba'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('recipeset_activity', 'recipeset_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('recipeset_activity', 'recipeset_id', existing_type=Integer, nullable=True)
