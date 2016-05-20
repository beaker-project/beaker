# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""delete log_recipe_task_result rows for deleted jobs

Revision ID: 4a7454ee677a
Revises: 29c945bb5b0f
Create Date: 2016-05-20 15:38:40.495128

"""

# revision identifiers, used by Alembic.
revision = '4a7454ee677a'
down_revision = '29c945bb5b0f'

from alembic import op

def upgrade():
    op.execute("""
        DELETE log_recipe_task_result
        FROM log_recipe_task_result
        INNER JOIN recipe_task_result ON log_recipe_task_result.recipe_task_result_id = recipe_task_result.id
        INNER JOIN recipe_task ON recipe_task_result.recipe_task_id = recipe_task.id
        INNER JOIN recipe on recipe_task.recipe_id = recipe.id
        INNER JOIN recipe_set on recipe.recipe_set_id = recipe_set.id
        INNER JOIN job on recipe_set.job_id = job.id
        WHERE job.deleted IS NOT NULL
        """)

def downgrade():
    pass # no downgrade because we are cleaning up old data.
