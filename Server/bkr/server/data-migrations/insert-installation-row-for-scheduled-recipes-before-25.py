# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Alembic revision 3ba776df4c76 was supposed to INSERT rows into the
'installation' table for recipes that were not yet provisioned at the time when
Beaker was upgraded to 25. It originally had a bug where it was ignoring
recipes in the 'Scheduled' state. That migration is fixed now, but we also
repeat the same INSERT statement here, for Beaker sites which were already
upgraded using the buggy version of the Alembic migration.
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
            LEFT OUTER JOIN installation ON installation.recipe_id = recipe.id
            WHERE recipe.status = 'Scheduled'
            AND installation.recipe_id is NULL;
            """)

    logger.info('Created installation row for %d recipes', result.rowcount)
    return True
