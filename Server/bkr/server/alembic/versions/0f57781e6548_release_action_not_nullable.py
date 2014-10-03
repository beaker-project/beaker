# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make system.release_action not NULLable

Revision ID: 0f57781e6548
Revises: 5612881c761b
Create Date: 2014-10-01 17:47:12.417236

"""

# revision identifiers, used by Alembic.
revision = '0f57781e6548'
down_revision = '5612881c761b'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("UPDATE system SET release_action = 'PowerOff' WHERE release_action IS NULL")
    op.alter_column('system', 'release_action',
            existing_type=sa.Enum(u'PowerOff', u'LeaveOn', u'ReProvision'),
            nullable=False)

def downgrade():
    op.alter_column('system', 'release_action',
            existing_type=sa.Enum(u'PowerOff', u'LeaveOn', u'ReProvision'),
            nullable=True)
