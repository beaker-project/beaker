# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix NULLability and FKs on a number of old columns

Revision ID: 3fc28d7eb6d3
Revises: 2d4258bf3f16
Create Date: 2014-10-10 11:17:01.604853

"""

# revision identifiers, used by Alembic.
revision = '3fc28d7eb6d3'
down_revision = '2d4258bf3f16'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import find_fk, create_fk_if_absent,\
    drop_fk

def upgrade():
    # This was an oversight in commit d8df7f836 for bug 598781.
    op.alter_column('recipe', 'autopick_random',
            existing_type=sa.Boolean, nullable=False)
    # This was an oversight in the commits for retention tags.
    op.alter_column('retention_tag', 'expire_in_days',
            existing_type=sa.Integer, nullable=False)
    op.alter_column('retention_tag', 'needs_product',
            existing_type=sa.Boolean, nullable=False)
    # This was an oversight in commits for "removing tasks".
    op.alter_column('task', 'valid',
            existing_type=sa.Boolean, nullable=False)
    # This was an oversight in commit 747902274 for bug 596410.
    op.alter_column('recipe_set_nacked', 'created',
            existing_type=sa.DateTime, nullable=False)
    # The log_* tables unfortunately require special treatment. They are so big 
    # that we need to avoid running multiple ALTER TABLEs on them in a single 
    # upgrade, because each ALTER TABLE is so expensive (sometimes hours!)
    # The missing nullability was an oversight in commit dbf2a15de for bug 751949.
    # The FKs may be missing on very old databases, dating back to when we were 
    # accidentally creating tables in MyISAM instead of InnoDB. However the FKs 
    # will exist on more recently created databases, so we need two different 
    # ALTER TABLE statements depending on whether we want to add the FKs ...
    if find_fk('log_recipe', ['recipe_id']) is None:
        op.execute("""
            ALTER TABLE log_recipe
            MODIFY recipe_id INT NOT NULL,
            ADD CONSTRAINT fk_log_recipe_recipe_id
                FOREIGN KEY (recipe_id) REFERENCES recipe (id)
            """)
    else:
        op.alter_column('log_recipe', 'recipe_id',
                existing_type=sa.Integer, nullable=False)
    if find_fk('log_recipe_task', ['recipe_task_id']) is None:
        op.execute("""
            ALTER TABLE log_recipe_task
            MODIFY recipe_task_id INT NOT NULL,
            ADD CONSTRAINT fk_log_recipe_task_recipe_task_id
                FOREIGN KEY (recipe_task_id) REFERENCES recipe_task (id)
            """)
    else:
        op.alter_column('log_recipe_task', 'recipe_task_id',
                existing_type=sa.Integer, nullable=False)
    if find_fk('log_recipe_task_result', ['recipe_task_result_id']) is None:
        op.execute("""
            ALTER TABLE log_recipe_task_result
            MODIFY recipe_task_result_id INT NOT NULL,
            ADD CONSTRAINT fk_log_recipe_task_result_recipe_task_result_id
                FOREIGN KEY (recipe_task_result_id) REFERENCES recipe_task_result (id)
            """)
    else:
        op.alter_column('log_recipe_task_result', 'recipe_task_result_id',
                existing_type=sa.Integer, nullable=False)
    # This was an oversight in commit e591d682 for bug 595801.
    drop_fk('job', ['retention_tag_id'])
    op.alter_column('job', 'retention_tag_id',
            existing_type=sa.Integer, nullable=False)
    op.create_foreign_key(None, 'job', 'retention_tag',
                ['retention_tag_id'], ['id'])
    # This was an oversight in commit eb8cded8 for bug 560695.
    op.alter_column('lab_controller', 'disabled',
            existing_type=sa.Boolean, nullable=False)
    # This was an oversight in commit 1ec1b4f1 for bug 703885.
    op.alter_column('tg_user', 'disabled',
            existing_type=sa.Boolean, nullable=False)
    # As above, this FK may be missing on very old databases due to MyISAM.
    create_fk_if_absent(
            'task_property_needed', 'task',
            ['task_id'], ['id'])

def downgrade():
    op.alter_column('recipe', 'autopick_random',
            existing_type=sa.Boolean, nullable=True)
    op.alter_column('retention_tag', 'expire_in_days',
            existing_type=sa.Integer, nullable=True)
    op.alter_column('retention_tag', 'needs_product',
            existing_type=sa.Boolean, nullable=True)
    op.alter_column('task', 'valid',
            existing_type=sa.Boolean, nullable=True,
            server_default='1')
    # No downgrade for the other columns as they were just fixing mistakes in 
    # earlier upgrades.
