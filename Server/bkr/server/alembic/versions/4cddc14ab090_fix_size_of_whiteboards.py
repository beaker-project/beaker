# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
fix size of whiteboards

Users like to leverage whiteboard for sorting jobs/recipes
into different groups. With high demand for more testing
they can not fix enough tags within 2000 characters.

Revision ID: 4cddc14ab090
Revises: 348daa35773c
Create Date: 2019-11-28 06:04:15.232813
"""

from alembic import op
from sqlalchemy import Unicode

# revision identifiers, used by Alembic.
revision = '4cddc14ab090'
down_revision = '348daa35773c'


def upgrade():
    op.alter_column('job', 'whiteboard', type_=Unicode(4096), nullable=True)
    op.alter_column('recipe', 'whiteboard', type_=Unicode(4096), nullable=True)


def downgrade():
    op.alter_column('job', 'whiteboard', type_=Unicode(2000), nullable=True)
    op.alter_column('recipe', 'whiteboard', type_=Unicode(2000), nullable=True)
