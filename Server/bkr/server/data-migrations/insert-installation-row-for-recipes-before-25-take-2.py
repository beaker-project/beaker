# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
This is an additional online migration re Alembic revision 3ba776df4c76 and the
already existing insert-installation-row-for-scheduled-recipes-before-25.py
migration script. With the deployment of the online migration, we found
additional regressions in scheduled jobs before the Beaker 25 migration. These
cases have been documented on Bug 1568224 comments 12 and 13. The cases boil
down to two distinct situations:

    a) Two recipes in a recipeset where scheduled, one failed to
       provision due to a bug in the code, while the other provisioned fine.
       The status of the recipe is a transient state: 'Waiting'
    b) The recipes have either been cancelled or aborted due to not
       matching systems or by a cancelled request by the user.
"""

import logging


logger = logging.getLogger(__name__)


def migrate_one_batch(engine):
    with engine.begin() as connection:
        result = connection.execute("""
            INSERT INTO installation
            (created, distro_tree_id, recipe_id, arch_id, distro_name, osmajor, osminor, variant)
            SELECT UTC_TIMESTAMP(),
                recipe.distro_tree_id,
                recipe.id,
                distro_tree.arch_id,
                distro.name,
                osmajor.osmajor,
                osversion.osminor,
                distro_tree.variant
            FROM recipe
            INNER JOIN distro_tree ON distro_tree.id = recipe.distro_tree_id
            INNER JOIN distro ON distro.id = distro_tree.distro_id
            INNER JOIN osversion ON osversion.id = distro.osversion_id
            INNER JOIN osmajor ON osmajor.id = osversion.osmajor_id
            INNER JOIN recipe_set ON recipe_set.id = recipe.recipe_set_id
            INNER JOIN job ON job.id = recipe_set.job_id
            LEFT OUTER JOIN installation ON installation.recipe_id = recipe.id
            WHERE job.status not in ('Completed', 'Cancelled', 'Aborted')
            AND installation.recipe_id is NULL;
            """)

    logger.info('Created installation row for %d recipes', result.rowcount)
    return True
