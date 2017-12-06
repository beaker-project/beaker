# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add system.scheduler_status column

Revision ID: 1042b15c2c7
Revises: 17e8de5c7d4b
Create Date: 2017-12-04 17:07:02.179659
"""

# revision identifiers, used by Alembic.
revision = '1042b15c2c7'
down_revision = '17e8de5c7d4b'

from alembic import op
from sqlalchemy import Column, Enum

def upgrade():
    # Create the column NULLable initially
    op.add_column('system', Column('scheduler_status', Enum(u'Idle', u'Pending', u'Reserved')))
    # Populate it with values:
    # Removed systems -> Idle
    # Reserved systems -> Reserved
    # Everything else -> Pending
    op.execute("""
        UPDATE system
        SET scheduler_status = 'Idle'
        WHERE status = 'Removed'
        """)
    op.execute("""
        UPDATE system
        SET scheduler_status = 'Reserved'
        WHERE user_id IS NOT NULL
        AND status != 'Removed'
        """)
    op.execute("""
        UPDATE system
        SET scheduler_status = 'Pending'
        WHERE user_id IS NULL
        AND status != 'Removed'
        """)
    # Make it non-NULLable
    op.alter_column('system', 'scheduler_status',
            type_=Enum(u'Idle', u'Pending', u'Reserved'),
            nullable=False)

def downgrade():
    op.drop_column('system', 'scheduler_status')
