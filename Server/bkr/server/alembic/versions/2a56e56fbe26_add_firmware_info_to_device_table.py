# This program is free software; you can redistribute it and/or modify
## i under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""add firmware columns to device table

Revision ID: 2a56e56fbe26
Revises: f18df089261
Create Date: 2017-07-25 18:48:06.192722

"""

# revision identifiers, used by Alembic.
revision = '2a56e56fbe26'
down_revision = '444bcfb89b2a'

from alembic import op
from sqlalchemy import Column, Unicode

def upgrade():
    op.add_column('device', Column('fw_version', Unicode(32)))
    op.drop_constraint('device_uix_1', 'device', type_='unique')
    op.create_unique_constraint('device_uix_1', 'device', ['vendor_id',
            'device_id', 'subsys_device_id', 'subsys_vendor_id', 'bus',
            'driver', 'description', 'device_class_id', 'fw_version'])


def downgrade():
    op.drop_constraint('device_uix_1', 'device', type_='unique')
    op.drop_column('device', 'fw_version')
    op.create_unique_constraint('device_uix_1', 'device', ['vendor_id',
            'device_id', 'subsys_device_id', 'subsys_vendor_id', 'bus',
            'driver', 'description', 'device_class_id'])
