# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Delete duplicate rows in osmajor_install_options

Revision ID: 5ab8960cdb43
Revises: 171c07fb4970
Create Date: 2015-08-21 16:43:35.335744
"""

# revision identifiers, used by Alembic.
revision = '5ab8960cdb43'
down_revision = '171c07fb4970'

from alembic import op

def upgrade():
    op.execute("""
        DELETE FROM x
        USING osmajor_install_options x
        INNER JOIN (SELECT MAX(id) AS max_id, osmajor_id, arch_id
            FROM osmajor_install_options
            GROUP BY osmajor_id, arch_id) y
        ON x.osmajor_id = y.osmajor_id AND
            (x.arch_id = y.arch_id OR x.arch_id IS NULL AND y.arch_id IS NULL) AND
            x.id != y.max_id
        """)

def downgrade():
    pass # no downgrade because we are fixing up old data
