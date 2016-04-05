# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Replace recipe_set_nacked with recipe_set.waived

Revision ID: 3c5510511fd9
Revises: 35118bee62f2
Create Date: 2015-11-11 13:26:06.954156

"""

# revision identifiers, used by Alembic.
revision = '3c5510511fd9'
down_revision = '35118bee62f2'

from alembic import op
from sqlalchemy import Column, Boolean

def upgrade():
    op.add_column('recipe_set', Column('waived', Boolean, nullable=False))
    # In theory the response table can have anything with any id, but 
    # realistically 'ack' is always 1 and 'nak' is always 2 because they are 
    # populated by beaker-init, and there can't be any other responses because 
    # the code has no support for anything else.
    # So we consider a recipe set waived if it has response id 2.
    op.execute("""
        UPDATE recipe_set
        INNER JOIN recipe_set_nacked ON recipe_set_nacked.recipe_set_id = recipe_set.id
        SET waived = TRUE
        WHERE recipe_set_nacked.response_id = 2
        """)
    # Not dropping recipe_set_nacked or response tables, so that they will 
    # still exist, holding old data, in case of downgrade.

def downgrade():
    op.drop_column('recipe_set', 'waived')
