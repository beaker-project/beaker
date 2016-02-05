# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Extract recipe reviewed state

Revision ID: 0ae85f81f838
Revises: 1c79b9a2722d
Create Date: 2015-11-09 15:35:04.249045

"""

# revision identifiers, used by Alembic.
revision = '0ae85f81f838'
down_revision = '1c79b9a2722d'

from alembic import op
from sqlalchemy import Column, Integer, Boolean, ForeignKey

def upgrade():
    op.create_table('recipe_reviewed_state',
        Column('recipe_id', Integer, ForeignKey('recipe.id',
                name='recipe_reviewed_state_recipe_id_fk',
                onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
        Column('user_id', Integer, ForeignKey('tg_user.user_id',
                name='recipe_reviewed_state_user_id_fk',
                onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
        Column('reviewed', Boolean, nullable=False),
        mysql_engine='InnoDB',
    )
    # We consider a recipe to reviewed by its owner if it's part of a recipe 
    # set has a response (ack/nak) set. Unfortunately this doesn't work 
    # perfectly because:
    #   * many people review their results but don't use the ack/nak system
    #   * Beaker automatically sets "ack" for recipe sets which Passed
    #   * the response could have been set by someone other than the owner
    # but it's the best we can do for existing recipes.
    op.execute("""
        INSERT INTO recipe_reviewed_state (recipe_id, user_id, reviewed)
        SELECT recipe.id, job.owner_id, TRUE
        FROM recipe
        INNER JOIN recipe_set ON recipe.recipe_set_id = recipe_set.id
        INNER JOIN job ON recipe_set.job_id = job.id
        INNER JOIN recipe_set_nacked ON recipe_set_nacked.recipe_set_id = recipe_set.id
        """)

def downgrade():
    op.drop_table('recipe_reviewed_state')
