# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Index activity columns

Revision ID: 214c585364d9
Revises: da3a49774b0
Create Date: 2015-03-03 17:19:31.404398

"""

# revision identifiers, used by Alembic.
revision = '214c585364d9'
down_revision = 'da3a49774b0'

from alembic import op

def upgrade():
    op.execute("""
        ALTER TABLE activity
        ADD INDEX ix_activity_action (action),
        ADD INDEX ix_activity_field_name (field_name),
        ADD INDEX ix_activity_service (service),
        ADD INDEX ix_activity_type (type)
        """)

def downgrade():
    op.execute("""
        ALTER TABLE activity
        DROP INDEX ix_activity_action,
        DROP INDEX ix_activity_field_name,
        DROP INDEX ix_activity_service,
        DROP INDEX ix_activity_type
        """)
