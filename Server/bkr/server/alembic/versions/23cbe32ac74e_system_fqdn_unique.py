# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make system.fqdn unique

Revision ID: 23cbe32ac74e
Revises: 0f57781e6548
Create Date: 2014-10-02 16:12:05.951034

"""

# revision identifiers, used by Alembic.
revision = '23cbe32ac74e'
down_revision = '0f57781e6548'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_unique_constraint('fqdn', 'system', ['fqdn'])

def downgrade():
    op.drop_constraint('fqdn', 'system', type_='unique')
