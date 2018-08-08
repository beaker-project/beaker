# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix columns with incorrect DECIMAL scale

Very old Beaker instances may have some columns incorrectly as DECIMAL(10,2)
instead of DECIMAL(10,0) as they are declared at the Python level.

Revision ID: 292b2e042673
Revises: 4d4e0a92ee10
Create Date: 2018-08-08 16:34:11.942581
"""

# revision identifiers, used by Alembic.
revision = '292b2e042673'
down_revision = '4d4e0a92ee10'

from alembic import op
from sqlalchemy.types import Numeric
from bkr.server.alembic.migration_utils import find_column_type

def upgrade():
    bad = [
        ('labinfo', 'weight'),
        ('labinfo', 'wattage'),
        ('labinfo', 'cooling'),
        ('recipe_task_result', 'score'),
    ]
    for table, column in bad:
        column_type = find_column_type(table, column)
        if column_type.scale != 0:
            op.alter_column(table, column, type_=Numeric(10, 0))

def downgrade():
    pass # no downgrade as this was a schema mistake
