# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add notify_system_loan preference

Revision ID: 39885f53180f
Revises: 2a6c3722f063
Create Date: 2017-12-21 16:30:24.956613
"""

# revision identifiers, used by Alembic.
revision = '39885f53180f'
down_revision = '2a6c3722f063'

from alembic import op
from sqlalchemy import Column, Boolean

def upgrade():
    op.add_column('tg_user', Column('notify_system_loan', Boolean, nullable=False))

def downgrade():
    op.drop_column('tg_user', 'notify_system_loan')
