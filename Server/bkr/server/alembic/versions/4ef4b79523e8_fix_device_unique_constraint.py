# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix device unique constraint

Revision ID: 4ef4b79523e8
Revises: 01a7a1210068
Create Date: 2014-10-10 14:20:39.241038

"""

# revision identifiers, used by Alembic.
revision = '4ef4b79523e8'
down_revision = '01a7a1210068'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.drop_constraint('device_uix_1', 'device', type_='unique')
    op.create_unique_constraint('device_uix_1', 'device', ['vendor_id',
            'device_id', 'subsys_device_id', 'subsys_vendor_id', 'bus',
            'driver', 'description', 'device_class_id'])

def downgrade():
    op.drop_constraint('device_uix_1', 'device', type_='unique')
    op.create_unique_constraint('device_uix_1', 'device', ['vendor_id',
            'device_id', 'subsys_device_id', 'subsys_vendor_id', 'bus',
            'driver', 'description'])
