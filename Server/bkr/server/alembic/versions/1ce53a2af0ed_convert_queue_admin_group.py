# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Convert queue_admin group to change_prio permission

Revision ID: 1ce53a2af0ed
Revises: 39885f53180f
Create Date: 2017-10-19 17:52:03.609655
"""

# revision identifiers, used by Alembic.
revision = '1ce53a2af0ed'
down_revision = '39885f53180f'

from alembic import op

def upgrade():
    # Create the permission if it doesn't exist.
    op.execute("""
        INSERT INTO permission (permission_name)
        SELECT 'change_prio'
        FROM DUAL
        WHERE NOT EXISTS
            (SELECT 1 FROM permission WHERE permission_name = 'change_prio')
        """)
    # Insert a mapping to give the new permission to the 'queue_admin' group,
    # if the group exists. It was never created by beaker-init so it will only
    # exist in sites where the admin had manually created it.
    op.execute("""
        INSERT INTO group_permission (group_id, permission_id)
        SELECT group_id, (SELECT permission_id FROM permission WHERE permission_name = 'change_prio')
        FROM tg_group
        WHERE group_name = 'queue_admin'
        """)

def downgrade():
    pass # nothing to roll back as the new permission will be ignored by old code
