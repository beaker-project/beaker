# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""remove ids from task join tables

Revision ID: 1626ad29c170
Revises: 3a141cda8089
Create Date: 2016-10-24 15:21:13.433339

"""

# revision identifiers, used by Alembic.
revision = '1626ad29c170'
down_revision = '4e8b85360255'

from alembic import op
from bkr.server.alembic import migration_utils


def upgrade():
    # remove any orphans and then duplicates before the current unique column is dropped
    op.execute("""
        DELETE FROM task_exclude_osmajor
        WHERE task_id IS NULL
        OR osmajor_id IS NULL
        """)
    op.execute("""
        DELETE FROM task_exclude_arch
        WHERE task_id IS NULL
        OR arch_id IS NULL
        """)
    op.execute("""
        DELETE a
        FROM task_exclude_osmajor a
        LEFT JOIN (
            SELECT MAX(id) max_id, task_id, osmajor_id
            FROM task_exclude_osmajor
            GROUP BY task_id, osmajor_id) b
            ON a.id = max_id
            AND a.task_id = b.task_id
            AND a.osmajor_id = b.osmajor_id
        WHERE b.max_id IS NULL
        """)
    op.execute("""
        DELETE a
        FROM task_exclude_arch a
        LEFT JOIN (
            SELECT MAX(id) max_id, task_id, arch_id
            FROM task_exclude_arch
            GROUP BY task_id, arch_id) b
            ON a.id = max_id
            AND a.task_id = b.task_id
            AND a.arch_id = b.arch_id
        WHERE b.max_id IS NULL
        """)
    # do the alter statements after the data has been cleaned up in the respective
    # tables
    task_osmajor_fk = migration_utils.find_fk('task_exclude_osmajor', ['task_id'])
    osmajor_fk = migration_utils.find_fk('task_exclude_osmajor', ['osmajor_id'])
    # alter the constraints and primary keys on the task_exclude_osmajor table
    # - drop redundant primary key column id of task_id and osmajor_id
    # - create new composite primary key
    # - alter the foreign keys constraints for task_id and osmajor_id to have cascade rules
    # - alter task_id and osmajor_id to NOT NULL
    op.execute("""
        ALTER TABLE task_exclude_osmajor
            DROP COLUMN id,
            ADD PRIMARY KEY(task_id, osmajor_id),
            DROP FOREIGN KEY `{task_osmajor_fk}`,
            ADD CONSTRAINT `task_exclude_osmajor_fk_task` FOREIGN KEY (`task_id`) REFERENCES `task`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
            DROP FOREIGN KEY `{osmajor_fk}`,
            ADD CONSTRAINT `task_exclude_osmajor_fk_osmajor` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
            MODIFY COLUMN task_id INT(11) NOT NULL,
            MODIFY COLUMN osmajor_id INT(11) NOT NULL
        """.format(task_osmajor_fk=task_osmajor_fk, osmajor_fk=osmajor_fk))

    task_arch_fk = migration_utils.find_fk('task_exclude_arch', ['task_id'])
    arch_fk = migration_utils.find_fk('task_exclude_arch', ['arch_id'])
    # alter the constraints and primary key on the task_exclude_arch table
    # - drop redundant primary key column id
    # - create new composite primary key of task_id and arch_id
    # - alter the foreign keys constraints for task_id and archr_id to have cascade rules
    # - alter task_id and arch_id to NOT NULL
    op.execute("""
        ALTER TABLE task_exclude_arch
            DROP COLUMN id,
            ADD PRIMARY KEY(task_id, arch_id),
            DROP FOREIGN KEY `{task_arch_fk}`,
            ADD CONSTRAINT `task_exclude_arch_fk_task` FOREIGN KEY (`task_id`) REFERENCES `task`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
            DROP FOREIGN KEY `{arch_fk}`,
            ADD CONSTRAINT `task_exclude_arch_fk_arch` FOREIGN KEY (`arch_id`) REFERENCES `arch`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
            MODIFY COLUMN task_id INT(11) NOT NULL,
            MODIFY COLUMN arch_id INT(11) NOT NULL
        """.format(task_arch_fk=task_arch_fk, arch_fk=arch_fk))


def downgrade():
    task_osmajor_fk = migration_utils.find_fk('task_exclude_osmajor', ['task_id'])
    osmajor_fk = migration_utils.find_fk('task_exclude_osmajor', ['osmajor_id'])
    op.execute("""
        ALTER TABLE task_exclude_osmajor
            DROP FOREIGN KEY `{task_osmajor_fk}`,
            DROP FOREIGN KEY `{osmajor_fk}`,
            DROP PRIMARY KEY,
            ADD COLUMN `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
            ADD CONSTRAINT `task_exclude_osmajor_ibfk_task` FOREIGN KEY (`task_id`) REFERENCES `task`(`id`),
            ADD CONSTRAINT `task_exclude_osmajor_ibfk_osmajor` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor`(`id`),
            MODIFY COLUMN task_id INT(11),
            MODIFY COLUMN osmajor_id INT(11)
        """.format(task_osmajor_fk=task_osmajor_fk, osmajor_fk=osmajor_fk))

    task_arch_fk = migration_utils.find_fk('task_exclude_arch', ['task_id'])
    arch_fk = migration_utils.find_fk('task_exclude_arch', ['arch_id'])
    op.execute("""
        ALTER TABLE task_exclude_arch
            DROP FOREIGN KEY `{task_arch_fk}`,
            DROP FOREIGN KEY `{arch_fk}`,
            DROP PRIMARY KEY,
            ADD COLUMN `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
            ADD CONSTRAINT `task_exclude_arch_ibfk_task` FOREIGN KEY (`task_id`) REFERENCES `task`(`id`),
            ADD CONSTRAINT `task_exclude_arch_ibfk_arch` FOREIGN KEY (`arch_id`) REFERENCES `arch`(`id`),
            MODIFY COLUMN task_id INT(11),
            MODIFY COLUMN arch_id INT(11)
        """.format(task_arch_fk=task_arch_fk, arch_fk=arch_fk))
