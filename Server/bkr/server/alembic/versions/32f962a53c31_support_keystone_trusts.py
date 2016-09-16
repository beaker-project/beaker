# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""store a Keystone trust id instead of the user's raw login credentials

Revision ID: 32f962a53c31
Revises: 3a141cda8089
Create Date: 2016-09-12 01:35:51.588516

"""

# revision identifiers, used by Alembic.
revision = '32f962a53c31'
down_revision = '3a141cda8089'

from alembic import op
from sqlalchemy import Column, String, Unicode

def upgrade():
    op.add_column('tg_user', Column('openstack_trust_id', Unicode(length=4000), nullable=True))
    op.drop_column('tg_user', 'openstack_tenant_name')
    op.drop_column('tg_user', 'openstack_password')
    op.drop_column('tg_user', 'openstack_username')

def downgrade():
    op.drop_column('tg_user', 'openstack_trust_id')
    op.add_column('tg_user', Column('openstack_username', Unicode(length=255), nullable=True))
    op.add_column('tg_user', Column('openstack_password', Unicode(length=2048), nullable=True))
    op.add_column('tg_user', Column('openstack_tenant_name', Unicode(length=2048), nullable=True))
