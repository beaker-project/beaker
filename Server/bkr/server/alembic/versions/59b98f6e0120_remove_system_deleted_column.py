# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Remove unused system.deleted column

Revision ID: 59b98f6e0120
Revises: b1a6732734e
Create Date: 2016-01-25 15:28:26.711117
"""

# revision identifiers, used by Alembic.
revision = '59b98f6e0120'
down_revision = 'b1a6732734e'

from alembic import op
from sqlalchemy import Column, Boolean

def upgrade():
    op.drop_column('system', 'deleted')

def downgrade():
    op.add_column('system', Column('deleted', Boolean, nullable=False, default=False))
    op.alter_column('system', 'deleted', existing_type=Boolean, nullable=True)

