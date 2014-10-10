# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Remove database defaults

Revision ID: 53942581687f
Revises: 348a7a0b9bba
Create Date: 2014-10-10 15:51:03.548807

"""

# revision identifiers, used by Alembic.
revision = '53942581687f'
down_revision = '348a7a0b9bba'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('recipe', 'virt_status',
            existing_type=sa.Enum('Possible', 'Precluded', 'Succeeded', 'Skipped', 'Failed'),
            nullable=False)
    op.alter_column('recipe_set', 'priority',
            existing_type=sa.Enum('Low', 'Medium', 'Normal', 'High', 'Urgent'),
            nullable=False)

def downgrade():
    pass # no downgrade because we are fixing a mistake in an upgrade
