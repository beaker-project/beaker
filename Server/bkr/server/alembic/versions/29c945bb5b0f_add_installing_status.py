# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add Installing status

Revision ID: 29c945bb5b0f
Revises: 4b9b07299243
Create Date: 2016-02-18 14:44:38.544741
"""

# revision identifiers, used by Alembic.
revision = '29c945bb5b0f'
down_revision = '4b9b07299243'

from alembic import op
from bkr.server.alembic.migration_utils import add_enum_value, drop_enum_value

def upgrade():
    add_enum_value('job', 'status', u'Installing', nullable=False)
    add_enum_value('recipe_set', 'status', u'Installing', nullable=False)
    add_enum_value('recipe', 'status', u'Installing', nullable=False)
    add_enum_value('recipe_task', 'status', u'Installing', nullable=False)

def downgrade():
    op.execute("""
        UPDATE job
        SET status = 'Running'
        WHERE status = 'Installing'
        """)
    op.execute("""
        UPDATE recipe_set
        SET status = 'Running'
        WHERE status = 'Installing'
        """)
    op.execute("""
        UPDATE recipe
        SET status = 'Running'
        WHERE status = 'Installing'
        """)
    # It should be impossible for recipe_task status to be Installing but let's 
    # do it for completeness...
    op.execute("""
        UPDATE recipe_task
        SET status = 'Running'
        WHERE status = 'Installing'
        """)
    drop_enum_value('job', 'status', u'Installing', nullable=False)
    drop_enum_value('recipe_set', 'status', u'Installing', nullable=False)
    drop_enum_value('recipe', 'status', u'Installing', nullable=False)
    drop_enum_value('recipe_task', 'status', u'Installing', nullable=False)
