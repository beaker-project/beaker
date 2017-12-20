# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Remove unused recipe_task_bugzilla table

Revision ID: 46b19cc8fd7e
Revises: 2384d43354a4
Create Date: 2017-12-20 16:34:10.380663
"""

# revision identifiers, used by Alembic.
revision = '46b19cc8fd7e'
down_revision = '2384d43354a4'

from alembic import op
from sqlalchemy import Column, Integer, ForeignKey

def upgrade():
    op.drop_table('recipe_task_bugzilla')

def downgrade():
    op.create_table('recipe_task_bugzilla',
            Column('id', Integer, primary_key=True),
            Column('recipe_task_id', Integer, ForeignKey('recipe_task.id')),
            Column('bugzilla_id', Integer),
            mysql_engine=u'InnoDB')
