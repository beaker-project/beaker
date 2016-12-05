# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""associate a floating ip to each OpenStack instance

Revision ID: f18df089261
Revises: 4f7a4316565f
Create Date: 2016-12-05 05:59:28.858413

"""

# revision identifiers, used by Alembic.
revision = 'f18df089261'
down_revision = '4f7a4316565f'

from alembic import op
from sqlalchemy import Column
from bkr.server.model import IPAddress

def upgrade():
    op.add_column('virt_resource', Column('floating_ip', IPAddress(), nullable=True))

def downgrade():
    op.drop_column('virt_resource', 'floating_ip')
