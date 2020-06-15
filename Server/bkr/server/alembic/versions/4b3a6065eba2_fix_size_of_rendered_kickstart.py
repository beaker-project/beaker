# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Fix size of rendered Kickstart

Revision ID: 4b3a6065eba2
Revises: 4cddc14ab090
Create Date: 2020-06-08 04:31:21.024268
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4b3a6065eba2'
down_revision = '4cddc14ab090'


def upgrade():
    op.alter_column('rendered_kickstart', 'kickstart',
                    existing_type=sa.UnicodeText(),
                    type_=sa.UnicodeText(length=262143),
                    existing_nullable=True)


def downgrade():
    op.alter_column('rendered_kickstart', 'kickstart',
                    existing_type=sa.UnicodeText(length=262143),
                    type_=sa.UnicodeText(),
                    existing_nullable=True)
