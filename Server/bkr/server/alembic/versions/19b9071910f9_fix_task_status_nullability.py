# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix task status NULLability

Revision ID: 19b9071910f9
Revises: 431e4e2ccbba
Create Date: 2014-10-07 14:56:14.828618

"""

# revision identifiers, used by Alembic.
revision = '19b9071910f9'
down_revision = '431e4e2ccbba'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('job', 'status',
            existing_type=sa.Enum(u'New', u'Processed', u'Queued',
                u'Scheduled', u'Waiting', u'Running', u'Completed',
                u'Cancelled', u'Aborted', u'Reserved'),
            nullable=False)
    op.alter_column('recipe_set', 'status',
            existing_type=sa.Enum(u'New', u'Processed', u'Queued',
                u'Scheduled', u'Waiting', u'Running', u'Completed',
                u'Cancelled', u'Aborted', u'Reserved'),
            nullable=False)
    op.alter_column('recipe', 'status',
            existing_type=sa.Enum(u'New', u'Processed', u'Queued',
                u'Scheduled', u'Waiting', u'Running', u'Completed',
                u'Cancelled', u'Aborted', u'Reserved'),
            nullable=False)
    op.alter_column('recipe_task', 'status',
            existing_type=sa.Enum(u'New', u'Processed', u'Queued',
                u'Scheduled', u'Waiting', u'Running', u'Completed',
                u'Cancelled', u'Aborted', u'Reserved'),
            nullable=False)

def downgrade():
    pass # no downgrade because we are fixing a mistake in an upgrade
