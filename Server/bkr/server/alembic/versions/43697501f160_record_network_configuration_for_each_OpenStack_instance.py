# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""record network configuration for each OpenStack instance

Revision ID: 43697501f160
Revises: 3028e6a6e3d7
Create Date: 2016-08-24 11:40:08.375121

"""

# revision identifiers, used by Alembic.
revision = '43697501f160'
down_revision = '3028e6a6e3d7'

from bkr.server.model import UUID
from alembic import op
from sqlalchemy import Column, String

def upgrade():
    # We cannot use nullable=False as old rows may have NULL in these columns.
    op.add_column('virt_resource', Column('network_id', UUID(), nullable=True))
    op.add_column('virt_resource', Column('subnet_id', UUID(), nullable=True))
    op.add_column('virt_resource', Column('router_id', UUID(), nullable=True))

def downgrade():
    op.drop_column('virt_resource', 'network_id')
    op.drop_column('virt_resource', 'subnet_id')
    op.drop_column('virt_resource', 'router_id')
