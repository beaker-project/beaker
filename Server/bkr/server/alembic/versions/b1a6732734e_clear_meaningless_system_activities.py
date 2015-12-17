# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Clear system activity entries for changing 'Custom Access Policy' to
'Custom access policy'

Revision ID: b1a6732734e
Revises: 54395adc8646
Create Date: 2015-12-16 11:48:22.408156

"""

# revision identifiers, used by Alembic.
revision = 'b1a6732734e'
down_revision = '54395adc8646'

from alembic import op

def upgrade():
    op.execute("""
        DELETE system_activity FROM
        system_activity INNER JOIN activity ON system_activity.id = activity.id
        WHERE activity.type = 'system_activity'
        AND activity.old_value = 'Custom Access Policy'
        AND activity.new_value = 'Custom access policy'
        """)
    op.execute("""
        DELETE FROM activity
        WHERE type = 'system_activity'
        AND old_value = 'Custom Access Policy'
        AND new_value = 'Custom access policy'
        """)

def downgrade():
    pass # no downgrade because we are fixing up old data left by a bug
