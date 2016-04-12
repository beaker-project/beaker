
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Data migration script related to Alembic revision 51637c12cbd9, which creates 
the installation table.

The Alembic migration back-populates the installation table based on existing 
recipe_resource rows, however for system_resource (recipes run on systems) the 
migration leaves kernel_options empty. This online migration is filling in the 
kernel options, which requires matching up command_queue rows to their 
corresponding recipes.

There is no direct record of the relationship between commands and the recipe 
that triggered them. So we have to guess, by finding commands enqueued between 
the start and finish times of the reservation corresponding to each recipe.

The 'auto_cmd_handler' callback string is the indicator that a command was 
enqueued by the scheduler as part of provisioning a recipe, rather than by 
a user manually or by release action ReProvision.
"""

import logging
from sqlalchemy import inspect

logger = logging.getLogger(__name__)

def migrate(metadata):
    if not any(info['name'] == 'callback' for info
            in inspect(metadata.bind).get_columns('command_queue')):
        logger.info('Skipping migration: command_queue.callback column does not exist, '
                'this database was not created by Beaker < 23')
        return

    # Associate commands for provisioning recipes with their newly created 
    # installation rows.
    while True:
        logger.info('Associating commands with installation (one batch)')
        with metadata.bind.begin() as connection:
            result = connection.execute("""
                UPDATE command_queue
                SET installation_id = (
                    SELECT installation.id
                    FROM reservation
                    INNER JOIN system_resource ON system_resource.reservation_id = reservation.id
                    INNER JOIN recipe_resource ON system_resource.id = recipe_resource.id
                    INNER JOIN installation ON recipe_resource.recipe_id = installation.recipe_id
                    WHERE system_resource.system_id = command_queue.system_id
                        AND reservation.start_time <= command_queue.updated
                    ORDER BY reservation.start_time DESC LIMIT 1
                )
                WHERE callback = 'bkr.server.model.auto_cmd_handler'
                    AND command_queue.installation_id IS NULL
                ORDER BY id DESC
                LIMIT 4000
                """)
        if result.rowcount == 0:
            logger.info('Done associating commands with installation')
            break
        else:
            logger.info('Updated %d rows', result.rowcount)

    # Now go back and fill in kernel_options for the installations, copied from 
    # the configure_netboot command.
    logger.info('Populating kernel options for installations')
    with metadata.bind.begin() as connection:
        connection.execute("""
            UPDATE installation
            INNER JOIN command_queue ON command_queue.installation_id = installation.id
            INNER JOIN activity ON activity.id = command_queue.id
            SET installation.kernel_options = command_queue.kernel_options
            WHERE activity.action = 'configure_netboot'
                AND command_queue.kernel_options IS NOT NULL
                AND installation.kernel_options = ''
            """)
    logger.info('Done populating kernel options for installations')
