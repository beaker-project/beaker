# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add missing FKs

Revision ID: 1c10e575800c
Revises: 2c0f1c0a668b
Create Date: 2014-10-10 11:46:31.840962

"""

# revision identifiers, used by Alembic.
revision = '1c10e575800c'
down_revision = '2c0f1c0a668b'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import create_fk_if_absent

def upgrade():
    create_fk_if_absent(
            'log_recipe', 'recipe',
            ['recipe_id'], ['id'])
    create_fk_if_absent(
            'log_recipe_task', 'recipe_task',
            ['recipe_task_id'], ['id'])
    create_fk_if_absent(
            'log_recipe_task_result', 'recipe_task_result',
            ['recipe_task_result_id'], ['id'])
    create_fk_if_absent(
            'task_property_needed', 'task',
            ['task_id'], ['id'])

def downgrade():
    pass # no downgrade because this is fixing up a schema mistake
