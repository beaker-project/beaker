# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""clear obsoleted data on system_recipe_map

Revision ID: da9939e1007
Revises: 53942581687f
Create Date: 2015-02-05 14:26:03.937974

"""

# revision identifiers, used by Alembic.
revision = 'da9939e1007'
down_revision = '10436ef002a7'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("""
        DELETE FROM system_recipe_map
        USING system_recipe_map
        LEFT JOIN recipe
        ON system_recipe_map.recipe_id = recipe.id
        WHERE recipe.status in ('Cancelled', 'Aborted')
        """)
def downgrade():
    pass # no downgrade because we are fixing up old data left by a bug
