# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Extract recipe set comments from recipe_set_nacked

Revision ID: 1c79b9a2722d
Revises: 38d7abc90c54
Create Date: 2015-11-05 14:38:37.925593

"""

# revision identifiers, used by Alembic.
revision = '1c79b9a2722d'
down_revision = '38d7abc90c54'

from alembic import op
from sqlalchemy import Column, ForeignKey, Integer, Unicode, DateTime

def upgrade():
    op.create_table('recipe_set_comment',
        Column('id', Integer, autoincrement=True, primary_key=True),
        Column('recipe_set_id', Integer, ForeignKey('recipe_set.id',
                name='recipe_set_comment_recipe_set_id_fk',
                onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
        Column('user_id', Integer, ForeignKey('tg_user.user_id',
                name='recipe_set_comment_user_id_fk',
                onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
        Column('comment', Unicode(4000), nullable=False),
        Column('created', DateTime, nullable=False),
        mysql_engine='InnoDB',
    )
    op.execute("""
        INSERT INTO recipe_set_comment (recipe_set_id, user_id, comment, created)
        SELECT recipe_set_id, job.owner_id, comment, created
        FROM recipe_set_nacked
        INNER JOIN recipe_set ON recipe_set_nacked.recipe_set_id = recipe_set.id
        INNER JOIN job ON recipe_set.job_id = job.id
        WHERE comment IS NOT NULL
        """)
    # Not dropping recipe_set_nacked.comment so that it will still exist, 
    # holding old data, in case of downgrade.

def downgrade():
    op.drop_table('recipe_set_comment')
