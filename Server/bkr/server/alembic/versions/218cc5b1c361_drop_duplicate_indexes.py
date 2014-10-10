# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Drop duplicate indexes

Revision ID: 218cc5b1c361
Revises: 41763e5d07cb
Create Date: 2014-10-10 13:27:38.315552

"""

# revision identifiers, used by Alembic.
revision = '218cc5b1c361'
down_revision = '41763e5d07cb'

from alembic import op
import sqlalchemy as sa

def upgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('job')
    if (any(index['name'] == 'result_2' for index in indexes) and
            any(index['name'] == 'status_2' for index in indexes)):
        op.execute("ALTER TABLE job DROP INDEX result_2, DROP INDEX status_2")
    indexes = sa.inspect(op.get_bind()).get_indexes('recipe_set')
    if (any(index['name'] == 'result_2' for index in indexes) and
            any(index['name'] == 'status_2' for index in indexes) and
            any(index['name'] == 'priority_2' for index in indexes)):
        op.execute("""
            ALTER TABLE recipe_set
            DROP INDEX result_2,
            DROP INDEX status_2,
            DROP INDEX priority_2
            """)

def downgrade():
    pass # no downgrade because this was a schema mistake
