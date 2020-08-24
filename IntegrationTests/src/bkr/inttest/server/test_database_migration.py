# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import collections
import datetime
import unittest
import pkg_resources
import sqlalchemy
from turbogears import config
from turbogears.database import metadata
from bkr.common import __version__
from bkr.server.tools.init import upgrade_db, downgrade_db, check_db, doit, init_db
from sqlalchemy import UnicodeText
from sqlalchemy.orm import create_session
from sqlalchemy.sql import func
from bkr.server.model import (
    SystemPool, System, SystemAccessPolicy, Group, User, OSMajor, OSMajorInstallOptions,
    GroupMembershipType, SystemActivity, Activity, RecipeSetComment, Recipe, RecipeSet,
    RecipeTaskResult, Command, CommandStatus, LogRecipeTaskResult, DataMigration, Job,
    SystemSchedulerStatus, Permission, Installation, Arch
)


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
        with self.migration_engine.connect() as connection:
            db_name = self.migration_engine.url.database
            connection.execute('DROP DATABASE IF EXISTS %s' % db_name)
            connection.execute('CREATE DATABASE %s' % db_name)
            connection.invalidate()  # can't reuse this one

    def tearDown(self):
        # If this assertion fails, it means the previous test (or some code
        # called during the test) leaked a database connection. This can cause
        # deadlocks with other tests in case the leaked connection was holding
        # an open transaction, which is why we force it to be 0.
        # https://bugzilla.redhat.com/show_bug.cgi?id=1356852
        self.assertEquals(self.migration_engine.pool.checkedout(), 0)

    def test_check_db(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/21.sql'))
        self.assertTrue(check_db(self.migration_metadata, '171c07fb4970'))
        self.assertFalse(check_db(self.migration_metadata, 'head'))
        upgrade_db(self.migration_metadata)
        self.assertTrue(check_db(self.migration_metadata, 'head'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1350302
    def test_empty_check_and_create(self):
        EmptyOpt = collections.namedtuple('EmtpyOpt',
                                          ['user_name',
                                           'password',
                                           'display_name',
                                           'email_address',
                                           'check',
                                           'downgrade'])

        opts = EmptyOpt._make(['empty', 'empty', 'Empty DB Test', 'empty@example.com', True, False])
        doit(opts, self.migration_metadata)
        try:
            doit(opts._replace(check=False), self.migration_metadata)
        except sqlalchemy.exc.NoSuchTableError:
            # Without the fix in doit() for bug 1350302, an exception will be thrown
            self.fail(
                "doit() raised NoSuchTableError, tried to update a non-existent database schema")

    def test_can_pass_beaker_version_to_downgrade(self):
        # We should be able to give it arbitrary Beaker versions and have it
        # figure out the matching schema version we want.
        # The downgrade process itself will do nothing in this case because we
        # are already on the right version.
        with self.migration_engine.connect() as connection:
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

    def test_can_downgrade_to_current_version(self):
        # Downgrading to the current version should just be a no-op.
        # The purpose of this to test is actually to make sure that beaker-init
        # knows about the version number. If this test fails, it means we have
        # tagged a new release but we forgot to record the schema version in
        # the table that lives in beaker-init (and in the docs).
        # It will also ensure that we have remembered to add a corresponding
        # schema dump to the tests here.
        #
        # There is an added wrinkle. During the normal development cycle, on
        # the develop branch our version will look like this:
        #   26.0.git.82.3ffb9167e
        # In this case, the database schema is not yet frozen and we do not
        # expect to be able to downgrade to version 26 yet. Once a release
        # candidate is tagged and the version becomes:
        #   26.0rc1
        # or on a maintenance branch like release-26, where the version is:
        #   26.1.git.9.3ffb9167e
        # the schema should be frozen and we should be able to downgrade to it.
        # Therefore this test will check either the current major version or
        # the previous major version based on the above conditions.
        major, minor = __version__.split('.')[:2]
        if minor == '0' and 'git' in __version__:
            # schema is not frozen yet, test the previous major version
            major_version_to_test = str(int(major) - 1)
        else:
            # schema should be frozen now
            major_version_to_test = major
        dump_filename = 'database-dumps/%s.sql' % major_version_to_test
        if not pkg_resources.resource_exists('bkr.inttest.server', dump_filename):
            raise AssertionError('Schema dump for version %s not found '
                                 'in IntegrationTests/src/bkr/inttest/server/database-dumps'
                                 % major_version_to_test)
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string(
                'bkr.inttest.server', dump_filename))
        downgrade_db(self.migration_metadata, major_version_to_test)
        self.check_migrated_schema()

    def test_full_upgrade(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.11.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_full_downgrade_then_upgrade(self):
        # The point is to test that the complete *downgrade* sequence is valid,
        # by then upgrading again and making sure we still have a correct schema.
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.11.sql'))
        upgrade_db(self.migration_metadata)
        downgrade_db(self.migration_metadata, 'base')
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_012(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.12.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_013(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.13.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_014(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.14.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_015(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.15.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_016(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.16.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_017(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/0.17.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_19(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/19.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_20(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/20.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_21(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/21.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_22(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/22.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_23(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/23.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_24(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/24.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_25(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/25.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_26(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/26.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_27(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/27.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_already_upgraded(self):
        with self.migration_engine.connect() as connection:
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
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/redhat-production-20160120.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20140820(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/redhat-production-20140820.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20130304(self):
        with self.migration_engine.connect() as connection:
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/redhat-production-20130304.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20120216(self):
        with self.migration_metadata.bind.connect() as connection:
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
            # may be left over from 23
            'external_reports',
            # may be left over from 22
            'response',
            'recipe_set_nacked',
            # may be left over from 19
            'system_group',
            # may be left over from 0.16
            'lab_controller_data_center',
        ]
        expected_tables = metadata.tables.keys()
        expected_tables.append('alembic_version')  # it exists, just not in metadata
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

        if hasattr(expected.type, 'length') and not isinstance(expected.type, UnicodeText):
            self.assertEquals(actual.type.length, expected.type.length,
                              '%r has wrong length' % actual)
        if hasattr(expected.type, 'precision'):
            self.assertEquals(actual.type.precision, expected.type.precision,
                              '%r has wrong numeric precision' % actual)
        if hasattr(expected.type, 'scale'):
            self.assertEquals(actual.type.scale, expected.type.scale,
                              '%r has wrong numeric scale' % actual)
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
        with self.migration_metadata.bind.connect() as connection:
            # create the DB schema for beaker 19
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/19.sql'))
            # populate synthetic data into relevant tables
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (1, "test.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (2, "test1.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (3, "test2.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
            connection.execute(
                'INSERT INTO tg_group(group_id, group_name, ldap) VALUES (3, "group1", FALSE)')
            connection.execute(
                'INSERT INTO tg_group(group_id, group_name, ldap) VALUES (4, "group2", FALSE)')
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
                              self.migration_session.query(Group).filter(
                                  Group.group_name == pool).one())

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
        with self.migration_metadata.bind.connect() as connection:
            # create the DB schema for beaker 19
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/19.sql'))
            # populate synthetic data into relevant tables
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (1, "test.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (2, "test1.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (3, "test2.fqdn.name", "2015-01-01", 1, 1, 1, 1)')
            connection.execute('INSERT INTO system_access_policy(id, system_id) VALUES (1, 2)')
            connection.execute('INSERT INTO system_access_policy(id, system_id) VALUES (2, 1)')
            connection.execute('INSERT INTO system_access_policy(id, system_id) VALUES (3, 3)')

        # Migrate
        upgrade_db(self.migration_metadata)

        # check the data has been migrated successfully
        systems = self.migration_session.query(System).all()
        expected_system_policy_map = {
            'test.fqdn.name': 2,
            'test1.fqdn.name': 1,
            'test2.fqdn.name': 3
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
        with self.migration_metadata.bind.connect() as connection:
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
        with self.migration_metadata.bind.connect() as connection:
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
                                                  OSMajorInstallOptions.arch_id, func.count()) \
            .group_by(OSMajorInstallOptions.osmajor_id,
                      OSMajorInstallOptions.arch_id)
        for osmajor_id, arch_id, count in row_counts:
            self.assertEquals(count, 1,
                              'Expected to find only one row in osmajor_install_options '
                              'for osmajor_id %s, arch_id %s' % (osmajor_id, arch_id))
        # check that the most recent install options are kept, older ones are deleted
        installopts = self.migration_session.query(OSMajorInstallOptions) \
            .join(OSMajorInstallOptions.osmajor) \
            .filter(OSMajor.osmajor == u'RedHatEnterpriseLinux6',
                    OSMajorInstallOptions.arch == None) \
            .one()
        self.assertEquals(installopts.ks_meta, u'testtwo')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1257020
    def test_clear_removed_users_from_groups(self):
        with self.migration_metadata.bind.connect() as connection:
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
        with self.migration_metadata.bind.connect() as connection:
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
        with self.migration_metadata.bind.connect() as connection:
            # populate empty database
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/21.sql'))
            connection.execute(
                "INSERT INTO tg_group (group_name, ldap) "
                "VALUES ('%s', 1)" % group_name)
        # run migration
        upgrade_db(self.migration_metadata)
        # check that the group row was created
        group = self.migration_session.query(Group) \
            .filter(Group.group_name == group_name).one()
        self.assertEqual(group.group_name, group_name)
        self.assertEqual(group.membership_type, GroupMembershipType.ldap)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_clear_meaningless_system_activities(self):
        with self.migration_metadata.bind.connect() as connection:
            # populate empty database
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/20.sql'))
            connection.execute(
                'INSERT INTO system(id, fqdn, date_added, owner_id, type, status, kernel_type_id) VALUES (1, "test.fqdn.name", "2015-12-15", 1, 1, 1, 1)')
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
        with self.migration_metadata.bind.connect() as connection:
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
        with self.migration_metadata.bind.connect() as connection:
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
        with self.migration_metadata.bind.connect() as connection:
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
        self.assertEqual(recipe.installation.kernel_options, u'')  # populated below
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
        # Run online data migration (two batches)
        migration = DataMigration(name=u'commands-for-recipe-installations')
        finished = migration.migrate_one_batch(self.migration_metadata.bind)
        self.assertFalse(finished)
        finished = migration.migrate_one_batch(self.migration_metadata.bind)
        self.assertTrue(finished)
        # Check that commands have been associated with their installation
        recipe = self.migration_session.query(Recipe).get(1)
        self.assertEqual(recipe.installation.kernel_options, u'ks=lol')
        installation_cmd = self.migration_session.query(Command).get(1)
        self.assertEqual(installation_cmd.installation, recipe.installation)
        manual_cmd = self.migration_session.query(Command).get(2)
        self.assertEqual(manual_cmd.installation, None)
        reprovision_cmd = self.migration_session.query(Command).get(3)
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1322700
    # https://bugzilla.redhat.com/show_bug.cgi?id=1337790
    def test_delete_recipe_task_results_for_deleted_job(self):
        with self.migration_metadata.bind.connect() as connection:
            # populate empty database
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/22.sql'))
            # populate test jobs
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'bz1322700-and-bz1337790-migration-setup.sql'))
        # run migration
        upgrade_db(self.migration_metadata)
        # Job one's recipe task results should not be deleted
        self.assertEquals(
            self.migration_session.query(RecipeTaskResult).filter_by(recipe_task_id=1).count(),
            1)
        # Job one's log recipe task results should not be deleted
        self.assertEquals(
            self.migration_session.query(LogRecipeTaskResult).filter_by(
                recipe_task_result_id=1).count(),
            1)
        # Job two's recipe task results should be deleted
        self.assertEquals(
            self.migration_session.query(RecipeTaskResult).filter_by(recipe_task_id=2).count(),
            0)
        # Job two's log recipe task results should be deleted
        self.assertEquals(
            self.migration_session.query(LogRecipeTaskResult).filter_by(
                recipe_task_result_id=2).count(),
            0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1346586
    def test_Installing_status_is_mapped_on_downgrade(self):
        with self.migration_metadata.bind.connect() as connection:
            # populate empty database
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/22.sql'))
            upgrade_db(self.migration_metadata)
            # create a job in Installing state
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, is_dirty, status) "
                "VALUES (1, 1, FALSE, 'Installing')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, queue_time, waived, status) "
                "VALUES (1, '2015-11-09 17:03:04', FALSE, 'Installing')")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, autopick_random, status) "
                "VALUES ('machine_recipe', 1, FALSE, 'Installing')")
        # run the downgrade
        downgrade_db(self.migration_metadata, '22')
        # status should be Running so that it works with 22.x
        with self.migration_metadata.bind.connect() as connection:
            self.assertEquals(
                connection.scalar('SELECT status FROM job WHERE id = 1'),
                u'Running')
            self.assertEquals(
                connection.scalar('SELECT status FROM recipe_set WHERE id = 1'),
                u'Running')
            self.assertEquals(
                connection.scalar('SELECT status FROM recipe WHERE id = 1'),
                u'Running')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1318524
    def test_command_queue_separated_from_activity(self):
        with self.migration_metadata.bind.connect() as connection:
            # populate empty database
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/23.sql'))
            # set up a test command
            connection.execute(
                "INSERT INTO system (id, fqdn, date_added, owner_id, type, status, kernel_type_id) "
                "VALUES (1, 'example.invalid', '2016-01-01 00:00:00', 1, 'Machine', 'Manual', 1)")
            connection.execute(
                "INSERT INTO activity (id, user_id, created, type, field_name, "
                "   service, action, old_value, new_value) "
                "VALUES (1, 1, '2016-08-11 16:47:56', 'command_activity', 'Command', "
                "   'Scheduler', 'on', '', "
                "   'ValueError: Power script /usr/lib/python2.7/site-packages/bk')")
            connection.execute(
                "INSERT INTO command_queue (id, system_id, status, updated, quiescent_period) "
                "VALUES (1, 1, 'Failed', '2016-08-11 16:47:56', 5)")
            # add an unrelated system activity (id 2 will conflict with the new command below)
            connection.execute(
                "INSERT INTO activity (id, user_id, created, type, field_name, "
                "   service, action, old_value, new_value) "
                "VALUES (2, 1, '2016-08-31 00:00:00', 'system_activity', 'Loaned', "
                "   'HTTP', 'Changed', 'bob', 'fred')")
            connection.execute(
                "INSERT INTO system_activity (id, system_id) VALUES (2, 1)")
        # run migration
        upgrade_db(self.migration_metadata)
        # command should be correctly populated
        cmd = self.migration_session.query(Command).get(1)
        self.assertEquals(cmd.user_id, 1)
        self.assertEquals(cmd.service, u'Scheduler')
        self.assertEquals(cmd.system_id, 1)
        self.assertEquals(cmd.queue_time, datetime.datetime(2016, 8, 11, 16, 47, 56))
        self.assertEquals(cmd.action, u'on')
        self.assertEquals(cmd.quiescent_period, 5)
        self.assertEquals(cmd.delay_until, None)
        self.assertEquals(cmd.status, CommandStatus.failed)
        self.assertEquals(cmd.error_message,
                          u'ValueError: Power script /usr/lib/python2.7/site-packages/bk')
        # old activity row should be gone
        self.assertIsNone(self.migration_session.query(Activity).filter_by(id=1).first())
        # insert a new command after upgrade, as if Beaker has been running for a while
        # (the downgrade has to cope with this properly:
        # https://bugzilla.redhat.com/show_bug.cgi?id=1376650)
        with self.migration_session.begin():
            new_command = Command(user_id=1, service=u'testdata', system_id=1,
                                  action=u'off', status=CommandStatus.running,
                                  quiescent_period=3,
                                  queue_time=datetime.datetime(2016, 9, 19, 11, 54, 7),
                                  start_time=datetime.datetime(2016, 9, 19, 11, 54, 27))
            self.migration_session.add(new_command)
            self.migration_session.flush()
            self.assertEquals(new_command.id, 2)
        # downgrade back to 23
        downgrade_db(self.migration_metadata, '23')
        # old activity and command_queue should be correctly populated
        with self.migration_metadata.bind.connect() as connection:
            activity_rows = connection.execute('SELECT * FROM activity ORDER BY id').fetchall()
            self.assertEquals(len(activity_rows), 3)
            self.assertEquals(activity_rows[0].id, 1)
            self.assertEquals(activity_rows[0].user_id, 1)
            self.assertEquals(activity_rows[0].created,
                              datetime.datetime(2016, 8, 11, 16, 47, 56))
            self.assertEquals(activity_rows[0].type, u'command_activity')
            self.assertEquals(activity_rows[0].field_name, u'Command')
            self.assertEquals(activity_rows[0].service, u'Scheduler')
            self.assertEquals(activity_rows[0].action, u'on')
            self.assertEquals(activity_rows[0].old_value, u'')
            self.assertEquals(activity_rows[0].new_value,
                              u'ValueError: Power script /usr/lib/python2.7/site-packages/bk')
            self.assertEquals(activity_rows[2].id, 3)
            self.assertEquals(activity_rows[2].user_id, 1)
            self.assertEquals(activity_rows[2].created,
                              datetime.datetime(2016, 9, 19, 11, 54, 7))
            self.assertEquals(activity_rows[2].type, u'command_activity')
            self.assertEquals(activity_rows[2].field_name, u'Command')
            self.assertEquals(activity_rows[2].service, u'testdata')
            self.assertEquals(activity_rows[2].action, u'off')
            self.assertEquals(activity_rows[2].old_value, u'')
            self.assertEquals(activity_rows[2].new_value, u'')
            command_rows = connection.execute('SELECT * FROM command_queue ORDER BY id').fetchall()
            self.assertEquals(len(command_rows), 2)
            self.assertEquals(command_rows[0].id, 1)
            self.assertEquals(command_rows[0].system_id, 1)
            self.assertEquals(command_rows[0].status, u'Failed')
            self.assertEquals(command_rows[0].delay_until, None)
            self.assertEquals(command_rows[0].quiescent_period, 5)
            self.assertEquals(command_rows[0].updated,
                              datetime.datetime(2016, 8, 11, 16, 47, 56))
            self.assertEquals(command_rows[0].installation_id, None)
            self.assertEquals(command_rows[1].id, 3)  # not 2, due to renumbering
            self.assertEquals(command_rows[1].system_id, 1)
            self.assertEquals(command_rows[1].status, u'Running')
            self.assertEquals(command_rows[1].delay_until, None)
            self.assertEquals(command_rows[1].quiescent_period, 3)
            self.assertEquals(command_rows[1].updated,
                              datetime.datetime(2016, 9, 19, 11, 54, 7))
            self.assertEquals(command_rows[1].installation_id, None)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_email_prefs_set_for_current_users(self):
        with self.migration_metadata.bind.connect() as connection:
            # create the DB schema for beaker 23
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/23.sql'))

            # insert synthetic data into tg_user
            connection.execute(
                "INSERT INTO tg_user (user_id, user_name, display_name, email_address, disabled, removed, use_old_job_page) "
                "VALUES (2, 'bob', 'Bob', 'bob@example.com', 1, '2015-12-01 15:43:28', 0)")

        # run migration
        upgrade_db(self.migration_metadata)
        # check notifications have been set for bob
        user = self.migration_session.query(User).all()

        self.assertEquals(user[1].user_name, u'bob')

        self.assertEquals(user[1].notify_job_completion, True)
        self.assertEquals(user[1].notify_broken_system, True)
        self.assertEquals(user[1].notify_group_membership, True)
        self.assertEquals(user[1].notify_reservesys, True)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1100593
    def test_reserve_condition_is_set_to_always_for_existing_rows(self):
        with self.migration_metadata.bind.connect() as connection:
            # create the DB schema for beaker 23
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/23.sql'))
            # existing job with a reservation request
            connection.execute(
                "INSERT INTO job (id, owner_id, retention_tag_id, dirty_version, clean_version) "
                "VALUES (1, 1, 1, '', '')")
            connection.execute(
                "INSERT INTO recipe_set (id, job_id, queue_time, waived) "
                "VALUES (1, 1, '2016-10-19 01:09:36', FALSE)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, autopick_random) "
                "VALUES (1, 'machine_recipe', 1, FALSE)")
            connection.execute(
                "INSERT INTO recipe_reservation (id, recipe_id, duration) "
                "VALUES (1, 1, 300)")
        # run migration
        upgrade_db(self.migration_metadata)
        # condition should be set to 'always' by default
        with self.migration_metadata.bind.connect() as connection:
            self.assertEquals(
                connection.scalar('SELECT `when` FROM recipe_reservation WHERE id = 1'),
                u'always')

    def test_remove_task_arch_and_osmajor_exclude_orphans_duplicates(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/23.sql'))
            # The idea to test all the combinations of orphans
            # that either side of arch, task, osmajor is NULL hence orphaned.
            # as well as duplicates.
            # uses the arch for ppc64
            connection.execute(
                "INSERT INTO task (id, name, rpm, path, valid, description, avg_time, "
                "creation_date, update_date, owner, version, license) "
                "VALUES (1, 'task1', 'rpm1', '/task1', 1, 'task1', 1, "
                "'2017-12-13 00:00:00', '2017-12-13 00:00:00', 'owner1', '1.1-1', 'GPLv99+')")
            connection.execute("INSERT INTO osmajor(id, osmajor) VALUES (1, 'redhat loonix');")
            connection.execute("INSERT INTO task_exclude_arch(task_id, arch_id)"
                               "VALUES (1, 5), (NULL, 5), (1, NULL), (1, 5);")
            connection.execute("INSERT INTO task_exclude_osmajor(task_id, osmajor_id)"
                               "VALUES (1, 1), (NULL, 1), (1, NULL), (1, 1);")

        upgrade_db(self.migration_metadata)

        with self.migration_metadata.bind.connect() as connection:
            # we test the case of orphaned on both sides, non-orphaned preserved
            # and duplicates removed
            self.assertEqual(connection.scalar(
                'SELECT count(*) FROM task_exclude_osmajor'), 1)
            self.assertEqual(connection.scalar(
                'SELECT count(*) FROM task_exclude_arch'), 1)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1362371
    def test_abort_commands_without_lab_controller(self):
        with self.migration_metadata.bind.connect() as connection:
            # populate empty database
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'database-dumps/23.sql'))
            connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                                                             'bz1362371-migration-setup.sql'))

        upgrade_db(self.migration_metadata)

        self.assertEquals(
            self.migration_session.query(Command).filter_by(system_id=1).count(),
            4)

        # Failed Command left in place
        self.assertEquals(
            self.migration_session.query(Command).filter_by(status=CommandStatus.aborted,
                                                            system_id=2).count(),
            4)

        # Failed Command left in place
        self.assertEquals(
            self.migration_session.query(Command).filter_by(status=CommandStatus.failed,
                                                            system_id=2).count(),
            1)

        cmd = self.migration_session.query(Command).get(9)
        self.assertEquals(cmd.status, CommandStatus.failed)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1404054
    def test_marks_all_migrations_as_finished_on_fresh_db(self):
        init_db(self.migration_metadata)
        with self.migration_session.begin():
            for name in DataMigration.all_names():
                migration = self.migration_session.query(DataMigration) \
                    .filter(DataMigration.name == name).one()
                self.assertEquals(migration.is_finished, True)

    def test_values_are_preserved_after_migration(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            # inserting data into openstack_region requires a lab controller
            connection.execute("INSERT INTO lab_controller(id, fqdn, disabled, user_id) "
                               "VALUES(1, 'lab.controller', 0, 1);")
            connection.execute(
                "INSERT INTO openstack_region (lab_controller_id, ipxe_image_id) VALUES "
                "(1, 'deadbeef-dead-beef-dead-beefdeadbeef');")

        upgrade_db(self.migration_metadata)

        # check ipxe_image_id binary value after upgrade
        with self.migration_metadata.bind.connect() as connection:
            self.assertEquals(connection.scalar('SELECT ipxe_image_id FROM openstack_region '
                                                'WHERE lab_controller_id = 1'),
                              '\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef')

        downgrade_db(self.migration_metadata, 'f18df089261')

        # check ipxe_image_id varchar value after downgrade
        with self.migration_metadata.bind.connect() as connection:
            self.assertEquals(connection.scalar('SELECT ipxe_image_id FROM openstack_region '
                                                'WHERE lab_controller_id = 1'),
                              u'deadbeef-dead-beef-dead-beefdeadbeef')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337789
    def test_purged_jobs_are_also_deleted(self):
        # The new invariant is that a job is always deleted *before* it is
        # purged (not one or the other) so any existing purged jobs must also
        # be marked as deleted.
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, dirty_version, clean_version, deleted) "
                "VALUES (1, 1, '', '', '2017-07-27 14:28:20')")
        upgrade_db(self.migration_metadata)
        job = self.migration_session.query(Job).get(1)
        self.assertEquals(job.purged, datetime.datetime(2017, 7, 27, 14, 28, 20))
        self.assertEquals(job.deleted, datetime.datetime(2017, 7, 27, 14, 28, 20))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337789
    def test_deleted_jobs_with_logs_are_not_purged(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            # We have a job which beaker-log-delete claims to have purged the
            # logs for (deleted timestamp is set) but there are actually still
            # logs left in it.
            # Note that we are setting the 'deleted' column here which becomes
            # 'purged' after the migration.
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, dirty_version, clean_version, deleted) "
                "VALUES (1, 1, '', '', '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, queue_time, waived) "
                "VALUES (1, '2015-11-09 17:03:04', 0)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, autopick_random) "
                "VALUES ('machine_recipe', 1, FALSE)")
            connection.execute(
                "INSERT INTO log_recipe (recipe_id, filename) "
                "VALUES (1, 'console.log')")
        # Do the schema upgrades
        upgrade_db(self.migration_metadata)
        # Do the data migration
        migration = DataMigration(name=u're-purge-old-jobs-with-logs')
        finished = migration.migrate_one_batch(self.migration_metadata.bind)
        self.assertTrue(finished)
        # Job should be deleted, but not purged, so that beaker-log-delete will purge it again
        job = self.migration_session.query(Job).get(1)
        self.assertEquals(job.purged, None)
        self.assertEquals(job.deleted, datetime.datetime(2017, 7, 27, 14, 28, 20))

    # https://bugzilla.redhat.com/show_bug.cgi?id=800455
    def test_downgrading_task_exclusive_osmajors_converts_to_excluded_osmajors(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            connection.execute("INSERT INTO osmajor (osmajor) "
                               "VALUES ('Fedora26'), ('Fedora27'), ('CentOS7')")
        # Upgrade to 25
        upgrade_db(self.migration_metadata)
        # We have a task which is exclusive to Fedora26
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                "INSERT INTO task (id, name, rpm, path, valid, description, avg_time, "
                "creation_date, update_date, owner, version, license) "
                "VALUES (1, '/a', 'a.rpm', '/a', 1, 'task1', 1, "
                "'2017-12-13 00:00:00', '2017-12-13 00:00:00', 'owner1', '1.1-1', 'GPLv99+')")
            connection.execute(
                "INSERT INTO task_exclusive_osmajor (task_id, osmajor_id) VALUES (1, 1)")
        # Downgrade back to 24
        downgrade_db(self.migration_metadata, '24')
        # Now the task should have excluded all other releases
        with self.migration_metadata.bind.connect() as connection:
            osmajor_ids = connection.execute(
                'SELECT osmajor_id FROM task_exclude_osmajor WHERE task_id = 1').fetchall()
            self.assertItemsEqual(osmajor_ids, [(2,), (3,)])

    def test_downgrading_task_exclusive_arches_converts_to_excluded_arches(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
        # Upgrade to 25
        upgrade_db(self.migration_metadata)
        # We have a task which is exclusive to s390(x)
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                "INSERT INTO task (id, name, rpm, path, valid, description, avg_time, "
                "creation_date, update_date, owner, version, license) "
                "VALUES (1, '/a', 'a.rpm', '/a', 1, 'task1', 1, "
                "'2017-12-13 00:00:00', '2017-12-13 00:00:00', 'owner1', '1.1-1', 'GPLv99+')")
            connection.execute("INSERT INTO task_exclusive_arch (task_id, arch_id) "
                               "SELECT 1, arch.id FROM arch WHERE arch.arch IN ('s390', 's390x')")
        # Downgrade back to 24
        downgrade_db(self.migration_metadata, '24')
        # Now the task should have excluded all other arches
        with self.migration_metadata.bind.connect() as connection:
            arches = connection.execute(
                'SELECT arch.arch FROM task_exclude_arch '
                'INNER JOIN arch ON task_exclude_arch.arch_id = arch.id '
                'WHERE task_id = 1').fetchall()
            self.assertItemsEqual(arches,
                                  [('aarch64',), ('arm',), ('armhfp',), ('i386',), ('ia64',),
                                   ('ppc',), ('ppc64',), ('ppc64le',), ('x86_64',)])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1519589
    def test_system_scheduler_status(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            # System 1 is removed
            connection.execute(
                "INSERT INTO system (id, fqdn, date_added, owner_id, type, status, kernel_type_id) "
                "VALUES (1, 'removed.example.com', '2017-12-06', 1, 'Machine', 'Removed', 1)")
            # System 2 is idle with Automated status
            connection.execute(
                "INSERT INTO system (id, fqdn, date_added, owner_id, type, status, kernel_type_id) "
                "VALUES (2, 'automated.example.com', '2017-12-06', 1, 'Machine', 'Automated', 1)")
            # System 3 is idle with Manual status
            connection.execute(
                "INSERT INTO system (id, fqdn, date_added, owner_id, type, status, kernel_type_id) "
                "VALUES (3, 'manual.example.com', '2017-12-06', 1, 'Machine', 'Manual', 1)")
            # System 4 is idle with Broken status
            connection.execute(
                "INSERT INTO system (id, fqdn, date_added, owner_id, type, status, kernel_type_id) "
                "VALUES (4, 'broken.example.com', '2017-12-06', 1, 'Machine', 'Broken', 1)")
            # System 5 is reserved by the scheduler
            connection.execute(
                "INSERT INTO system (id, fqdn, date_added, owner_id, type, status, kernel_type_id, user_id) "
                "VALUES (5, 'reserved.example.com', '2017-12-06', 1, 'Machine', 'Automated', 1, 1)")
            connection.execute(
                "INSERT INTO reservation (id, system_id, user_id, start_time, type) "
                "VALUES (1, 5, 1, '2017-12-06 00:00:00', 'recipe')")
        # Do the schema upgrades
        upgrade_db(self.migration_metadata)
        # Job should be deleted, but not purged, so that beaker-log-delete will purge it again
        systems = self.migration_session.query(System).order_by(System.id).all()
        # Removed system should be 'idle', we don't want the scheduler to bother looking at it.
        self.assertEquals(systems[0].scheduler_status, SystemSchedulerStatus.idle)
        # Idle systems should be 'pending', so that the scheduler will check if
        # there is a queued recipe for them to start. Note that this includes
        # Manual and Broken systems since they can be scheduled too!
        self.assertEquals(systems[1].scheduler_status, SystemSchedulerStatus.pending)
        self.assertEquals(systems[2].scheduler_status, SystemSchedulerStatus.pending)
        self.assertEquals(systems[3].scheduler_status, SystemSchedulerStatus.pending)
        # Reserved systems should be 'reserved'.
        self.assertEquals(systems[4].scheduler_status, SystemSchedulerStatus.reserved)

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_queued_recipe_has_installation_column_after_upgrade(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            # add a queued job
            connection.execute(
                "INSERT INTO osmajor (osmajor) "
                "VALUES ('Tiara9')")
            connection.execute(
                "INSERT INTO osversion (osmajor_id, osminor) "
                "VALUES (1, 9)")
            connection.execute(
                "INSERT INTO distro (name, osversion_id, date_created) "
                "VALUES ('Tiara9.9', 1, '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO distro_tree (distro_id, arch_id, variant, date_created) "
                "VALUES (1, 1, 'Server', '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, status, dirty_version, clean_version) "
                "VALUES (1, 1, 'Queued', '', '')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, status, queue_time, waived) "
                "VALUES (1, 'Queued', '2015-11-05 16:31:01', 0)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'New', FALSE)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Processed', FALSE)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Queued', FALSE)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Scheduled', FALSE)")
        # Do the schema upgrades
        upgrade_db(self.migration_metadata)
        self.assertEqual(4, self.migration_session.query(Recipe).count())
        for recipe in self.migration_session.query(Recipe).all():
            self.assertIsNotNone(recipe.installation)
            self.assertEqual(recipe.installation.distro_tree_id, 1)
            self.assertEqual(recipe.installation.arch.arch, u'i386')
            self.assertEqual(recipe.installation.variant, u'Server')
            self.assertEqual(recipe.installation.distro_name, u'Tiara9.9')
            self.assertEqual(recipe.installation.osmajor, u'Tiara9')
            self.assertEqual(recipe.installation.osminor, u'9')
        with self.migration_metadata.bind.connect() as connection:
            self.assertEqual(4,
                             connection.scalar('SELECT count(*) FROM installation;'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1159105
    def test_queue_admin_group_is_granted_permission(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            connection.execute(
                "INSERT INTO tg_group (group_id, group_name, display_name, membership_type, created) "
                "VALUES (41, 'queue_admin', 'queue_admin', 'normal', '2010-05-17 17:23:47')")
        upgrade_db(self.migration_metadata)
        group = self.migration_session.query(Group).get(41)
        change_prio = self.migration_session.query(Permission) \
            .filter_by(permission_name=u'change_prio').one()
        self.assertEquals(group.permissions, [change_prio])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1550361
    def test_downgrading_upgrading_distro_element_will_not_leave_NULL_columns(self):
        init_db(self.migration_metadata)
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                "INSERT INTO beaker_tag (id, tag, type) "
                "VALUES (1, 'scratch', 'retention_tag')")
            connection.execute(
                "INSERT INTO retention_tag (id, expire_in_days, needs_product) "
                "VALUES (1, 0, 0)")
            connection.execute(
                "INSERT INTO tg_user (user_id, user_name, display_name, email_address, disabled, removed, use_old_job_page, notify_job_completion, notify_broken_system, notify_system_loan, notify_group_membership, notify_reservesys) "
                "VALUES (1, 'bob', 'Bob', 'bob@example.com', 1, '2015-12-01 15:43:28', 0, 0, 0, 0, 0, 0)")
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, is_dirty) "
                "VALUES (1, 1, FALSE)")
            connection.execute(
                "INSERT INTO arch (id, arch) "
                "VALUES (2, 'i386')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, queue_time, waived) "
                "VALUES (1, '2015-11-05 16:31:01', 0)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, autopick_random) "
                "VALUES ('machine_recipe', 1, FALSE)")
            connection.execute(
                "INSERT INTO osmajor (id, osmajor) "
                "VALUES (1, 'RedHatEnterpriseLinux6')")
            connection.execute(
                "INSERT INTO osversion (osmajor_id, osminor) "
                "VALUES (1, 9)")
            connection.execute(
                "INSERT INTO distro (name, osversion_id, date_created) "
                "VALUES ('RHEL6', 1, '2015-12-01 15:43:28')")
            connection.execute(
                "INSERT INTO distro_tree (distro_id, arch_id, variant, date_created) "
                "VALUES (1, 2, 'Server', '2015-12-01 15:43:28')")
            connection.execute(
                "INSERT INTO installation (id, created, recipe_id, tree_url, initrd_path, kernel_path, osmajor, arch_id) "
                "VALUES (1, '2018-03-02 05:21:45', 1, 'http://download.test/Fedora-27/os', 'initrd.img', 'vmlinuz', 'Fedora27', 2)")
        downgrade_db(self.migration_metadata, '24.5')
        upgrade_db(self.migration_metadata)
        installation = self.migration_session.query(Installation).get(1)
        self.assertEqual('http://download.test/Fedora-27/os', installation.tree_url)
        self.assertEqual(datetime.datetime(2018, 3, 2, 5, 21, 45), installation.created)
        self.assertEqual('initrd.img', installation.initrd_path)
        self.assertEqual('vmlinuz', installation.kernel_path)
        self.assertEqual('Fedora27', installation.osmajor)
        self.assertEqual(u'i386', installation.arch.arch)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1550361
    def test_upgrade_will_not_insert_duplicate_installation_rows(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/24.sql'))
            # add a queued job
            connection.execute(
                "INSERT INTO osmajor (osmajor) "
                "VALUES ('Tiara9')")
            connection.execute(
                "INSERT INTO osversion (osmajor_id, osminor) "
                "VALUES (1, 9)")
            connection.execute(
                "INSERT INTO distro (name, osversion_id, date_created) "
                "VALUES ('Tiara9.9', 1, '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO distro_tree (distro_id, arch_id, variant, date_created) "
                "VALUES (1, 1, 'Server', '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, status, dirty_version, clean_version) "
                "VALUES (1, 1, 'Queued', '', '')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, status, queue_time, waived) "
                "VALUES (1, 'Queued', '2015-11-05 16:31:01', 0)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Queued', FALSE)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Processed', FALSE)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Aborted', FALSE)")
        # Do the schema upgrades
        upgrade_db(self.migration_metadata)
        # Scenario: An error occurred so lets downgrade again to the last stable version
        downgrade_db(self.migration_metadata, '24.5')
        # All is fixed upgrade again
        upgrade_db(self.migration_metadata)
        with self.migration_metadata.bind.connect() as connection:
            self.assertEqual(3,
                             connection.scalar('SELECT count(*) FROM installation;'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1568224
    def test_scheduled_recipe_has_installation_column_after_upgrade(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/25.sql'))
            # add a queued job
            connection.execute(
                "INSERT INTO osmajor (id, osmajor) "
                "VALUES (1, 'RedHatEnterpriseLinux6')")
            connection.execute(
                "INSERT INTO osversion (osmajor_id, osminor) "
                "VALUES (1, 9)")
            connection.execute(
                "INSERT INTO distro (name, osversion_id, date_created) "
                "VALUES ('RHEL6', 1, '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO distro_tree (distro_id, arch_id, variant, date_created) "
                "VALUES (1, 1, 'Server', '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, status, dirty_version, clean_version) "
                "VALUES (1, 1, 'Scheduled', '', '')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, status, queue_time, waived) "
                "VALUES (1, 'Scheduled', '2015-11-05 16:31:01', 0)")
            connection.execute(
                "INSERT INTO recipe (type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES ('machine_recipe', 1, 1, 'Scheduled', FALSE)")
        recipe = self.migration_session.query(Recipe).get(1)
        # Recipe has been missed by past migration and has no installation row
        self.assertIsNone(recipe.installation)
        self.migration_session.close()

        # This migration has become a NOOP
        migration = DataMigration(name=u'insert-installation-row-for-scheduled-recipes-before-25')
        finished = migration.migrate_one_batch(self.migration_metadata.bind)
        self.assertTrue(finished)

        # This is the right data migration
        migration = DataMigration(name=u'insert-installation-row-for-recipes-before-25-take-2')
        finished = migration.migrate_one_batch(self.migration_metadata.bind)
        self.assertTrue(finished)

        recipe = self.migration_session.query(Recipe).get(1)
        self.assertIsNotNone(recipe.installation)
        self.assertEqual(recipe.installation.distro_tree_id, 1)
        self.assertEqual(recipe.installation.arch.arch, u'i386')
        self.assertEqual(recipe.installation.variant, u'Server')
        self.assertEqual(recipe.installation.distro_name, u'RHEL6')
        self.assertEqual(recipe.installation.osmajor, u'RedHatEnterpriseLinux6')
        self.assertEqual(recipe.installation.osminor, u'9')
        with self.migration_metadata.bind.connect() as connection:
            self.assertEqual(1,
                             connection.scalar('SELECT count(*) FROM installation;'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1568224
    def test_scheduled_recipe_has_installation_column_after_upgrade_when_cancelled(self):
        with self.migration_metadata.bind.connect() as connection:
            connection.execute(
                pkg_resources.resource_string('bkr.inttest.server', 'database-dumps/25.sql'))
            # add a queued job
            connection.execute(
                "INSERT INTO osmajor (id, osmajor) "
                "VALUES (1, 'RedHatEnterpriseLinux6')")
            connection.execute(
                "INSERT INTO osversion (osmajor_id, osminor) "
                "VALUES (1, 9)")
            connection.execute(
                "INSERT INTO distro (name, osversion_id, date_created) "
                "VALUES ('RHEL6', 1, '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO distro_tree (distro_id, arch_id, variant, date_created) "
                "VALUES (1, 1, 'Server', '2017-07-27 14:28:20')")
            connection.execute(
                "INSERT INTO job (owner_id, retention_tag_id, status, dirty_version, clean_version) "
                "VALUES (1, 1, 'Installing', '', '')")
            connection.execute(
                "INSERT INTO recipe_set (job_id, status, queue_time, waived) "
                "VALUES (1, 'Aborted', '2015-11-05 16:31:01', 0)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES (1, 'machine_recipe', 1, 1, 'Cancelled', FALSE)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES (2, 'machine_recipe', 1, 1, 'Aborted', FALSE)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES (3, 'machine_recipe', 1, 1, 'Installing', FALSE)")
            connection.execute(
                "INSERT INTO installation (created, recipe_id, distro_tree_id, variant, distro_name, initrd_path, kernel_path, osminor, osmajor, arch_id) "
                "VALUES ('2018-03-02 05:21:45', 3, 1, 'Server', 'RHEL6', 'initrd.img', 'vmlinuz', '9', 'RedHatEnterpriseLinux6', 1)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES (4, 'machine_recipe', 1, 1, 'Waiting', FALSE)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES (5, 'machine_recipe', 1, 1, 'Running', FALSE)")
            connection.execute(
                "INSERT INTO recipe (id, type, recipe_set_id, distro_tree_id, status, autopick_random) "
                "VALUES (6, 'machine_recipe', 1, 1, 'Scheduled', FALSE)")
        r1, r2, r3, r4, r5, r6 = self.migration_session.query(Recipe).all()
        for recipe in [r1, r2, r4, r5, r6]:
            self.assertIsNone(recipe.installation)
        self.assertIsNotNone(r3.installation)
        self.migration_session.close()

        migration = DataMigration(name=u'insert-installation-row-for-recipes-before-25-take-2')
        finished = migration.migrate_one_batch(self.migration_metadata.bind)
        self.assertTrue(finished)

        for recipe in self.migration_session.query(Recipe).all():
            self.assertIsNotNone(recipe.installation,
                                 'Installation row for recipeid %s (%s) should exist' % (
                                 recipe.id, recipe.status))
            self.assertEqual(recipe.installation.distro_tree_id, 1)
            self.assertEqual(recipe.installation.arch.arch, u'i386')
            self.assertEqual(recipe.installation.variant, u'Server')
            self.assertEqual(recipe.installation.distro_name, u'RHEL6')
            self.assertEqual(recipe.installation.osmajor, u'RedHatEnterpriseLinux6')
            self.assertEqual(recipe.installation.osminor, u'9')
        with self.migration_metadata.bind.connect() as connection:
            self.assertEqual(6,
                             connection.scalar('SELECT count(*) FROM installation;'))
