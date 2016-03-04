# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""support group description

Revision ID: 38d7abc90c54
Revises: 59b98f6e0120
Create Date: 2016-03-04 09:22:27.538702

"""

# revision identifiers, used by Alembic.
revision = '38d7abc90c54'
down_revision = '59b98f6e0120'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('tg_group', sa.Column('description', sa.Unicode(length=4000)))

def downgrade():
    op.drop_column('tg_group', 'description')
