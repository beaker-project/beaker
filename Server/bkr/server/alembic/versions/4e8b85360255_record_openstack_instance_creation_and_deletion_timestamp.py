# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""record OpenStack instance creation and deletion timestamps

Revision ID: 4e8b85360255
Revises: 32f962a53c31
Create Date: 2016-10-26 13:08:43.952818

"""

# revision identifiers, used by Alembic.
revision = '4e8b85360255'
down_revision = '32f962a53c31'

from alembic import op
from sqlalchemy import Column, DateTime, func

def upgrade():
    # The existing rows may have NULL in these columns.
    op.add_column('virt_resource', Column('instance_created', DateTime, nullable=True))
    op.add_column('virt_resource', Column('instance_deleted', DateTime, nullable=True))

def downgrade():
    op.drop_column('virt_resource', 'instance_created')
    op.drop_column('virt_resource', 'instance_deleted')
