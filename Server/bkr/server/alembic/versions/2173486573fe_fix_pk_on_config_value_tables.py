# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix PK on config value tables

Revision ID: 2173486573fe
Revises: 5ab8960cdb43
Create Date: 2015-10-23 13:35:02.391212

"""

# revision identifiers, used by Alembic.
revision = '2173486573fe'
down_revision = '5ab8960cdb43'

from alembic import op

def upgrade():
    op.execute("""
        ALTER TABLE config_value_string
        DROP PRIMARY KEY,
        ADD PRIMARY KEY (id)
        """)
    op.execute("""
        ALTER TABLE config_value_int
        DROP PRIMARY KEY,
        ADD PRIMARY KEY (id)
        """)

def downgrade():
    op.execute("""
        ALTER TABLE config_value_string
        DROP PRIMARY KEY,
        ADD PRIMARY KEY (id, config_item_id)
        """)
    op.execute("""
        ALTER TABLE config_value_int
        DROP PRIMARY KEY,
        ADD PRIMARY KEY (id, config_item_id)
        """)
