
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Older versions of beaker-log-delete did not always correctly delete all logs 
for a job before marking it as "deleted" (we now call this "purged").

If there is any job which has been purged, but still has associated log_* rows, 
we clear the purged timestamp so that beaker-log-delete will try purging again.
"""

import logging
from sqlalchemy import inspect

logger = logging.getLogger(__name__)

def migrate_one_batch(engine):
    logger.info('Clearing purged timestamp on jobs with logs')
    with engine.begin() as connection:
        result = connection.execute("""
            UPDATE job
            SET purged = NULL
            WHERE purged IS NOT NULL
            AND EXISTS (
                SELECT 1 FROM log_recipe
                INNER JOIN recipe ON log_recipe.recipe_id = recipe.id
                INNER JOIN recipe_set ON recipe.recipe_set_id = recipe_set.id
                WHERE recipe_set.job_id = job.id
            ) OR EXISTS (
                SELECT 1 FROM log_recipe_task
                INNER JOIN recipe_task ON log_recipe_task.recipe_task_id = recipe_task.id
                INNER JOIN recipe ON recipe_task.recipe_id = recipe.id
                INNER JOIN recipe_set ON recipe.recipe_set_id = recipe_set.id
                WHERE recipe_set.job_id = job.id
            )
            """)
    logger.info('Cleared purged timestamp on %d jobs with logs', result.rowcount)
    return True # migration complete
