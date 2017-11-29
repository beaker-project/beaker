# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Create task_exclusive_arch table

Revision ID: 17e8de5c7d4b
Revises: 4b554078fbea
Create Date: 2017-11-29 16:00:02.075386
"""

# revision identifiers, used by Alembic.
revision = '17e8de5c7d4b'
down_revision = '4b554078fbea'

from alembic import op
from sqlalchemy import Column, Integer, ForeignKey

def upgrade():
    op.create_table('task_exclusive_arch',
        Column('task_id', Integer,
               ForeignKey('task.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, nullable=False, index=True),
        Column('arch_id', Integer,
               ForeignKey('arch.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, nullable=False, index=True),
        mysql_engine='InnoDB',
    )

def downgrade():
    # Convert any existing "exclusive" rows to their "exclude" equivalent
    op.execute("""
        INSERT INTO task_exclude_arch (task_id, arch_id)
        SELECT task.id, arch.id
        FROM task, arch
        WHERE
            EXISTS (SELECT 1 FROM task_exclusive_arch WHERE task_id = task.id)
            AND NOT EXISTS (SELECT 1 FROM task_exclusive_arch WHERE task_id = task.id AND arch_id = arch.id)
        """)
    op.drop_table('task_exclusive_arch')
