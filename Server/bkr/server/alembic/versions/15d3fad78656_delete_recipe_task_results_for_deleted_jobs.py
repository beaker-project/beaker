# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""delete recipe_task_result rows for deleted jobs

Revision ID: 15d3fad78656
Revises: 4a7454ee677a
Create Date: 2016-04-19 16:30:23.095129

"""

# revision identifiers, used by Alembic.
revision = "15d3fad78656"
down_revision = "4a7454ee677a"

from alembic import op


def upgrade():
    op.execute(
        """
        DELETE recipe_task_result
        FROM recipe_task_result
        INNER JOIN recipe_task ON recipe_task_result.recipe_task_id = recipe_task.id
        INNER JOIN recipe on recipe_task.recipe_id = recipe.id
        INNER JOIN recipe_set on recipe.recipe_set_id = recipe_set.id
        INNER JOIN job on recipe_set.job_id = job.id
        WHERE job.deleted IS NOT NULL
        """
    )


def downgrade():
    pass  # no downgrade because we are cleaning up old data.
