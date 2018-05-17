# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add distro metadata columns to installation

Revision ID: 3ba776df4c76
Revises: 2441049ac32c
Create Date: 2017-11-13 17:48:17.686405

"""

# revision identifiers, used by Alembic.
revision = '3ba776df4c76'
down_revision = '2441049ac32c'

from alembic import op
import sqlalchemy as sa


def has_migration_run_before():
    # If we find at least one of the new column names in the existing table, we
    # assume that the migration has already been run before. If the database
    # was left with some new columns left in the installation table, all bets
    # are off.
    columns = sa.inspect(op.get_bind()).get_columns('installation')
    return 'tree_url' in [c['name'] for c in columns]

def upgrade():
    if not has_migration_run_before():
        op.execute("""
            ALTER TABLE installation
            ADD COLUMN tree_url TEXT DEFAULT NULL,
            ADD COLUMN initrd_path TEXT DEFAULT NULL,
            ADD COLUMN kernel_path TEXT DEFAULT NULL,
            ADD COLUMN distro_name TEXT DEFAULT NULL,
            ADD COLUMN osmajor TEXT DEFAULT NULL,
            ADD COLUMN osminor TEXT DEFAULT NULL,
            ADD COLUMN variant TEXT DEFAULT NULL,
            ADD COLUMN arch_id INT DEFAULT NULL,
            ADD CONSTRAINT installation_arch_id_fk FOREIGN KEY (arch_id)
                REFERENCES arch (id)
        """)

    # Create installation entries for recipes which have just been scheduled,
    # but don't re-create them in case this migration runs again after a former
    # downgrade.
    op.execute("""
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


def downgrade():
    """Don't touch the new installation columns, but deal with the new data
    during the upgrade. See Bug 1550361"""
