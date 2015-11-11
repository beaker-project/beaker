# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Preserve arbitrary XML in Job column

Revision ID: b830bfac525
Revises: 1b4aec9ce90d
Create Date: 2015-11-10 23:41:01.990834

"""

revision = 'b830bfac525'
down_revision = '1b4aec9ce90d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('job', sa.Column('extra_xml', sa.UnicodeText(), nullable=True))


def downgrade():
    op.drop_column('job', 'extra_xml')
