# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add columns for user email notifications

Revision ID: 468779d8e8
Revises: 3028e6a6e3d7
Create Date: 2016-09-25 00:54:16.965342

"""

# revision identifiers, used by Alembic.
revision = '468779d8e8'
down_revision = '43697501f160'

from alembic import op
from sqlalchemy import Column, Boolean


def upgrade():
    op.add_column('tg_user', Column('notify_job_completion', Boolean, nullable=False, default=True))
    op.add_column('tg_user', Column('notify_broken_system', Boolean, nullable=False, default=True))
    op.add_column('tg_user', Column('notify_group_membership', Boolean, nullable=False, default=True))
    op.add_column('tg_user', Column('notify_reservesys', Boolean, nullable=False, default=True))
    op.execute('UPDATE tg_user SET notify_job_completion = TRUE, '
               'notify_broken_system = TRUE, notify_group_membership = TRUE, '
               'notify_reservesys = TRUE')


def downgrade():
    op.drop_column('tg_user', 'notify_job_completion')
    op.drop_column('tg_user', 'notify_broken_system')
    op.drop_column('tg_user', 'notify_group_membership')
    op.drop_column('tg_user', 'notify_reservesys')
