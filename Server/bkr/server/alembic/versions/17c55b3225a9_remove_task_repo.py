# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Remove unused task.repo column

Revision ID: 17c55b3225a9
Revises: 357e67243615
Create Date: 2017-12-13 16:48:24.751566
"""

# revision identifiers, used by Alembic.
revision = '17c55b3225a9'
down_revision = '357e67243615'

from alembic import op
from sqlalchemy import Column, Unicode

def upgrade():
    op.drop_column('task', 'repo')

def downgrade():
    op.add_column('task', Column('repo', Unicode(256)))
