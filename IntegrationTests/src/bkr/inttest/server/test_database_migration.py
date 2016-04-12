# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import unittest2 as unittest
import pkg_resources
import sqlalchemy
from turbogears import config
from turbogears.database import metadata
from bkr.server.tools.init import upgrade_db, downgrade_db, check_db, \
        run_online_data_migration
from sqlalchemy.orm import create_session
from sqlalchemy.sql import func
from alembic.environment import MigrationContext
from bkr.server.model import SystemPool, System, SystemAccessPolicy, Group, User, \
        OSMajor, OSMajorInstallOptions, GroupMembershipType, SystemActivity, \
        Activity, RecipeSetComment, Recipe, RecipeSet, CommandActivity

def has_initial_sublist(larger, prefix):
    """ Return true iff list *prefix* is an initial sublist of list 
    *larger*. Like .startswith() for lists. """
    if len(prefix) > len(larger):
        return False
    for i, value in enumerate(prefix):
        if larger[i] != value:
            return False
    return True

class MigrationTest(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        # For the database migration tests we use a side database (usually 
        # 'beaker_migration_test') separate from the main one used in tests 
        # (usually 'beaker_test'). This is to avoid interfering with the schema 
        # that is already created and populated at the start of the test run.
        if not config.get('beaker.migration_test_dburi'):
            raise unittest.SkipTest('beaker.migration_test_dburi is not set')
        self.migration_engine = sqlalchemy.create_engine(
                config.get('beaker.migration_test_dburi'))
        self.migration_metadata = sqlalchemy.MetaData(bind=self.migration_engine)
        self.migration_session = create_session(bind=self.migration_engine)
        connection = self.migration_engine.connect()
        db_name = self.migration_engine.url.database
        connection.execute('DROP DATABASE IF EXISTS %s' % db_name)
        connection.execute('CREATE DATABASE %s' % db_name)
        connection.invalidate() # can't reuse this one

    def test_check_db(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        self.assertTrue(check_db(self.migration_metadata, '171c07fb4970'))
        self.assertFalse(check_db(self.migration_metadata, 'head'))
        upgrade_db(self.migration_metadata)
        self.assertTrue(check_db(self.migration_metadata, 'head'))

    def test_can_pass_beaker_version_to_downgrade(self):
        # We should be able to give it arbitrary Beaker versions and have it 
        # figure out the matching schema version we want.
        # The downgrade process itself will do nothing in this case because we 
        # are already on the right version.
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        downgrade_db(self.migration_metadata, '21')
        self.assertTrue(check_db(self.migration_metadata, '171c07fb4970'))
        # Should also accept minor versions
        downgrade_db(self.migration_metadata, '21.1')
        self.assertTrue(check_db(self.migration_metadata, '171c07fb4970'))
        # Should also accept RPM version-releases, this makes our playbooks simpler
        downgrade_db(self.migration_metadata, '21.1-1.el6eng')
        self.assertTrue(check_db(self.migration_metadata, '171c07fb4970'))

    def test_full_upgrade(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.11.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_full_downgrade_then_upgrade(self):
        # The point is to test that the complete *downgrade* sequence is valid, 
        # by then upgrading again and making sure we still have a correct schema.
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.11.sql'))
        upgrade_db(self.migration_metadata)
        downgrade_db(self.migration_metadata, 'base')
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_012(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.12.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_013(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.13.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_014(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.14.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_015(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.15.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_016(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.16.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_017(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.17.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_19(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/19.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_20(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/20.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_21(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_22(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/22.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_already_upgraded(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.17.sql'))
        upgrade_db(self.migration_metadata)
        # Upgrading an already-upgraded database should be a no-op.
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    # These schema dumps are derived from actual dumps from the Red Hat 
    # production Beaker instance at various points in time, which makes 
    # them a more realistic test case than the synthetically generated 
    # schemas used in the cases above.

    def test_redhat_production_20160120(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20160120.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20140820(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20140820.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20130304(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20130304.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20120216(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20120216.sql'))
        raise unittest.SkipTest('Database migrations are not implemented '
                'far enough into the past yet')
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def check_migrated_schema(self):
        """
        Compares the schema in the migrated db (self.migration_metadata) 
        against the fresh one which was populated for this test run (global TG 
        metadata).
        """
        self.migration_metadata.reflect()
        # The upgraded schema will not be *completely identical* to the fresh 
        # one. There are some exceptions because the migrations intentionally 
        # leave behind some structures to avoid destroying data in case the 
        # admin wants to downgrade later. So we have to account for those here.
        ignored_tables = [
            # may be left over from 22
            'response',
            'recipe_set_nacked',
            # may be left over from 19
            'system_group',
            # may be left over from 0.16
            'lab_controller_data_center',
        ]
        expected_tables = metadata.tables.keys()
        expected_tables.append('alembic_version') # it exists, just not in metadata
        actual_tables = self.migration_metadata.tables.keys()
        for ignored_table in ignored_tables:
            if ignored_table in actual_tables:
                actual_tables.remove(ignored_table)
        self.assertItemsEqual(expected_tables, actual_tables)
        for table_name in metadata.tables:
            expected_columns = metadata.tables[table_name].columns.keys()
            actual_columns = self.migration_metadata.tables[table_name].columns.keys()
            if table_name == 'command_queue':
                # may be left over from 22
                for col in ['callback', 'distro_tree_id', 'kernel_options']:
                    if col in actual_columns:
                        actual_columns.remove(col)
            if table_name == 'virt_resource':
                # may be left over from 0.16
                if 'system_name' in actual_columns:
                    actual_columns.remove('system_name')
                if 'mac_address' in actual_columns:
                    actual_columns.remove('mac_address')
            elif table_name == 'system':
                # may be left over from 0.15
                if 'private' in actual_columns:
                    actual_columns.remove('private')
                # may be left over from 0.14
                if 'shared' in actual_columns:
                    actual_columns.remove('shared')
            elif table_name == 'system_group':
                # may be left over from 0.14
                if 'admin' in actual_columns:
                    actual_columns.remove('admin')
            self.assertItemsEqual(expected_columns, actual_columns)
            for column_name in metadata.tables[table_name].columns.keys():
                self.assert_columns_equivalent(
                        metadata.tables[table_name].columns[column_name],
                        self.migration_metadata.tables[table_name].columns[column_name])
            expected_indexes = self.find_expected_indexes_for_table(
                    metadata.tables[table_name])
            actual_indexes = dict((index.name, [col.name for col in index.columns])
                    for index in self.migration_metadata.tables[table_name].indexes)
            if table_name == 'command_queue':
                # may be left over from 22
                actual_indexes = dict((name, cols) for name, cols
                        in actual_indexes.iteritems()
                        if cols != ['distro_tree_id'])
            if table_name == 'virt_resource':
                if 'ix_virt_resource_mac_address' in actual_indexes:
                    # may be left over from 0.16
                    del actual_indexes['ix_virt_resource_mac_address']
            # These may exist for unknown hysterical raisins (commit 520b4ddd)
            if table_name == 'log_recipe':
                if 'recipe_id_id' in actual_indexes:
                    del actual_indexes['recipe_id_id']
            if table_name == 'log_recipe_task':
                if 'recipe_task_id_id' in actual_indexes:
                    del actual_indexes['recipe_task_id_id']
            if table_name == 'log_recipe_task_result':
                if 'recipe_task_result_id_id' in actual_indexes:
                    del actual_indexes['recipe_task_result_id_id']
            # This was accidentally created in 0.7.1 upgrade (commit 75a9bea9) 
            # but it serves no purpose so we aren't adding it
            if table_name == 'task':
                if 'priority' in actual_indexes:
                    del actual_indexes['priority']
            # For now, we are ignoring differences in index names. That's 
            # because we have a lot of cases where the SA generated name is 
            # ix_<table>_<col> and that will appear in a fresh schema, but an 
            # older upgraded schema will have the MySQL generated name <col>.
            self.assertItemsEqual(expected_indexes.values(),
                    actual_indexes.values(),
                    'Incorrect indexes on %s' % table_name)
            expected_uniques = []
            for constraint in metadata.tables[table_name].constraints:
                if isinstance(constraint, (sqlalchemy.PrimaryKeyConstraint,
                        sqlalchemy.ForeignKeyConstraint)):
                    # PKs and FKs are checked below on individual columns
                    continue
                elif isinstance(constraint, sqlalchemy.CheckConstraint):
                    # SA generates CheckConstraints for ENUM columns but they 
                    # are not actually used in MySQL, so we ignore them
                    continue
                elif isinstance(constraint, sqlalchemy.UniqueConstraint):
                    expected_uniques.append([col.name for col in constraint.columns])
                else:
                    raise AssertionError('Need code to handle %r' % constraint)
            for index in metadata.tables[table_name].indexes:
                if index.unique:
                    expected_uniques.append([col.name for col in index.columns])
            actual_uniques = []
            # In MySQL, all unique constraints become unique indexes
            for index in self.migration_metadata.tables[table_name].indexes:
                if index.unique:
                    actual_uniques.append([col.name for col in index.columns])
            self.assertItemsEqual(expected_uniques, actual_uniques,
                    'Incorrect unique constraints on %s' % table_name)

    def find_expected_indexes_for_table(self, table):
        # This is not as easy as you might think (thanks MySQL...)
        expected_indexes = {}
        for index in table.indexes:
            expected_indexes[index.name] = [col.name for col in index.columns]
        # If we have defined a column with a unique constraint but it is not 
        # explicitly indexed (and is also not the first column in a primary 
        # key), then InnoDB will implicitly create an index on that column. 
        # So there will be some extra indexes which we never explicitly 
        # defined in Python land.
        for constraint in table.constraints:
            if isinstance(constraint, sqlalchemy.UniqueConstraint):
                cols = [col.name for col in constraint.columns]
                if any(has_initial_sublist(index_cols, cols)
                        for index_cols in expected_indexes.values()):
                    continue
                if has_initial_sublist(table.primary_key.columns.values(),
                        constraint.columns.values()):
                    continue
                name = constraint.name or constraint.columns.values()[0].name
                expected_indexes[name] = cols
        # Similarly, if we have defined a foreign key without an 
        # explicit index, InnoDB creates one implicitly.
        for fk in table.foreign_keys:
            if any(index_cols[0] == fk.parent.name
                    for index_cols in expected_indexes.values()):
                continue
            if table.primary_key.columns.values()[0] == fk.parent:
                continue
            expected_indexes[fk.name or fk.parent.name] = [fk.parent.name]
        return expected_indexes

    def assert_columns_equivalent(self, expected, actual):
        self.assertEquals(actual.name, expected.name)
        # actual.type is the dialect-specific type so it will not be identical 
        # to expected.type
        if isinstance(actual.type, sqlalchemy.dialects.mysql.TINYINT):
            self.assertTrue(isinstance(expected.type, sqlalchemy.Boolean),
                    'Actual type was TINYINT which is equivalent to Boolean, '
                    'but expected type was %r' % expected.type)
        else:
            self.assertTrue(actual.type._compare_type_affinity(expected.type),
                    'Actual type %r should be equivalent to expected type %r'
                    % (actual.type, expected.type))
        if hasattr(expected.type, 'length'):
            self.assertEquals(actual.type.length, expected.type.length,
                    '%r has wrong length' % actual)
        if hasattr(expected.type, 'enums'):
            self.assertItemsEqual(actual.type.enums, expected.type.enums)
        self.assertEquals(actual.nullable, expected.nullable,
                '%r should%s be nullable' % (actual,
                '' if expected.nullable else ' not'))
        self.assertEquals(actual.primary_key, expected.primary_key)
        if expected.server_default:
            self.assertEquals(actual.server_default, expected.server_default,
                    '%r has incorrect database default' % actual)
        else:
            if not actual.nullable and actual.server_default:
                # MySQL forces non-NULLable columns to have a default even if 
                # we don't want to specify one, so we just ignore those.
                default_text = str(actual.server_default.arg)
                if default_text not in ["''", "'0'", "0"]:
                    raise AssertionError('%r should not have database default %s'
                            % (actual, default_text))
            else:
                self.assertIsNone(actual.server_default,
                        '%r should not have a database default' % actual)
        actual_fk_targets = set(fk.target_fullname for fk in actual.foreign_keys)
        expected_fk_targets = set(fk.target_fullname for fk in expected.foreign_keys)
        self.assertItemsEqual(actual_fk_targets, expected_fk_targets,
                '%r has incorrect FK targets' % actual)

    def assert_indexes_equivalent(self, expected, actual):
        self.assertEquals(expected.name, actual.name)
        self.assertEquals([col.name for col in expected.columns],
                [col.name for col in actual.columns])
        self.assertEquals(expected.unique, actual.unique)

    def test_migrate_system_groups_to_pools(self):
        connection = self.migration_metadata.bind.connect()

        # create the DB schema for beaker 19
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                         'database-dumps/19.sql'))
        # populate synthetic data into relevant tables
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (1, "test.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (2, "test1.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (3, "test2.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
        connection.execute('INSERT INTO tg_group(group_id, group_name, ldap) VALUES (3, "group1", FALSE)')
        connection.execute('INSERT INTO tg_group(group_id, group_name, ldap) VALUES (4, "group2", FALSE)')
        connection.execute('INSERT INTO system_group(system_id, group_id) VALUES (1, 3)')
        connection.execute('INSERT INTO system_group(system_id, group_id) VALUES (2, 3)')
        connection.execute('INSERT INTO system_group(system_id, group_id) VALUES (1, 4)')
        connection.execute('INSERT INTO system_group(system_id, group_id) VALUES (3, 4)')

        # Migrate to system pools
        upgrade_db(self.migration_metadata)

        # check data for system_pool
        created_pools = self.migration_session.query(SystemPool).all()
        self.assertItemsEqual(['group1', 'group2'],
                          [pool.name for pool in created_pools])
        self.assertItemsEqual(['Pool migrated from group group1',
                               'Pool migrated from group group2'],
                              [pool.description for pool in created_pools])
        expected_system_pool_owners = {
            u'group1': u'group1',
            u'group2': u'group2',
        }
        for pool in expected_system_pool_owners.keys():
            p = self.migration_session.query(SystemPool).filter(SystemPool.name == pool).one()
            self.assertEquals(p.owning_group,
                              self.migration_session.query(Group).filter(Group.group_name == pool).one())

        expected_system_pools_map = {
            u'test.fqdn.name': [u'group1', u'group2'],
            u'test1.fqdn.name': [u'group1'],
            u'test2.fqdn.name': [u'group2'],
        }
        for system in expected_system_pools_map.keys():
            s = self.migration_session.query(System).filter(System.fqdn == system).one()
            self.assertItemsEqual([p.name for p in s.pools],
                                  expected_system_pools_map[system])

        min_user_id = min([user.id for user in self.migration_session.query(User).all()])
        for pool in created_pools:
            self.assertEquals(pool.activity[-1].action, u'Created')
            self.assertEquals(pool.activity[-1].field_name, u'Pool')
            self.assertEquals(pool.activity[-1].user.user_id, min_user_id)
            self.assertEquals(pool.activity[-1].new_value, pool.name)
            self.assertEquals(pool.activity[-1].service, u'Migration')

    def test_migrate_system_access_policies_to_custom_access_policies(self):
        connection = self.migration_metadata.bind.connect()

        # create the DB schema for beaker 19
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                         'database-dumps/19.sql'))
        # populate synthetic data into relevant tables
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (1, "test.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (2, "test1.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (3, "test2.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
        connection.execute('INSERT INTO system_access_policy(id, system_id) VALUES (1, 2)')
        connection.execute('INSERT INTO system_access_policy(id, system_id) VALUES (2, 1)')
        connection.execute('INSERT INTO system_access_policy(id, system_id) VALUES (3, 3)')

        # Migrate
        upgrade_db(self.migration_metadata)

        # check the data has been migrated successfully
        systems = self.migration_session.query(System).all()
        expected_system_policy_map = {
            'test.fqdn.name':2,
            'test1.fqdn.name':1,
            'test2.fqdn.name':3
        }
        for s in systems:
            self.assertEquals(s.custom_access_policy_id,
                              expected_system_policy_map[s.fqdn])
            self.assertEquals(s.active_access_policy_id,
                              expected_system_policy_map[s.fqdn])

        # downgrade test
        downgrade_db(self.migration_metadata, '1c444555ea3d')
        # XXX self.metadata.reflect() isn't for some reason detecting
        # the schema changes
        migration_metadata = sqlalchemy.MetaData(bind=self.migration_engine)
        migration_metadata.reflect()
        self.assertIn('system_id',
                      migration_metadata.tables['system_access_policy'].columns.keys())
        self.assertNotIn('system_access_policy_id',
                      migration_metadata.tables['system_pool'].columns.keys())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1198914
    def test_delete_orphaned_system_access_policies(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/20.sql'))
        # access policy 1 is referenced, access policy 2 is an orphan
        connection.execute("INSERT INTO system_access_policy (id) VALUES (1)")
        connection.execute("INSERT INTO system_access_policy_rule "
                "(policy_id, user_id, group_id, permission) "
                "VALUES (1, NULL, NULL, 'view')")
        connection.execute("INSERT INTO system "
                "(fqdn, date_added, owner_id, type, status, kernel_type_id, "
                " custom_access_policy_id, active_access_policy_id) "
                "VALUES ('test.example.invalid', '2015-01-01', 1, 1, 1, 1, 1, 1)")
        connection.execute("INSERT INTO system_access_policy (id) VALUES (2)")
        connection.execute("INSERT INTO system_access_policy_rule "
                "(policy_id, user_id, group_id, permission) "
                "VALUES (2, NULL, NULL, 'view')")
        # run migration
        upgrade_db(self.migration_metadata)
        # check that access policy 2 has been deleted
        self.assertEquals(
                self.migration_session.query(SystemAccessPolicy).filter_by(id=2).count(),
                0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1244996
    def test_delete_duplicate_osmajor_install_options(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/20.sql'))
        # RedHatEnterpriseLinux6 has duplicate rows in osmajor_install_options,
        # RedHatEnterpriseLinux7 just has one row
        connection.execute(
                "INSERT INTO osmajor (id, osmajor) "
                "VALUES (1, 'RedHatEnterpriseLinux6')")
        connection.execute(
                "INSERT INTO osmajor_install_options (osmajor_id, arch_id, ks_meta) "
                "VALUES (1, NULL, 'testone'), (1, NULL, 'testtwo')")
        connection.execute(
                "INSERT INTO osmajor (id, osmajor) "
                "VALUES (2, 'RedHatEnterpriseLinux7')")
        connection.execute(
                "INSERT INTO osmajor_install_options (osmajor_id, arch_id, ks_meta) "
                "VALUES (2, NULL, 'testthree')")
        # run migration
        upgrade_db(self.migration_metadata)
        # check that there is only one row per osmajor-arch combination
        row_counts = self.migration_session.query(OSMajorInstallOptions.osmajor_id,
                    OSMajorInstallOptions.arch_id, func.count())\
                .group_by(OSMajorInstallOptions.osmajor_id,
                    OSMajorInstallOptions.arch_id)
        for osmajor_id, arch_id, count in row_counts:
            self.assertEquals(count, 1,
                    'Expected to find only one row in osmajor_install_options '
                    'for osmajor_id %s, arch_id %s' % (osmajor_id, arch_id))
        # check that the most recent install options are kept, older ones are deleted
        installopts = self.migration_session.query(OSMajorInstallOptions)\
                .join(OSMajorInstallOptions.osmajor)\
                .filter(OSMajor.osmajor == u'RedHatEnterpriseLinux6',
                        OSMajorInstallOptions.arch == None)\
                .one()
        self.assertEquals(installopts.ks_meta, u'testtwo')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1257020
    def test_clear_removed_users_from_groups(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        # bob is in the colonel group
        connection.execute(
                "INSERT INTO tg_user (user_id, user_name, display_name, email_address, disabled, removed) "
                "VALUES (2, 'bob', 'Bob', 'bob@example.com', 1, '2015-12-01 15:43:28')")
        connection.execute(
                "INSERT INTO tg_group (group_id, group_name, display_name, ldap) "
                "VALUES (3, 'colonel', 'Colonel', 0)")
        connection.execute(
                "INSERT INTO user_group (user_id, group_id, is_owner) "
                "VALUES (2, 3, 1)")
        # run migration
        upgrade_db(self.migration_metadata)
        colonel = self.migration_session.query(Group).get(3)
        # check that bob is removed from the group
        bob = self.migration_session.query(User).get(2)
        self.assertNotIn(colonel, bob.groups)
        self.assertNotIn(bob, colonel.users)
        self.assertEqual(colonel.activity[0].field_name, u'User')
        self.assertEqual(colonel.activity[0].action, u'Removed')
        self.assertEqual(colonel.activity[0].old_value, u'bob')
        self.assertEqual(colonel.activity[0].service, u'Migration')
        self.assertEqual(colonel.activity[0].user.user_name, u'admin')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1257020
    def test_clear_removed_users_from_access_policies(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        # fred is in a custom access policy (1) and a pool access policy (2)
        connection.execute(
                "INSERT INTO tg_user (user_id, user_name, display_name, email_address, disabled, removed) "
                "VALUES (2, 'fred', 'Fred', 'fred@example.com', 1, '2015-12-01 17:18:56')")
        connection.execute("INSERT INTO system_access_policy (id) VALUES (1)")
        connection.execute(
                "INSERT INTO system_access_policy_rule (policy_id, user_id, group_id, permission) "
                "VALUES (1, 2, NULL, 'reserve')")
        connection.execute("INSERT INTO system "
                "(id, fqdn, date_added, owner_id, type, status, kernel_type_id, "
                " custom_access_policy_id, active_access_policy_id) "
                "VALUES (1, 'test.example.invalid', '2015-01-01', 1, 'Machine', 'Automated', 1, 1, 1)")
        connection.execute("INSERT INTO system_access_policy (id) VALUES (2)")
        connection.execute(
                "INSERT INTO system_access_policy_rule (policy_id, user_id, group_id, permission) "
                "VALUES (2, 2, NULL, 'loan_self')")
        connection.execute(
                "INSERT INTO system_pool (id, name, owning_user_id, access_policy_id) "
                "VALUES (1, 'colonel-hard-wear', 1, 2)")
        # run migration
        upgrade_db(self.migration_metadata)
        # check that fred is removed from the system access policy
        system = self.migration_session.query(System).get(1)
        self.assertEqual([], system.custom_access_policy.rules)
        self.assertEqual(system.activity[0].field_name, u'Access Policy Rule')
        self.assertEqual(system.activity[0].action, u'Removed')
        self.assertEqual(system.activity[0].old_value, u'<grant reserve to fred>')
        self.assertEqual(system.activity[0].service, u'Migration')
        self.assertEqual(system.activity[0].user.user_name, u'admin')
        # check that fred is removed from the pool access policy
        pool = self.migration_session.query(SystemPool).get(1)
        self.assertEqual([], pool.access_policy.rules)
        self.assertEqual(pool.activity[0].field_name, u'Access Policy Rule')
        self.assertEqual(pool.activity[0].action, u'Removed')
        self.assertEqual(pool.activity[0].old_value, u'<grant loan_self to fred>')
        self.assertEqual(pool.activity[0].service, u'Migration')
        self.assertEqual(pool.activity[0].user.user_name, u'admin')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_migrate_ldap_groups(self):
        group_name = u'my_ldap_group'
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        connection.execute(
                "INSERT INTO tg_group (group_name, ldap) "
                "VALUES ('%s', 1)" % group_name)
        # run migration
        upgrade_db(self.migration_metadata)
        # check that the group row was created
        group = self.migration_session.query(Group)\
                .filter(Group.group_name == group_name).one()
        self.assertEqual(group.group_name, group_name)
        self.assertEqual(group.membership_type, GroupMembershipType.ldap)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_clear_meaningless_system_activities(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/20.sql'))
        connection.execute('INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (1, "test.fqdn.name", "2015-12-15", 1, 1, 1, 1)')
        connection.execute("INSERT INTO activity "
                "(id, user_id, created, type, field_name, service, action, old_value, new_value) "
                "VALUES (1, NULL, '2015-12-15 01:11:56', 'system_activity', 'System Acess Policy', "
                "'HTTP', 'changed', 'Custom Access Policy', 'Custom access policy')")
        connection.execute("INSERT INTO system_activity (id, system_id) "
                "VALUES (1, 1)")
        # run migration
        upgrade_db(self.migration_metadata)
        # check that systtem activity and activity have been deleted
        self.assertEquals(
                self.migration_session.query(SystemActivity).filter_by(id=1).count(),
                0)

    def test_migrate_recipe_set_comments_and_waived_from_nacked(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        # job owned by admin, with a recipe set which has been nacked and commented
        connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, dirty_version, clean_version) "
                "VALUES (1, 1, '', '')")
        connection.execute(
                "INSERT INTO recipe_set (job_id, queue_time) "
                "VALUES (1, '2015-11-05 16:31:01')")
        connection.execute(
                "INSERT INTO recipe_set_nacked (recipe_set_id, response_id, comment, created) "
                "VALUES (1, 2, 'it broke', '2015-11-05 16:32:40')")
        # run migration
        upgrade_db(self.migration_metadata)
        # check that the comment row was created
        comments = self.migration_session.query(RecipeSetComment).all()
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].recipe_set_id, 1)
        self.assertEqual(comments[0].comment, u'it broke')
        self.assertEqual(comments[0].user.user_name, u'admin')
        self.assertEqual(comments[0].created, datetime.datetime(2015, 11, 5, 16, 32, 40))
        # check that the recipe set is waived
        recipeset = self.migration_session.query(RecipeSet).first()
        self.assertEqual(recipeset.waived, True)

    def test_migrate_recipe_reviewed_status_from_nacked(self):
        connection = self.migration_metadata.bind.connect()
        # populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/21.sql'))
        # job owned by admin, with a recipe set which has been acked
        connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, dirty_version, clean_version) "
                "VALUES (1, 1, '', '')")
        connection.execute(
                "INSERT INTO recipe_set (job_id, queue_time) "
                "VALUES (1, '2015-11-09 17:03:04')")
        connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, autopick_random) "
                "VALUES ('machine_recipe', 1, FALSE)")
        connection.execute(
                "INSERT INTO recipe_set_nacked (recipe_set_id, response_id, comment, created) "
                "VALUES (1, 1, NULL, '2015-11-09 17:32:03')")
        # run migration
        upgrade_db(self.migration_metadata)
        # check that the recipe is marked as reviewed by admin
        recipe = self.migration_session.query(Recipe).get(1)
        self.assertEqual(recipe.get_reviewed_state(User.by_user_name(u'admin')), True)

    # https://bugzilla.redhat.com/show_bug.cgi?id=991245
    def test_populate_installation_from_recipe_resource(self):
        connection = self.migration_metadata.bind.connect()
        # Populate empty database
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/22.sql'))
        # Populate test data for migration
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'bz991245-migration-setup.sql'))
        # Run migration
        upgrade_db(self.migration_metadata)
        # Check that installation has been populated for recipe 1 (system_resource)
        recipe = self.migration_session.query(Recipe).get(1)
        self.assertEqual(recipe.installation.distro_tree.distro.name, u'distro')
        self.assertEqual(recipe.installation.kernel_options, u'') # populated below
        self.assertEqual(recipe.installation.rendered_kickstart.kickstart, u'lol')
        self.assertEqual(recipe.installation.system.fqdn, u'test.fqdn.name')
        self.assertEqual(recipe.installation.rebooted,
                datetime.datetime(2016, 2, 16, 1, 0, 5))
        self.assertEqual(recipe.installation.install_started,
                datetime.datetime(2016, 2, 16, 1, 1, 0))
        self.assertEqual(recipe.installation.install_finished,
                datetime.datetime(2016, 2, 16, 1, 20, 0))
        self.assertEqual(recipe.installation.postinstall_finished,
                datetime.datetime(2016, 2, 16, 1, 21, 0))
        self.assertEqual(recipe.installation.created,
                datetime.datetime(2016, 2, 16, 1, 0, 0))
        self.migration_session.close()
        # Run online data migration
        run_online_data_migration(self.migration_metadata, 'commands-for-recipe-installations')
        # Check that commands have been associated with their installation
        recipe = self.migration_session.query(Recipe).get(1)
        self.assertEqual(recipe.installation.kernel_options, u'ks=lol')
        installation_cmd = self.migration_session.query(CommandActivity).get(1)
        self.assertEqual(installation_cmd.installation, recipe.installation)
        manual_cmd = self.migration_session.query(CommandActivity).get(2)
        self.assertEqual(manual_cmd.installation, None)
        reprovision_cmd = self.migration_session.query(CommandActivity).get(3)
        self.assertEqual(reprovision_cmd.installation, None)
        # Check that installation has been populated for recipe 2 (guest_resource)
        recipe = self.migration_session.query(Recipe).get(2)
        self.assertEqual(recipe.installation.distro_tree.distro.name, u'distro')
        self.assertEqual(recipe.installation.kernel_options, u'')
        self.assertEqual(recipe.installation.rendered_kickstart.kickstart, u'lol2')
        self.assertIsNone(recipe.installation.system)
        self.assertIsNone(recipe.installation.rebooted)
        self.assertEqual(recipe.installation.install_started,
                datetime.datetime(2016, 2, 16, 1, 31, 0))
        self.assertEqual(recipe.installation.install_finished,
                datetime.datetime(2016, 2, 16, 1, 40, 0))
        self.assertEqual(recipe.installation.postinstall_finished,
                datetime.datetime(2016, 2, 16, 1, 41, 0))
        self.assertEqual(recipe.installation.created,
                datetime.datetime(2016, 2, 16, 1, 0, 0))
        # Check that installation has been populated for recipes 3 and 4
        # (host and guest that never started)
        recipe = self.migration_session.query(Recipe).get(3)
        self.assertEqual(recipe.installation.created,
                datetime.datetime(2016, 2, 17, 0, 0, 0))
        recipe = self.migration_session.query(Recipe).get(4)
        self.assertEqual(recipe.installation.created,
                datetime.datetime(2016, 2, 17, 0, 0, 0))
