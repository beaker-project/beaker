# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Separate command_queue from activity

Also add new start_time and finish_time columns while we're at it.

Revision ID: 3028e6a6e3d7
Revises: 38cfd9b8ce52
Create Date: 2016-08-08 16:31:30.583860

"""

# revision identifiers, used by Alembic.
revision = '3028e6a6e3d7'
down_revision = '38cfd9b8ce52'

import logging
from alembic import op
from sqlalchemy import select, insert, update, Column, Integer, ForeignKey, \
        String, DateTime, Enum
# These are the "lightweight" SQL expression versions (not using metadata):
from sqlalchemy.sql.expression import table, column
from bkr.server.alembic.migration_utils import find_fk

log = logging.getLogger(__name__)

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
        ADD COLUMN start_time DATETIME DEFAULT NULL AFTER queue_time,
        ADD INDEX (start_time),
        ADD COLUMN finish_time DATETIME DEFAULT NULL AFTER start_time,
        ADD INDEX (finish_time),
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
    # We have to deal with the possibility that new command_queue rows have 
    # been inserted after the upgrade, which will have ids conflicting with 
    # other existing rows in activity...
    # We will build a new copy of command_queue for the downgrade.
    op.create_table('command_queue_downgraded',
            Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
            Column('system_id', Integer, ForeignKey('system.id',
                onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
            Column('status', Enum(u'Queued', u'Running', u'Completed',
                u'Failed', u'Aborted'), nullable=False, index=True),
            Column('task_id', String(255)),
            Column('delay_until', DateTime),
            Column('quiescent_period', Integer),
            Column('updated', DateTime),
            Column('installation_id', Integer, ForeignKey('installation.id')),
            mysql_engine='InnoDB')
    # First we find the lowest conflicting id (if any):
    connection = op.get_bind()
    first_conflicting_id = connection.scalar("""
        SELECT MIN(command_queue.id)
        FROM command_queue
        INNER JOIN activity ON command_queue.id = activity.id
        """)
    if first_conflicting_id:
        # We have to renumber all command_queue rows from this id and above.
        # We do it one row at a time in Python land, since we have to insert 
        # into activity to find each new id...
        log.debug('Renumbering command_queue rows starting from %s',
                first_conflicting_id)
        # Lightweight table definitions for building SQLAlchemy queries:
        activity_table = table('activity',
                column('id'), column('user_id'), column('created'),
                column('type'), column('field_name'), column('service'),
                column('action'), column('old_value'), column('new_value'))
        command_queue_table = table('command_queue',
                column('id'), column('user_id'), column('service'),
                column('queue_time'), column('start_time'),
                column('finish_time'), column('system_id'), column('action'),
                column('status'), column('delay_until'),
                column('quiescent_period'), column('error_message'),
                column('installation_id'))
        command_queue_downgraded = table('command_queue_downgraded',
                column('id'), column('system_id'), column('status'),
                column('task_id'), column('delay_until'),
                column('quiescent_period'), column('updated'),
                column('installation_id'))
        conflicting_rows = connection.execute(command_queue_table.select()
                .where(command_queue_table.c.id >= first_conflicting_id))
        for row in conflicting_rows:
            result = connection.execute(insert(activity_table).values(
                    user_id=row.user_id,
                    created=row.queue_time,
                    type=u'command_activity',
                    field_name=u'Command',
                    service=row.service,
                    action=row.action,
                    old_value=u'',
                    new_value=(row.error_message or '')[:60]))
            new_id = result.lastrowid
            connection.execute(insert(command_queue_downgraded).values(
                    id=new_id,
                    system_id=row.system_id,
                    status=row.status,
                    task_id='',
                    delay_until=row.delay_until,
                    quiescent_period=row.quiescent_period,
                    updated=row.queue_time,
                    installation_id=row.installation_id))
    # For all the older rows which existed before the upgrade, we can use 
    # a straightforward INSERT INTO activity, to essentially just restore the 
    # rows we DELETE'd in the upgrade.
    if first_conflicting_id:
        where = 'WHERE id < %s' % first_conflicting_id
    else:
        where = ''
    op.execute("""
        INSERT INTO activity (id, user_id, created, type, field_name, service,
            action, old_value, new_value)
        SELECT id, user_id, queue_time, 'command_activity', 'Command', service,
            action, '', SUBSTRING(error_message, 1, 60)
        FROM command_queue
        """ + where)
    op.execute("""
        INSERT INTO command_queue_downgraded (id, system_id, status, task_id,
            delay_until, quiescent_period, updated, installation_id)
        SELECT id, system_id, status, '', delay_until, quiescent_period,
            queue_time, installation_id
        FROM command_queue
        """ + where)
    op.drop_table('command_queue')
    op.rename_table('command_queue_downgraded', 'command_queue')
