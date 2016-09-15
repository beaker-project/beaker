# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""delete log_recipe_task and log_recipe for deleted jobs

Revision ID: 1be4eef2ee1f
Revises: 3028e6a6e3d7
Create Date: 2016-09-19 17:34:26.032947

"""

# revision identifiers, used by Alembic.
revision = '1be4eef2ee1f'
down_revision = '1626ad29c170'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        DELETE log_recipe_task
        FROM log_recipe_task
        INNER JOIN recipe_task ON log_recipe_task.recipe_task_id = recipe_task.id
        INNER JOIN recipe on recipe_task.recipe_id = recipe.id
        INNER JOIN recipe_set on recipe.recipe_set_id = recipe_set.id
        INNER JOIN job on recipe_set.job_id = job.id
        WHERE job.deleted IS NOT NULL;

    """)

    op.execute("""
        DELETE log_recipe
        FROM log_recipe 
        INNER JOIN recipe on log_recipe.recipe_id = recipe.id
        INNER JOIN recipe_set on recipe.recipe_set_id = recipe_set.id
        INNER JOIN job on recipe_set.job_id = job.id
        WHERE job.deleted IS NOT NULL;
    """)


def downgrade():
    pass
