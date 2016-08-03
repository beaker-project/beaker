# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add data_migration table

Revision ID: 2e171e6198e6
Revises: 15d3fad78656
Create Date: 2016-08-03 11:11:55.680872
"""

# revision identifiers, used by Alembic.
revision = '2e171e6198e6'
down_revision = '15d3fad78656'

from alembic import op
from sqlalchemy import Column, Integer, Unicode, DateTime

def upgrade():
    op.create_table('data_migration',
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(255), nullable=False, unique=True),
            Column('finish_time', DateTime),
            mysql_engine='InnoDB')

def downgrade():
    op.drop_table('data_migration')
