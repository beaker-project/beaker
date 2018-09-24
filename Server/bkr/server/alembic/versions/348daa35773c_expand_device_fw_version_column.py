# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Expand device.fw_version column

Revision ID: 348daa35773c
Revises: 292b2e042673
Create Date: 2018-09-24 13:51:26.257198
"""

# revision identifiers, used by Alembic.
revision = '348daa35773c'
down_revision = '292b2e042673'

from alembic import op
from sqlalchemy import Unicode

def upgrade():
    op.alter_column('device', 'fw_version', type_=Unicode(241), nullable=True)

def downgrade():
    op.alter_column('device', 'fw_version', type_=Unicode(32), nullable=True)
