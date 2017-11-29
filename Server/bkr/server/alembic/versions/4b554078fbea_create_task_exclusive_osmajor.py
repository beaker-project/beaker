# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Create task_exclusive_osmajor table

Revision ID: 4b554078fbea
Revises: 2a56e56fbe26
Create Date: 2017-11-28 16:16:53.013288
"""

# revision identifiers, used by Alembic.
revision = '4b554078fbea'
down_revision = '2a56e56fbe26'

from alembic import op
from sqlalchemy import Column, Integer, ForeignKey

def upgrade():
    op.create_table('task_exclusive_osmajor',
        Column('task_id', Integer,
               ForeignKey('task.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, nullable=False, index=True),
        Column('osmajor_id', Integer,
               ForeignKey('osmajor.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, nullable=False, index=True),
        mysql_engine='InnoDB',
    )

def downgrade():
    # Convert any existing "exclusive" rows to their "exclude" equivalent
    op.execute("""
        INSERT INTO task_exclude_osmajor (task_id, osmajor_id)
        SELECT task.id, osmajor.id
        FROM task, osmajor
        WHERE
            EXISTS (SELECT 1 FROM task_exclusive_osmajor WHERE task_id = task.id)
            AND NOT EXISTS (SELECT 1 FROM task_exclusive_osmajor WHERE task_id = task.id AND osmajor_id = osmajor.id)
        """)
    op.drop_table('task_exclusive_osmajor')
