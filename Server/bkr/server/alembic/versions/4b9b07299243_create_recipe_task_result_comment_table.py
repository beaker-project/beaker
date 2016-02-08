# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""create recipe task result comment table

Revision ID: 4b9b07299243
Revises: 2cc8e59635f5
Create Date: 2016-02-05 16:27:38.887778

"""

# revision identifiers, used by Alembic.
revision = '4b9b07299243'
down_revision = '2cc8e59635f5'

from alembic import op
from sqlalchemy import Column, ForeignKey, Integer, Unicode, DateTime

def upgrade():
    op.create_table('recipe_task_result_comment',
        Column('id', Integer, autoincrement=True, primary_key=True),
        Column('recipe_task_result_id', Integer, ForeignKey('recipe_task_result.id',
                name='recipe_task_result_comment_recipe_task_result_id_fk',
                onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
        Column('user_id', Integer, ForeignKey('tg_user.user_id',
                name='recipe_task_result_comment_user_id_fk',
                onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
        Column('comment', Unicode(4000), nullable=False),
        Column('created', DateTime, nullable=False),
        mysql_engine='InnoDB',
    )

def downgrade():
    op.drop_table('recipe_task_result_comment')
