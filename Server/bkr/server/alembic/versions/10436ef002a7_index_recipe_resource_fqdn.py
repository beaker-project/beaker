# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""index recipe_resource.fqdn

Revision ID: 10436ef002a7
Revises: 53942581687f
Create Date: 2015-01-27 10:51:51.552217

"""

# revision identifiers, used by Alembic.
revision = '10436ef002a7'
down_revision = '53942581687f'

from alembic import op

def upgrade():
    op.create_index(u'ix_recipe_resource_fqdn', 'recipe_resource', ['fqdn'])

def downgrade():
    op.drop_index(u'ix_recipe_resource_fqdn', table_name='recipe_resource')
