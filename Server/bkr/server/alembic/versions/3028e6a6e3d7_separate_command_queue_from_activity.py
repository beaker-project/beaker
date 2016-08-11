# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Separate command_queue from activity

Revision ID: 3028e6a6e3d7
Revises: 38cfd9b8ce52
Create Date: 2016-08-08 16:31:30.583860

"""

# revision identifiers, used by Alembic.
revision = '3028e6a6e3d7'
down_revision = '38cfd9b8ce52'

from alembic import op
from sqlalchemy import inspect
from bkr.server.alembic.migration_utils import find_fk

def upgrade():
    id_constraint_name = find_fk('command_queue', ['id'])
    op.execute("""
        ALTER TABLE command_queue
        DROP COLUMN updated,
        DROP COLUMN task_id,
        DROP FOREIGN KEY %s,
        MODIFY id INT NOT NULL AUTO_INCREMENT,
        ADD COLUMN user_id INT DEFAULT NULL AFTER id,
        ADD CONSTRAINT command_queue_user_id_fk
            FOREIGN KEY (user_id) REFERENCES tg_user (user_id),
        ADD COLUMN service VARCHAR(100) NOT NULL AFTER user_id,
        ADD INDEX (service),
        ADD COLUMN queue_time DATETIME NOT NULL AFTER service,
        ADD INDEX (queue_time),
        ADD COLUMN action VARCHAR(40) NOT NULL after system_id,
        ADD INDEX (action),
        ADD COLUMN error_message VARCHAR(4000) DEFAULT NULL AFTER quiescent_period
        """
        % id_constraint_name)
    op.execute("""
        UPDATE command_queue
        INNER JOIN activity ON activity.id = command_queue.id
        SET command_queue.user_id = activity.user_id,
        command_queue.service = activity.service,
        command_queue.queue_time = activity.created,
        command_queue.action = activity.action,
        command_queue.error_message = NULLIF(activity.new_value, '')
        """)
    op.execute("""
        DELETE FROM activity
        WHERE type = 'command_activity'
        """)

def downgrade():
    op.execute("""
        INSERT INTO activity (id, user_id, created, type, field_name, service,
            action, old_value, new_value)
        SELECT id, user_id, queue_time, 'command_activity', 'Command', service,
            action, '', SUBSTRING(error_message, 1, 60)
        FROM command_queue
        """)
    op.execute("""
        ALTER TABLE command_queue
        MODIFY id INT NOT NULL,
        ADD CONSTRAINT command_queue_id_fk
            FOREIGN KEY (id) REFERENCES activity (id),
        DROP FOREIGN KEY command_queue_user_id_fk,
        DROP COLUMN user_id,
        DROP COLUMN service,
        DROP COLUMN queue_time,
        DROP COLUMN action,
        DROP COLUMN error_message,
        ADD COLUMN updated DATETIME,
        ADD COLUMN task_id VARCHAR(255)
        """)
