# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""correct recipe task comment table definition

Revision ID: 2cc8e59635f5
Revises: 51637c12cbd9
Create Date: 2016-02-05 13:45:23.239586

"""

# revision identifiers, used by Alembic.
revision = '2cc8e59635f5'
down_revision = '51637c12cbd9'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import drop_fk

def upgrade():
    drop_fk('recipe_task_comment', ['recipe_task_id'])
    op.alter_column('recipe_task_comment', 'recipe_task_id', nullable=False,
            existing_type=sa.Integer)
    op.create_foreign_key('recipe_task_comment_recipe_task_id_fk',
            'recipe_task_comment', 'recipe_task',
            ['recipe_task_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    drop_fk('recipe_task_comment', ['user_id'])
    op.drop_index('ix_recipe_task_comment_user_id', table_name='recipe_task_comment')
    op.alter_column('recipe_task_comment', 'user_id', nullable=False,
            existing_type=sa.Integer)
    op.create_foreign_key('recipe_task_comment_user_id_fk', 'recipe_task_comment',
            'tg_user', ['user_id'], ['user_id'], onupdate='CASCADE', ondelete='CASCADE')
    op.alter_column('recipe_task_comment', 'comment', nullable=False,
            type_=sa.Unicode(4000))
    op.alter_column('recipe_task_comment', 'created', nullable=False,
            existing_type=sa.DateTime)

def downgrade():
    drop_fk('recipe_task_comment', ['recipe_task_id'])
    op.alter_column('recipe_task_comment', 'recipe_task_id', nullable=True,
            existing_type=sa.Integer)
    op.create_foreign_key(None, 'recipe_task_comment', 'recipe_task',
            ['recipe_task_id'], ['id'])
    drop_fk('recipe_task_comment', ['user_id'])
    op.drop_index('recipe_task_comment_user_id_fk', table_name='recipe_task_comment')
    op.create_index('ix_recipe_task_comment_user_id', 'recipe_task_comment',
            ['user_id'])
    op.alter_column('recipe_task_comment', 'user_id', nullable=True,
            existing_type=sa.Integer)
    op.create_foreign_key(None, 'recipe_task_comment','tg_user', ['user_id'],
            ['user_id'])
    op.alter_column('recipe_task_comment', 'comment', nullable=True,
            type_=sa.UnicodeText())
    op.alter_column('recipe_task_comment', 'created', nullable=True,
            existing_type=sa.DateTime)
