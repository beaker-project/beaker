# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Access Policies for System Pools

Revision ID: da3a49774b0
Revises: 1c444555ea3d
Create Date: 2015-03-03 15:17:20.504251

"""

# revision identifiers, used by Alembic.
revision = 'da3a49774b0'
down_revision = '1c444555ea3d'

from alembic import op

def upgrade():
    op.execute("""
       ALTER TABLE system
       ADD COLUMN custom_access_policy_id INT DEFAULT NULL,
       ADD CONSTRAINT custom_access_policy_id_fk
       FOREIGN KEY (custom_access_policy_id)
       REFERENCES system_access_policy (id),
       ADD COLUMN active_access_policy_id INT DEFAULT NULL,
       ADD CONSTRAINT active_access_policy_id_fk
       FOREIGN KEY (active_access_policy_id)
       REFERENCES system_access_policy (id)
    """)

    op.execute("""
       UPDATE system INNER JOIN system_access_policy
       ON system_access_policy.system_id = system.id
       SET custom_access_policy_id=system_access_policy.id, active_access_policy_id=system_access_policy.id
    """)

    op.execute("""
       ALTER TABLE system_access_policy
       DROP FOREIGN KEY system_access_policy_system_id_fk,
       DROP COLUMN system_id
    """)

    # Add a dummy column to assist setting up system pool policies
    op.execute("""
       ALTER TABLE system_access_policy
       ADD system_pool_id int
    """)
    op.execute("""
       INSERT INTO system_access_policy(system_pool_id)
       SELECT id FROM system_pool
    """)

    op.execute("""
       INSERT INTO system_access_policy_rule(policy_id, user_id, group_id, permission)
       SELECT system_access_policy.id, NULL, NULL, 'view'
       FROM system_access_policy
       INNER JOIN system_pool ON system_access_policy.system_pool_id = system_pool.id
     """)

    op.execute("""
       ALTER TABLE system_pool
       ADD COLUMN access_policy_id INT NOT NULL
    """)
    op.execute("""
       UPDATE system_pool INNER JOIN system_access_policy
       ON system_access_policy.system_pool_id=system_pool.id
       SET system_pool.access_policy_id=system_access_policy.id
    """)
    op.execute("""
       ALTER TABLE system_pool
       ADD CONSTRAINT system_pool_access_policy_id_fk
       FOREIGN KEY (access_policy_id)
       REFERENCES system_access_policy (id)
    """)
    # Drop the dummy column
    op.execute("""
       ALTER TABLE system_access_policy
       DROP system_pool_id
    """)

def downgrade():

    # add system_id to system_access_policy_table
    op.execute("""
       ALTER TABLE system_access_policy
       ADD COLUMN system_id INT DEFAULT NULL ,
       ADD CONSTRAINT system_access_policy_system_id_fk
       FOREIGN KEY (system_id)
       REFERENCES system (id)
    """)

    op.execute("""
       UPDATE system_access_policy INNER JOIN system
       ON system_access_policy.id = system.custom_access_policy_id
       SET system_access_policy.system_id=system.id
    """)

    op.execute("""
       ALTER TABLE system
       DROP FOREIGN KEY custom_access_policy_id_fk,
       DROP COLUMN custom_access_policy_id,
       DROP FOREIGN KEY active_access_policy_id_fk,
       DROP COLUMN active_access_policy_id
    """)

    op.execute("""
       ALTER TABLE system_pool
       DROP FOREIGN KEY system_pool_access_policy_id_fk,
       DROP COLUMN access_policy_id
    """)
