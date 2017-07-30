# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""convert glance image id to UUID

Revision ID: 1a7dec79baa4
Revises: f18df089261
Create Date: 2017-07-28 15:35:54.029695

"""

# revision identifiers, used by Alembic.
revision = '1a7dec79baa4'
down_revision = 'f18df089261'

from alembic import op


def upgrade():
    op.execute("""
        ALTER TABLE openstack_region 
        CHANGE ipxe_image_id ipxe_image_id_old varchar(2048),
        ADD COLUMN ipxe_image_id binary(16)
        """)
    op.execute("""
        UPDATE openstack_region 
        SET ipxe_image_id=UNHEX(REPLACE(ipxe_image_id_old, '-', ''))
    """)
    op.execute("""
        ALTER TABLE openstack_region 
        DROP ipxe_image_id_old
    """)


def downgrade():
    op.execute("""
        ALTER TABLE openstack_region 
        CHANGE ipxe_image_id ipxe_image_id_old binary(16),
        ADD COLUMN ipxe_image_id varchar(2048)
    """)
    op.execute("""
        UPDATE openstack_region 
        SET ipxe_image_id=LOWER(CONCAT(SUBSTR(HEX(ipxe_image_id_old), 1, 8), '-', 
        SUBSTR(HEX(ipxe_image_id_old), 9, 4), '-', 
        SUBSTR(HEX(ipxe_image_id_old), 13, 4), '-', 
        SUBSTR(HEX(ipxe_image_id_old), 17, 4), '-', 
        SUBSTR(HEX(ipxe_image_id_old), 21, 12)))
    """)
    op.execute("""
        ALTER TABLE openstack_region 
        DROP ipxe_image_id_old
    """)
