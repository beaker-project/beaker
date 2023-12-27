# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
add image_path to Installation table

Revision ID: 140c5eea2836
Revises: 4b3a6065eba2
Create Date: 2022-09-01 18:06:05.437563
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '140c5eea2836'
down_revision = '4b3a6065eba2'


def upgrade():
    op.add_column('installation', sa.Column('image_path', sa.UnicodeText(), nullable=True))


def downgrade():
    op.drop_column('installation', 'image_path')
