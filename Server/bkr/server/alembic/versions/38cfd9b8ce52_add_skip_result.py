# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""add Skip result

Revision ID: 38cfd9b8ce52
Revises: 2e171e6198e6
Create Date: 2016-07-05 12:56:44.933243
"""

# revision identifiers, used by Alembic.
revision = '38cfd9b8ce52'
down_revision = '2e171e6198e6'

from alembic import op
from bkr.server.alembic.migration_utils import add_enum_value, drop_enum_value

def upgrade():
    add_enum_value('job', 'result', u'Skip', nullable=False)
    add_enum_value('recipe_set', 'result', u'Skip', nullable=False)
    add_enum_value('recipe', 'result', u'Skip', nullable=False)
    add_enum_value('recipe_task', 'result', u'Skip', nullable=False)
    add_enum_value('recipe_task_result', 'result', u'Skip', nullable=False)

def downgrade():
    drop_enum_value('job', 'result', u'Skip', nullable=False)
    drop_enum_value('recipe_set', 'result', u'Skip', nullable=False)
    drop_enum_value('recipe', 'result', u'Skip', nullable=False)
    drop_enum_value('recipe_task', 'result', u'Skip', nullable=False)
    drop_enum_value('recipe_task_result', 'result', u'Skip', nullable=False)
