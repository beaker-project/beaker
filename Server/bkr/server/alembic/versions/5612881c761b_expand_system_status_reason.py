# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Expand system.status_reason

Revision ID: 5612881c761b
Revises: 42c18b6580e0
Create Date: 2014-10-01 17:43:47.862690

"""

# revision identifiers, used by Alembic.
revision = '5612881c761b'
down_revision = '42c18b6580e0'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.alter_column('system', 'status_reason', type_=sa.Unicode(4000), nullable=True)

def downgrade():
    op.alter_column('system', 'status_reason', type_=sa.Unicode(255), nullable=True)
