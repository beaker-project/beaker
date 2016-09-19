# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Create installation table

Revision ID: 51637c12cbd9
Revises: 3c5510511fd9
Create Date: 2016-02-15 14:16:53.312688
"""

# revision identifiers, used by Alembic.
revision = '51637c12cbd9'
down_revision = '3c5510511fd9'

from alembic import op
from sqlalchemy import Column, Integer, Unicode, UnicodeText, DateTime, ForeignKey
from bkr.server.alembic.migration_utils import drop_fk

def upgrade():
    op.create_table('installation',
        Column('id', Integer, primary_key=True),
        Column('distro_tree_id', Integer, ForeignKey('distro_tree.id',
                name='installation_distro_tree_id_fk'), nullable=False),
        Column('kernel_options', UnicodeText, nullable=False),
        Column('rendered_kickstart_id', Integer, ForeignKey('rendered_kickstart.id',
                name='installation_rendered_kickstart_id_fk', ondelete='SET NULL')),
        Column('created', DateTime, nullable=False),
        Column('rebooted', DateTime, nullable=True),
        Column('install_started', DateTime, nullable=True),
        Column('install_finished', DateTime, nullable=True),
        Column('postinstall_finished', DateTime, nullable=True),
        Column('system_id', Integer, ForeignKey('system.id',
                name='installation_system_id_fk'), nullable=True),
        Column('recipe_id', Integer, ForeignKey('recipe.id',
                name='installation_recipe_id_fk'), nullable=True),
        mysql_engine='InnoDB'
    )
    op.add_column('command_queue', Column('installation_id', Integer,
            ForeignKey('installation.id', name='command_queue_installation_id_fk'),
            nullable=True))

    # Back-populate installations for system_resource rows.
    # Kernel options are left blank here, they are filled in by the 
    # 'commands-for-recipe-installations' online data migration script.
    op.execute("""
        INSERT INTO installation (distro_tree_id, kernel_options,
            rendered_kickstart_id, created, rebooted, install_started,
            install_finished, postinstall_finished, system_id, recipe_id)
        SELECT recipe.distro_tree_id,
            '',
            recipe.rendered_kickstart_id,
            reservation.start_time,
            recipe_resource.rebooted,
            recipe_resource.install_started,
            recipe_resource.install_finished,
            recipe_resource.postinstall_finished,
            system_resource.system_id,
            recipe.id
        FROM recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
        INNER JOIN system_resource ON recipe_resource.id = system_resource.id
        INNER JOIN reservation ON system_resource.reservation_id = reservation.id
        """)

    # Back-populate installations for virt_resource rows. These are easy.
    op.execute("""
        INSERT INTO installation (distro_tree_id, kernel_options,
            rendered_kickstart_id, created, rebooted, install_started,
            install_finished, postinstall_finished, recipe_id)
        SELECT recipe.distro_tree_id,
            virt_resource.kernel_options,
            recipe.rendered_kickstart_id,
            recipe.start_time,
            recipe_resource.rebooted,
            recipe_resource.install_started,
            recipe_resource.install_finished,
            recipe_resource.postinstall_finished,
            recipe.id
        FROM recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
        INNER JOIN virt_resource ON recipe_resource.id = virt_resource.id
        """)

    # Back-populate installations for guest_resource rows. These are even easier.
    op.execute("""
        INSERT INTO installation (distro_tree_id, kernel_options,
            rendered_kickstart_id, created, rebooted, install_started,
            install_finished, postinstall_finished, recipe_id)
        SELECT recipe.distro_tree_id,
            COALESCE(recipe.kernel_options, ''),
            recipe.rendered_kickstart_id,
            COALESCE(hostreservation.start_time, '1970-01-01 00:00:01'),
            recipe_resource.rebooted,
            recipe_resource.install_started,
            recipe_resource.install_finished,
            recipe_resource.postinstall_finished,
            recipe.id
        FROM recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
        INNER JOIN guest_resource ON recipe_resource.id = guest_resource.id
        INNER JOIN machine_guest_map ON machine_guest_map.guest_recipe_id = recipe.id
        INNER JOIN recipe hostrecipe ON machine_guest_map.machine_recipe_id = hostrecipe.id
        LEFT JOIN recipe_resource hostresource ON hostresource.recipe_id = hostrecipe.id
        LEFT JOIN system_resource ON hostresource.id = system_resource.id
        LEFT JOIN reservation hostreservation ON system_resource.reservation_id = hostreservation.id
        """)

    # Not dropping these command_queue columns because there is no way to get 
    # the data back in downgrade. Old commands won't have any associated 
    # installation.
    #op.drop_column('command_queue', 'callback')
    #op.drop_column('command_queue', 'distro_tree_id')
    #op.drop_column('command_queue', 'kernel_options')
    op.execute("""
        ALTER TABLE recipe
        DROP FOREIGN KEY recipe_rendered_kickstart_id_fk,
        DROP COLUMN rendered_kickstart_id
        """)
    op.execute("""
        ALTER TABLE recipe_resource
        DROP COLUMN rebooted,
        DROP COLUMN postinstall_finished,
        DROP COLUMN install_started,
        DROP COLUMN install_finished
        """)
    op.drop_column('virt_resource', 'kernel_options')


def downgrade():
    op.add_column('recipe', Column('rendered_kickstart_id', Integer,
            ForeignKey('rendered_kickstart.id', name='recipe_rendered_kickstart_id_fk'),
            nullable=True))
    op.execute("""
        UPDATE recipe
        INNER JOIN installation ON installation.recipe_id = recipe.id
        SET recipe.rendered_kickstart_id = installation.rendered_kickstart_id
        """)

    op.execute("""
        ALTER TABLE recipe_resource
        ADD COLUMN rebooted DATETIME DEFAULT NULL,
        ADD COLUMN install_started DATETIME DEFAULT NULL,
        ADD COLUMN install_finished DATETIME DEFAULT NULL,
        ADD COLUMN postinstall_finished DATETIME DEFAULT NULL
        """)
    op.execute("""
        UPDATE recipe_resource
        INNER JOIN recipe ON recipe_resource.recipe_id = recipe.id
        INNER JOIN installation ON installation.recipe_id = recipe.id
        SET recipe_resource.rebooted = installation.rebooted,
            recipe_resource.install_started = installation.install_started,
            recipe_resource.install_finished = installation.install_finished,
            recipe_resource.postinstall_finished = installation.postinstall_finished
        """)

    op.add_column('virt_resource', Column('kernel_options', Unicode(2048), nullable=True))
    op.execute("""
        UPDATE virt_resource
        INNER JOIN recipe_resource ON recipe_resource.id = virt_resource.id
        INNER JOIN recipe ON recipe_resource.recipe_id = recipe.id
        INNER JOIN installation ON installation.recipe_id = recipe.id
        SET virt_resource.kernel_options = installation.kernel_options
        """)

    drop_fk('command_queue', ['installation_id'])
    op.drop_column('command_queue', 'installation_id')
    op.drop_table('installation')
