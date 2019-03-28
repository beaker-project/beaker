
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase
from bkr.server.model import System, Key, Key_Value_String, SystemStatus, Cpu
import datetime


class SystemListTest(ClientTestCase):

    def check_systems(self, present=None, absent=None):
        for system in present:
            self.assert_(system.fqdn in self.returned_systems)

        for system in absent:
            self.assert_(system.fqdn not in self.returned_systems)

    def test_list_all_systems(self):
        with session.begin():
            data_setup.create_system() # so that we have at least one
            system1 = data_setup.create_system(status=SystemStatus.removed)
        out = run_client(['bkr', 'system-list'])
        self.assertNotIn(system1.fqdn, out.splitlines())
        self.assertEqual(len(out.splitlines()),
                         System.query.filter(System.status!=SystemStatus.removed).count())

    def test_list_removed_systems(self):
        with session.begin():
            data_setup.create_system()
            system2 = data_setup.create_system(status=SystemStatus.removed)
        out = run_client(['bkr', 'system-list', '--removed'])
        self.assertIn(system2.fqdn, out.splitlines())
        self.assertEqual(len(out.splitlines()),
                         System.query.filter(System.status==SystemStatus.removed).count())

    # https://bugzilla.redhat.com/show_bug.cgi?id=920018
    def test_list_systems_lc_disabled(self):
        with session.begin():
            lc1 = data_setup.create_labcontroller()
            lc2 = data_setup.create_labcontroller()
            system1 = data_setup.create_system(fqdn=data_setup.unique_name(u'aaaa%s.testdata'))
            system1.lab_controller = lc1
            system2 = data_setup.create_system(fqdn=data_setup.unique_name(u'aaaa%s.testdata'))
            system2.lab_controller = lc2

            # set lc2 to disabled
            lc2.disabled = True

        out = run_client(['bkr', 'system-list'])
        systems = out.splitlines()
        self.assertIn(system1.fqdn, systems)
        self.assertIn(system2.fqdn, systems)

        out = run_client(['bkr', 'system-list', '--free'])
        systems = out.splitlines()
        self.assertIn(system1.fqdn, systems)
        self.assertNotIn(system2.fqdn, systems)

        out = run_client(['bkr', 'system-list', '--available'])
        systems = out.splitlines()
        self.assertIn(system1.fqdn, systems)
        self.assertIn(system2.fqdn, systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=690063
    def test_xml_filter(self):
        with session.begin():
            module_key = Key.by_name(u'MODULE')
            with_module = data_setup.create_system()
            with_module.key_values_string.extend([
                    Key_Value_String(module_key, u'cciss'),
                    Key_Value_String(module_key, u'kvm')])
            without_module = data_setup.create_system()
        out = run_client(['bkr', 'system-list',
                          '--xml-filter', '<key_value key="MODULE" />'])
        returned_systems = out.splitlines()
        self.assert_(with_module.fqdn in returned_systems, returned_systems)
        self.assert_(without_module.fqdn not in returned_systems,
                returned_systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1167164
    def test_handles_xml_syntax_error(self):
        try:
            run_client(['bkr', 'system-list', '--xml-filter', '<error'])
            self.fail('should be an error')
        except ClientError as e:
            self.assertIn('Invalid XML syntax for host filter', e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1118523
    def test_predefined_host_filter(self):
        with session.begin():
            matching = data_setup.create_system()
            matching.cpu = Cpu(vendor=u'GenuineIntel', family=6, model=47, model_name=u'Intel')
            nonmatching = data_setup.create_system()
        out = run_client(['bkr', 'system-list',
                          '--host-filter', 'INTEL__WESTMERE'])
        returned_systems = out.splitlines()
        self.assertIn(matching.fqdn, returned_systems)
        self.assertNotIn(nonmatching.fqdn, returned_systems)

    def test_multiple_xml_filters(self):
        with session.begin():
            module_key = Key.by_name(u'MODULE')
            matching = data_setup.create_system()
            matching.cpu = Cpu(vendor=u'GenuineIntel', family=6, model=47, model_name=u'Intel')
            matching.key_values_string.append(
                    Key_Value_String(module_key, u'cciss'))
            nonmatching = data_setup.create_system()
        out = run_client(['bkr', 'system-list',
                          '--xml-filter', '<not><lender value="shark"/></not>',
                          '--xml-filter', '<key_value key="MODULE" value="cciss"/>',
                          '--host-filter', 'INTEL__WESTMERE'])
        returned_systems = out.splitlines()
        self.assertIn(matching.fqdn, returned_systems)
        self.assertNotIn(nonmatching.fqdn, returned_systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=949777
    def test_inventory_date_search(self):

        # date times
        today = datetime.date.today()
        time_now = datetime.datetime.combine(today, datetime.time(0, 0))
        time_delta1 = datetime.datetime.combine(today, datetime.time(0, 30))
        time_tomorrow = time_now + datetime.timedelta(days=1)

        # today date
        date_today = time_now.date().isoformat()
        date_tomorrow = time_tomorrow.date().isoformat()

        with session.begin():
            not_inv = data_setup.create_system()

            inv1 = data_setup.create_system()
            inv1.date_lastcheckin = time_now

            inv2 = data_setup.create_system()
            inv2.date_lastcheckin = time_delta1

            inv3 = data_setup.create_system()
            inv3.date_lastcheckin = time_tomorrow

        # uninventoried
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<last_inventoried op="=" value="" />'
                          '</system>'])

        self.returned_systems = out.splitlines()
        self.check_systems(present=[not_inv], absent=[inv1, inv2, inv3])

        # Return all inventoried systems
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<last_inventoried op="!=" value="" />'
                          '</system>'])

        self.returned_systems = out.splitlines()
        self.check_systems(present=[inv1, inv2, inv2], absent=[not_inv])

        # inventoried on a certain date
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<last_inventoried op="=" value="%s" />'
                          '</system>'% date_today])

        self.returned_systems = out.splitlines()
        self.check_systems(present=[inv1, inv2], absent=[not_inv, inv3])

        # not inventoried on a certain date
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<last_inventoried op="!=" value="%s" />'
                          '</system>' % date_today])

        self.returned_systems = out.splitlines()
        self.check_systems(present=[inv3], absent=[not_inv, inv1, inv2])

        # Before a certain date
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<last_inventoried op="&lt;" value="%s" />'
                          '</system>' % date_tomorrow])

        self.returned_systems = out.splitlines()
        self.check_systems(present=[inv1, inv2], absent=[not_inv, inv3])

        # On or before a certain date
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<last_inventoried op="&lt;=" value="%s" />'
                          '</system>' % date_tomorrow])

        self.returned_systems = out.splitlines()
        self.check_systems(present=[inv1, inv2, inv3], absent=[not_inv])

        # Only date is valid, not date time
        try:
            out = run_client(['bkr', 'system-list',
                              '--xml-filter',
                              '<system>'
                              '<last_inventoried op="&gt;" value="%s 00:00:00" />'
                              '</system>' % today])
            self.fail('Must Fail or Die')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assert_('Invalid date format' in e.stderr_output,
                    e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=955868
    def test_added_date_search(self):

        # date times
        today = datetime.date.today()
        time_now = datetime.datetime.combine(today, datetime.time(0, 0))
        time_delta1 = datetime.datetime.combine(today, datetime.time(0, 30))
        time_tomorrow = time_now + datetime.timedelta(days=1)
        time_tomorrow = time_now + datetime.timedelta(days=2)

        # dates
        date_today = time_now.date().isoformat()
        date_tomorrow = time_tomorrow.date().isoformat()

        with session.begin():
            sys_today1 = data_setup.create_system(arch=u'i386', shared=True,
                                          date_added=time_now)
            sys_today2 = data_setup.create_system(arch=u'i386', shared=True,
                                          date_added=time_delta1)
            sys_tomorrow = data_setup.create_system(arch=u'i386', shared=True,
                                            date_added=time_tomorrow)

        # on a date
        out = run_client(['bkr', 'system-list',
                          '--xml-filter',
                          '<system>'
                          '<added op="=" value="%s" />'
                          '</system>' % date_today])

        returned_systems = out.splitlines()
        self.assert_(sys_today1.fqdn in returned_systems)
        self.assert_(sys_today2.fqdn in returned_systems)
        self.assert_(sys_tomorrow.fqdn not in returned_systems)

        # on a datetime
        try:
            run_client(['bkr', 'system-list',
                        '--xml-filter',
                        '<system>'
                        '<added op="=" value="%s" />'
                        '</system>' % time_now])
            self.fail('Must Fail or Die')
        except ClientError as e:
            self.assertEquals(e.status, 1)
            self.assert_('Invalid date format' in e.stderr_output, e.stderr_output)

        # date as  " "
        try:
            run_client(['bkr', 'system-list',
                        '--xml-filter',
                        '<system>'
                        '<added op="=" value=" " />'
                        '</system>'])
            self.fail('Must Fail or die')
        except ClientError as e:
            self.assertEquals(e.status, 1)
            self.assert_('Invalid date format' in e.stderr_output, e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1217158
    def test_filter_by_pool(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            inpool = data_setup.create_system()
            pool.systems.append(inpool)
            data_setup.create_system()
        out = run_client(['bkr', 'system-list', '--pool', pool.name])
        self.assertEquals([inpool.fqdn], out.splitlines())

        # --group is a hidden compatibility alias for --pool
        out = run_client(['bkr', 'system-list', '--group', pool.name])
        self.assertEquals([inpool.fqdn], out.splitlines())

    def test_old_command_list_systems_still_works(self):
        with session.begin():
            data_setup.create_system() # so that we have at least one
            system1 = data_setup.create_system(status=SystemStatus.removed)
        out = run_client(['bkr', 'list-systems'])
        self.assertNotIn(system1.fqdn, out.splitlines())
        self.assertEqual(len(out.splitlines()),
                         System.query.filter(System.status!=SystemStatus.removed).count())
