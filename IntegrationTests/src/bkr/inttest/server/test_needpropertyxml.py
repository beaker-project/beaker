
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from collections import namedtuple
from bkr.server.model import session, System, SystemType, SystemStatus, Cpu, \
        Arch, Numa, Key, Key_Value_String, Key_Value_Int, Disk
from bkr.server.needpropertyxml import XmlHost
from bkr.inttest import data_setup, DatabaseTestCase

class SystemFilteringTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def check_filter(self, filterxml, present=[], absent=[]):
        session.flush()
        query = XmlHost.from_string(filterxml).apply_filter(System.query)
        if present:
            self.assertItemsEqual(present,
                    query.filter(System.id.in_([s.id for s in present])).all())
        if absent:
            self.assertItemsEqual([],
                    query.filter(System.id.in_([s.id for s in absent])).all())

    def test_autoprov(self):
        no_power = data_setup.create_system()
        no_power.power = None
        no_lab = data_setup.create_system(lab_controller=None)
        included = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller())
        self.check_filter("""
            <hostRequires>
                <auto_prov value="True" />
            </hostRequires>
            """,
            present=[included],
            absent=[no_power, no_lab])

    def test_system_type(self):
        excluded = data_setup.create_system(type=SystemType.prototype)
        included = data_setup.create_system(type=SystemType.machine)
        self.check_filter("""
            <hostRequires>
                <system><type op="==" value="Machine" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        # Deprecated system_type
        self.check_filter("""
            <hostRequires>
                <system_type op="==" value="Machine" />
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_status(self):
        excluded = data_setup.create_system(status=SystemStatus.manual)
        included = data_setup.create_system(
            lab_controller=data_setup.create_labcontroller(),
            status=SystemStatus.automated)
        self.check_filter("""
            <hostRequires>
                <system><status op="==" value="Automated" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_lender(self):
        excluded = data_setup.create_system(lender=u'my excluded lender')
        included = data_setup.create_system(lender=u'my included lender')
        self.check_filter("""
            <hostRequires>
                <system><lender op="like" value="%included%" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_model(self):
        excluded = data_setup.create_system(model=u'grover')
        included = data_setup.create_system(model=u'elmo')
        self.check_filter("""
            <hostRequires>
                <system><model op="=" value="elmo" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_vendor(self):
        excluded = data_setup.create_system(vendor=u'apple')
        included = data_setup.create_system(vendor=u'mango')
        self.check_filter("""
            <hostRequires>
                <system><vendor op="!=" value="apple" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_owner(self):
        owner1 = data_setup.create_user()
        owner2 = data_setup.create_user()
        excluded = data_setup.create_system(owner=owner1)
        excluded.user = owner2
        included = data_setup.create_system(owner=owner2)
        self.check_filter("""
            <hostRequires>
                <system><owner op="=" value="%s" /></system>
            </hostRequires>
            """ % owner2.user_name,
            present=[included], absent=[excluded])

    def test_system_user(self):
        user1 = data_setup.create_user()
        user2 = data_setup.create_user()
        excluded = data_setup.create_system(owner=user2)
        excluded.user = user1
        included = data_setup.create_system()
        included.user = user2
        self.check_filter("""
            <hostRequires>
                <system>
                 <user op="=" value="%s" />
                 <owner op="!=" value="%s" />
                </system>
            </hostRequires>
            """ % (user2.user_name, user2.user_name),
            present=[included], absent=[excluded])

    #https://bugzilla.redhat.com/show_bug.cgi?id=955868
    def test_system_added(self):
        # date times
        today = datetime.date.today()
        time_now = datetime.datetime.combine(today, datetime.time(0, 0))
        time_delta1 = datetime.datetime.combine(today, datetime.time(0, 30))
        time_tomorrow = time_now + datetime.timedelta(days=2)

        # today date
        date_today = time_now.date().isoformat()
        date_tomorrow = time_tomorrow.date().isoformat()

        sys_today1 = data_setup.create_system(date_added=time_now)
        sys_today2 = data_setup.create_system(date_added=time_delta1)
        sys_tomorrow = data_setup.create_system(date_added=time_tomorrow)

        # on a date
        self.check_filter("""
            <hostRequires>
                <system><added op="=" value="%s" /></system>
            </hostRequires>
            """ % date_today,
            present=[sys_today1, sys_today2], absent=[sys_tomorrow])

        # not on a date
        self.check_filter("""
            <hostRequires>
                <system><added op="!=" value="%s" /></system>
            </hostRequires>
            """ % date_today,
            present=[sys_tomorrow], absent=[sys_today1, sys_today2])

        # after a date
        self.check_filter("""
            <hostRequires>
                <system><added op="&gt;" value="%s" /></system>
            </hostRequires>
            """ % date_today,
            present=[sys_tomorrow], absent=[sys_today1, sys_today2])

        # before a date
        self.check_filter("""
            <hostRequires>
                <system><added op="&lt;" value="%s" /></system>
            </hostRequires>
            """ % date_tomorrow,
            present=[sys_today1, sys_today2], absent=[sys_tomorrow])

        # on a date time
        with self.assertRaisesRegexp(ValueError, 'Invalid date format'):
            self.check_filter("""
                <hostRequires>
                    <system><added op="=" value="%s" /></system>
                </hostRequires>
                """ % time_now)

    # https://bugzilla.redhat.com/show_bug.cgi?id=949777
    def test_system_inventory_filter(self):
        # date times
        today = datetime.date.today()
        time_now = datetime.datetime.combine(today, datetime.time(0, 0))
        time_delta1 = datetime.datetime.combine(today, datetime.time(0, 30))
        time_tomorrow = time_now + datetime.timedelta(days=1)
        time_dayafter = time_now + datetime.timedelta(days=2)

        # dates
        date_today = time_now.date().isoformat()
        date_dayafter = time_dayafter.date().isoformat()

        not_inv = data_setup.create_system()
        inv1 = data_setup.create_system()
        inv1.date_lastcheckin = time_now
        inv2 = data_setup.create_system()
        inv2.date_lastcheckin = time_delta1
        inv3 = data_setup.create_system()
        inv3.date_lastcheckin = time_tomorrow

        # not inventoried
        self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="=" value="" /> </system>
                </hostRequires>
                """,
                present=[not_inv], absent=[inv1, inv2, inv3])

        # inventoried
        self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="!=" value="" /> </system>
                </hostRequires>
                """,
                present=[inv1, inv2, inv3], absent=[not_inv])

        # on a particular day
        self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="=" value="%s" /> </system>
                </hostRequires>
                """ % date_today,
                present=[inv1, inv2],
                absent=[not_inv, inv3])

        # on a particular day on which no machines have been inventoried
        self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="=" value="%s" /> </system>
                </hostRequires>
                """ % date_dayafter,
                absent=[inv1, inv2, inv3, not_inv])

        # not on a particular day
        self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="!=" value="%s" /> </system>
                </hostRequires>
                """ % date_today,
                present=[inv3], absent=[not_inv, inv1, inv2])

        # after a particular day
        self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="&gt;" value="%s" /> </system>
                </hostRequires>
                """ % date_today,
                present=[inv3], absent=[not_inv, inv1, inv2])

        # Invalid date with &gt;
        with self.assertRaisesRegexp(ValueError, 'Invalid date format'):
            self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="&gt;" value="foo-bar-baz f:b:z" /> </system>
                </hostRequires>
                """)

        # Invalid date format with =
        with self.assertRaisesRegexp(ValueError, 'Invalid date format'):
            self.check_filter("""
                <hostRequires>
                    <system> <last_inventoried op="=" value="2013-10-10 00:00:10" /> </system>
                </hostRequires>
                """)

    def test_system_loaned(self):
        user1 = data_setup.create_user()
        user2 = data_setup.create_user()
        excluded = data_setup.create_system(loaned=user1, owner=user2)
        excluded.user = user2
        included = data_setup.create_system(loaned=user2)
        self.check_filter("""
            <hostRequires>
                <system>
                 <loaned op="=" value="%s" />
                 <owner op="!=" value="%s" />
                </system>
            </hostRequires>
            """ % (user2.user_name, user2.user_name),
            present=[included], absent=[excluded])

    def test_system_location(self):
        excluded = data_setup.create_system(location=u'singletary')
        included = data_setup.create_system(location=u'rayburn')
        self.check_filter("""
            <hostRequires>
                <system><location op="=" value="rayburn" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_serial(self):
        excluded = data_setup.create_system(serial=u'0u812')
        included = data_setup.create_system(serial=u'2112')
        self.check_filter("""
            <hostRequires>
                <system><serial op="=" value="2112" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_system_powertype(self):
        excluded = data_setup.create_system()
        data_setup.configure_system_power(excluded, power_type=u'ipmilan')
        included = data_setup.create_system()
        data_setup.configure_system_power(included, power_type=u'virsh')
        self.check_filter("""
            <hostRequires>
                <system><powertype op="=" value="virsh" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_hostname(self):
        excluded = data_setup.create_system()
        included = data_setup.create_system()
        self.check_filter("""
            <hostRequires>
                <hostname op="==" value="%s" />
            </hostRequires>
            """ % included.fqdn,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <system><name op="==" value="%s" /></system>
            </hostRequires>
            """ % included.fqdn,
            present=[included], absent=[excluded])

    def test_memory(self):
        excluded = data_setup.create_system(memory=128)
        included = data_setup.create_system(memory=1024)
        self.check_filter("""
            <hostRequires>
                <memory op="&gt;=" value="256" />
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_cpu(self):
        excluded = data_setup.create_system()
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system()
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        self.check_filter("""
            <hostRequires>
                <and>
                    <cpu_count op="=" value="4" />
                </and>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                    <cpu><processors op="=" value="4" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <and>
                    <cpu><processors op="&gt;" value="2" /></cpu>
                    <cpu><processors op="&lt;" value="5" /></cpu>
                </and>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <and>
                    <cpu_count op="&gt;" value="2" />
                    <cpu_count op="&lt;" value="5" />
                </and>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><cores op="&gt;" value="1" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><family op="=" value="10" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><model op="=" value="4" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><sockets op="&gt;=" value="2" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><speed op="&gt;=" value="1500.0" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><stepping op="&gt;=" value="1" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><vendor op="like" value="%Intel" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><model_name op="like" value="%Xeon%" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><hyper value="true" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_cpu_flags(self):
        excluded = data_setup.create_system()
        excluded.cpu = Cpu(processors=1, flags=[u'ssse3', 'pae'])
        included = data_setup.create_system()
        included.cpu = Cpu(processors=1, flags=[u'ssse3', 'vmx'])
        self.check_filter("""
            <hostRequires>
                <cpu><flag value="vmx" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><flag op="!=" value="pae" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <cpu><flag op="like" value="%vmx%" /></cpu>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_or_lab_controller(self):
        lc1 = data_setup.create_labcontroller(fqdn=u'lab1.testdata.invalid')
        lc2 = data_setup.create_labcontroller(fqdn=u'lab2.testdata.invalid')
        lc3 = data_setup.create_labcontroller(fqdn=u'lab3.testdata.invalid')
        included = data_setup.create_system()
        included.lab_controller = lc1
        excluded = data_setup.create_system()
        excluded.lab_controller = lc3
        self.check_filter("""
               <hostRequires>
                <or>
                 <hostlabcontroller op="=" value="lab1.testdata.invalid"/>
                 <hostlabcontroller op="=" value="lab2.testdata.invalid"/>
                </or>
               </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
               <hostRequires>
                <or>
                 <labcontroller op="=" value="lab1.testdata.invalid"/>
                 <labcontroller op="=" value="lab2.testdata.invalid"/>
                </or>
               </hostRequires>
            """,
            present=[included], absent=[excluded])

    # https://bugzilla.redhat.com/show_bug.cgi?id=831448
    def test_hostlabcontroller_notequal(self):
        desirable_lc = data_setup.create_labcontroller()
        undesirable_lc = data_setup.create_labcontroller()
        included = data_setup.create_system(lab_controller=desirable_lc)
        excluded = data_setup.create_system(lab_controller=undesirable_lc)
        self.check_filter("""
                <hostRequires>
                    <hostlabcontroller op="!=" value="%s" />
                </hostRequires>
                """ % undesirable_lc.fqdn,
                present=[included], absent=[excluded])
        self.check_filter("""
                <hostRequires>
                    <labcontroller op="!=" value="%s" />
                </hostRequires>
                """ % undesirable_lc.fqdn,
                present=[included], absent=[excluded])

    def test_arch_equal(self):
        excluded = data_setup.create_system(arch=u'i386')
        included = data_setup.create_system(arch=u'i386')
        included.arch.append(Arch.by_name(u'x86_64'))
        self.check_filter("""
            <hostRequires>
                <arch op="=" value="x86_64" />
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <system><arch op="=" value="x86_64" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_arch_notequal(self):
        excluded = data_setup.create_system(arch=u'i386')
        excluded.arch.append(Arch.by_name(u'x86_64'))
        included = data_setup.create_system(arch=u'i386')
        self.check_filter("""
            <hostRequires>
                <arch op="!=" value="x86_64" />
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <system><arch op="!=" value="x86_64" /></system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_numa_node_count(self):
        excluded = data_setup.create_system()
        excluded.numa = Numa(nodes=1)
        included = data_setup.create_system()
        included.numa = Numa(nodes=64)
        self.check_filter("""
            <hostRequires>
                <and>
                    <numa_node_count op=">=" value="32" />
                </and>
            </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
            <hostRequires>
                <system>
                    <numanodes op=">=" value="32" />
                </system>
            </hostRequires>
            """,
            present=[included], absent=[excluded])

    def test_key_equal(self):
        module_key = Key.by_name(u'MODULE')
        with_cciss = data_setup.create_system()
        with_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_cciss = data_setup.create_system()
        without_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'ida'),
                Key_Value_String(module_key, u'kvm')])
        self.check_filter("""
            <hostRequires>
                <key_value key="MODULE" op="==" value="cciss"/>
            </hostRequires>
            """,
            present=[with_cciss], absent=[without_cciss])

    # https://bugzilla.redhat.com/show_bug.cgi?id=679879
    def test_key_notequal(self):
        module_key = Key.by_name(u'MODULE')
        with_cciss = data_setup.create_system()
        with_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_cciss = data_setup.create_system()
        without_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'ida'),
                Key_Value_String(module_key, u'kvm')])
        self.check_filter("""
            <hostRequires>
                <and>
                    <key_value key="MODULE" op="!=" value="cciss"/>
                </and>
            </hostRequires>
            """,
            present=[without_cciss], absent=[with_cciss])

    def test_key_present(self):
        module_key = Key.by_name(u'MODULE')
        with_module = data_setup.create_system()
        with_module.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_module = data_setup.create_system()
        self.check_filter("""
            <hostRequires>
                <key_value key="MODULE" op="==" />
            </hostRequires>
            """,
            present=[with_module], absent=[without_module])

    def test_key_absent(self):
        module_key = Key.by_name(u'MODULE')
        with_module = data_setup.create_system()
        with_module.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_module = data_setup.create_system()
        self.check_filter("""
            <hostRequires>
                <key_value key="MODULE" op="!=" />
            </hostRequires>
            """,
            present=[without_module], absent=[with_module])
        # ... or using <not/> is a saner way to do it:
        self.check_filter("""
            <hostRequires>
                <not><key_value key="MODULE" /></not>
            </hostRequires>
            """,
            present=[without_module], absent=[with_module])

    # https://bugzilla.redhat.com/show_bug.cgi?id=729156
    def test_keyvalue_does_not_cause_duplicate_rows(self):
        system = data_setup.create_system()
        disk_key = Key.by_name(u'DISK')
        system.key_values_int.extend([
                Key_Value_Int(disk_key, 30718),
                Key_Value_Int(disk_key, 140011),
                Key_Value_Int(disk_key, 1048570)])
        session.flush()
        filter = """
            <hostRequires>
                <and>
                    <system><name op="=" value="%s" /></system>
                    <key_value key="DISK" op="&gt;" value="9000" />
                </and>
            </hostRequires>
            """ % system.fqdn
        query = XmlHost.from_string(filter).apply_filter(System.query)
        self.assertEquals(len(query.all()), 1)
        # with the bug this count comes out as 3 instead of 1,
        # which doesn't sound so bad...
        # but when it's 926127 instead of 278, that's bad
        self.assertEquals(query.count(), 1)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1183239
    def test_arch_inside_or(self):
        # The bug was that <arch/> inside <or/> with other conditions would 
        # produce a cartesian product where the join condition was on one side 
        # of the OR, leading to a row explosion (similar to the case above).
        lc = data_setup.create_labcontroller(fqdn=u'bz1183239.lab')
        data_setup.create_system(lab_controller=lc, arch=[u'i386', u'x86_64'])
        session.flush()
        filter = """
            <hostRequires>
                <labcontroller value="bz1183239.lab" />
                <or>
                    <system><arch value="i386" /></system>
                    <hostname op="!=" value="blerch" />
                </or>
            </hostRequires>
            """
        query = XmlHost.from_string(filter).apply_filter(System.query)
        self.assertEquals(len(query.all()), 1)
        # with the bug this count comes out as 2 instead of 1,
        # which doesn't sound so bad...
        # but when it's 30575826 instead of 4131, that's bad
        self.assertEquals(query.count(), 1)

    # https://bugzilla.redhat.com/show_bug.cgi?id=824050
    def test_multiple_nonexistent_keys(self):
        filter = """
            <hostRequires>
                <and>
                    <key_value key="NOTEXIST1" op="=" value="asdf"/>
                    <key_value key="NOTEXIST2" op="=" value="asdf"/>
                </and>
            </hostRequires>
            """
        query = XmlHost.from_string(filter).apply_filter(System.query)
        query.all() # don't care about the results, just that it doesn't break

    # https://bugzilla.redhat.com/show_bug.cgi?id=714974
    def test_hypervisor(self):
        baremetal = data_setup.create_system(hypervisor=None)
        kvm = data_setup.create_system(hypervisor=u'KVM')
        xen = data_setup.create_system(hypervisor=u'Xen')
        self.check_filter("""
            <hostRequires>
                    <system><hypervisor op="=" value="KVM" /></system>
            </hostRequires>
            """,
            present=[kvm], absent=[baremetal, xen])
        self.check_filter("""
            <hostRequires>
                <and>
                    <hypervisor op="=" value="KVM" />
                </and>
            </hostRequires>
            """,
            present=[kvm], absent=[baremetal, xen])
        self.check_filter("""
            <hostRequires>
                    <system><hypervisor op="=" value="" /></system>
            </hostRequires>
            """,
            present=[baremetal], absent=[kvm, xen])
        self.check_filter("""
            <hostRequires>
                <and>
                    <hypervisor op="=" value="" />
                </and>
            </hostRequires>
            """,
            present=[baremetal], absent=[kvm, xen])
        self.check_filter("""
            <hostRequires/>
            """,
            present=[baremetal, kvm, xen])
        # https://bugzilla.redhat.com/show_bug.cgi?id=886816
        self.check_filter("""
            <hostRequires>
                <hypervisor op="!=" value="KVM" />
            </hostRequires>
            """,
            present=[baremetal, xen], absent=[kvm])
        # https://bugzilla.redhat.com/show_bug.cgi?id=1464120
        self.check_filter("""
            <hostRequires>
                <not><hypervisor op="=" value="KVM" /></not>
            </hostRequires>
            """,
            present=[baremetal, xen], absent=[kvm])
        self.check_filter("""
            <hostRequires>
                <not><hypervisor op="like" value="%KVM%" /></not>
            </hostRequires>
            """,
            present=[baremetal, xen], absent=[kvm])
        self.check_filter("""
            <hostRequires>
                <not>
                    <or>
                        <hypervisor op="like" value="%KVM%" />
                        <hypervisor op="like" value="%Xen%" />
                    </or>
                </not>
            </hostRequires>
            """,
            present=[baremetal], absent=[kvm, xen])

    # https://bugzilla.redhat.com/show_bug.cgi?id=731615
    def test_filtering_by_device(self):
        network_class = data_setup.create_device_class(u'NETWORK')
        with_e1000 = data_setup.create_system()
        with_e1000.devices.append(data_setup.create_device(
                device_class_id=network_class.id,
                vendor_id=u'8086', device_id=u'107c',
                subsys_vendor_id=u'8086', subsys_device_id=u'1376',
                bus=u'pci', driver=u'e1000',
                description=u'82541PI Gigabit Ethernet Controller'))
        with_tg3 = data_setup.create_system()
        with_tg3.devices.append(data_setup.create_device(
                device_class_id=network_class.id,
                vendor_id=u'14e4', device_id=u'1645',
                subsys_vendor_id=u'10a9', subsys_device_id=u'8010',
                bus=u'pci', driver=u'tg3',
                description=u'NetXtreme BCM5701 Gigabit Ethernet'))
        self.check_filter("""
            <hostRequires>
                <device op="=" driver="e1000" />
            </hostRequires>
            """,
            present=[with_e1000], absent=[with_tg3])
        # preferred spelling of this is <not><... op="=" ..></not>
        # but we support the counter-intuitive != as well
        self.check_filter("""
            <hostRequires>
                <device op="!=" driver="e1000" />
            </hostRequires>
            """,
            present=[with_tg3], absent=[with_e1000])
        self.check_filter("""
            <hostRequires>
                <device op="like" description="82541PI%" />
            </hostRequires>
            """,
            present=[with_e1000], absent=[with_tg3])
        self.check_filter("""
            <hostRequires>
                <device op="=" type="network" vendor_id="8086" />
            </hostRequires>
            """,
            present=[with_e1000], absent=[with_tg3])
        self.check_filter("""
            <hostRequires>
                <device op="=" vendor_id="14E4" device_id="1645" />
            </hostRequires>
            """,
            present=[with_tg3], absent=[with_e1000])
        # this filter does nothing, but at least it shouldn't explode
        self.check_filter("""
            <hostRequires>
                <device op="=" />
            </hostRequires>
            """,
            present=[with_e1000, with_tg3])

    # https://bugzilla.redhat.com/show_bug.cgi?id=766919
    def test_filtering_by_disk(self):
        small_disk = data_setup.create_system()
        small_disk.disks[:] = [Disk(size=8000000000,
                sector_size=512, phys_sector_size=512)]
        big_disk = data_setup.create_system()
        big_disk.disks[:] = [Disk(size=2000000000000,
                sector_size=4096, phys_sector_size=4096)]
        big_512e_disk = data_setup.create_system()
        big_512e_disk.disks[:] = [Disk(size=2000000000000,
                sector_size=512, phys_sector_size=4096)]
        two_disks = data_setup.create_system()
        two_disks.disks[:] = [
                Disk(size=500000000000, sector_size=512, phys_sector_size=512),
                Disk(size=8000000000, sector_size=4096, phys_sector_size=4096)]

        # criteria inside the same <disk/> element apply to a single disk
        # and are AND'ed by default
        self.check_filter("""
            <hostRequires>
                <disk>
                    <size op="&gt;" value="10" units="GB" />
                    <phys_sector_size op="=" value="4" units="KiB" />
                </disk>
            </hostRequires>
            """,
            present=[big_disk, big_512e_disk], absent=[small_disk, two_disks])

        # separate <disk/> elements can match separate disks
        self.check_filter("""
            <hostRequires>
                <disk><size op="&gt;" value="10" units="GB" /></disk>
                <disk><phys_sector_size op="=" value="4" units="KiB" /></disk>
            </hostRequires>
            """,
            present=[big_disk, big_512e_disk, two_disks], absent=[small_disk])

        # <not/> combined with a negative filter can be used to filter against 
        # all disks (e.g. "give me systems with only 512-byte-sector disks")
        self.check_filter("""
            <hostRequires>
                <not><disk><sector_size op="!=" value="512" /></disk></not>
            </hostRequires>
            """,
            present=[small_disk, big_512e_disk], absent=[big_disk, two_disks])

        # https://bugzilla.redhat.com/show_bug.cgi?id=1197074
        # use logical operators inside <disk>
        self.check_filter("""
            <hostRequires>
                <disk>
                    <and>
                        <size op="&gt;" value="10" units="GB" />
                        <phys_sector_size op="=" value="4" units="KiB" />
                    </and>
                </disk>
            </hostRequires>
            """,
            present=[big_disk, big_512e_disk], absent=[small_disk, two_disks])

        self.check_filter("""
            <hostRequires>
                <disk>
                    <or>
                        <size op="&gt;" value="10" units="GB" />
                        <phys_sector_size op="=" value="4" units="KiB" />
                    </or>
                </disk>
            </hostRequires>
            """,
            present=[big_disk, big_512e_disk, two_disks], absent=[small_disk])

        self.check_filter("""
            <hostRequires>
                <disk>
                    <not>
                        <sector_size op="!=" value="512" />
                        <phys_sector_size op="=" value="4" units="KiB" />
                    </not>
                </disk>
            </hostRequires>
            """,
            present=[small_disk, two_disks, big_512e_disk], absent=[big_disk])

        self.check_filter("""
            <hostRequires>
                <disk><sector_size op="=" value="4096" /></disk>
            </hostRequires>
            """,
            present=[big_disk, two_disks], absent=[small_disk, big_512e_disk])

        self.check_filter("""
            <hostRequires>
                <disk><sector_size op="!=" value="4096" /></disk>
            </hostRequires>
            """,
            present=[small_disk, big_512e_disk, two_disks], absent=[big_disk])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1187402
    def test_filtering_by_diskspace(self):
        one_disk = data_setup.create_system()
        one_disk.disks[:] = [Disk(size=8000000000, sector_size=512, phys_sector_size=512)]
        two_disks = data_setup.create_system()
        two_disks.disks[:] = [Disk(size=500000000000, sector_size=512, phys_sector_size=512),
                              Disk(size=8000000000, sector_size=4096, phys_sector_size=4096)]
        self.check_filter("""
            <hostRequires>
                <diskspace op="&gt;" value="500" units="GB"/>
            </hostRequires>
            """,
            present=[two_disks], absent=[one_disk])

        self.check_filter("""
            <hostRequires>
                <diskspace op="&lt;" value="50" units="GB"/>
            </hostRequires>
            """,
            present=[one_disk], absent=[two_disks])

        self.check_filter("""
            <hostRequires>
                <diskspace op="==" value="508" units="GB"/>
            </hostRequires>
            """,
            present=[two_disks], absent=[one_disk])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1216257
    def test_filtering_by_diskcount(self):
        one_disk = data_setup.create_system()
        one_disk.disks[:] = [Disk(size=8000000000, sector_size=512, phys_sector_size=512)]
        two_disks = data_setup.create_system()
        two_disks.disks[:] = [Disk(size=500000000000, sector_size=512, phys_sector_size=512),
                              Disk(size=8000000000, sector_size=4096, phys_sector_size=4096)]
        three_disks = data_setup.create_system()
        three_disks.disks[:] = [Disk(size=400000000000, sector_size=4096, phys_sector_size=4096),
                                Disk(size=9000000000, sector_size=512, phys_sector_size=512),
                                Disk(size=200000000000, sector_size=512, phys_sector_size=512)]
        self.check_filter("""
            <hostRequires>
                <diskcount op="&lt;" value="2" />
            </hostRequires>
            """,
            present=[one_disk], absent=[two_disks, three_disks])

        self.check_filter("""
            <hostRequires>
                <diskcount op="==" value="2" />
            </hostRequires>
            """,
            present=[two_disks], absent=[one_disk, three_disks])

        self.check_filter("""
            <hostRequires>
                <diskcount op="&gt;" value="2"/>
            </hostRequires>
            """,
            present=[three_disks], absent=[one_disk, two_disks])

    # <group> is deprecated, but we keep the tests to prevent regressive behaviour
    def test_group(self):
        pool_a = data_setup.create_system_pool()
        pool_b = data_setup.create_system_pool()
        system_0 = data_setup.create_system()
        system_a = data_setup.create_system()
        system_a.pools.append(pool_a)
        system_ab = data_setup.create_system()
        system_ab.pools.append(pool_a)
        system_ab.pools.append(pool_b)
        system_b = data_setup.create_system()
        system_b.pools.append(pool_b)
        self.check_filter("""
            <hostRequires>
                <and>
                    <group op="=" value="%s" />
                </and>
            </hostRequires>
            """ % pool_a.name,
            present=[system_a, system_ab],
            absent=[system_b, system_0])
        self.check_filter("""
            <hostRequires>
                <and>
                    <group op="!=" value="%s" />
                </and>
            </hostRequires>
            """ % pool_a.name,
            present=[system_b, system_0],
            absent=[system_a, system_ab])
        # https://bugzilla.redhat.com/show_bug.cgi?id=601952
        self.check_filter("""
            <hostRequires>
                <and>
                    <group op="==" value="" />
                </and>
            </hostRequires>
            """,
            present=[system_0],
            absent=[system_a, system_ab, system_b])
        self.check_filter("""
            <hostRequires>
                <and>
                    <group op="!=" value="" />
                </and>
            </hostRequires>
            """,
            present=[system_a, system_ab, system_b],
            absent=[system_0])

        # https://bugzilla.redhat.com/show_bug.cgi?id=1226076
        self.check_filter("""
            <hostRequires>
                <or>
                    <group op="=" value="%s" />
                    <group op="=" value="%s" />
                </or>
            </hostRequires>
            """ % (pool_a.name, pool_b.name),
            present=[system_a, system_ab, system_b],
            absent=[system_0])

    def test_system_pool(self):
        pool_a = data_setup.create_system_pool()
        pool_b = data_setup.create_system_pool()
        system_0 = data_setup.create_system()
        system_a = data_setup.create_system()
        system_a.pools.append(pool_a)
        system_ab = data_setup.create_system()
        system_ab.pools.append(pool_a)
        system_ab.pools.append(pool_b)
        system_b = data_setup.create_system()
        system_b.pools.append(pool_b)
        self.check_filter("""
            <hostRequires>
                <and>
                    <pool op="=" value="%s" />
                </and>
            </hostRequires>
            """ % pool_a.name,
            present=[system_a, system_ab],
            absent=[system_b, system_0])
        self.check_filter("""
            <hostRequires>
                <and>
                    <pool op="!=" value="%s" />
                </and>
            </hostRequires>
            """ % pool_a.name,
            present=[system_b, system_0],
            absent=[system_a, system_ab])
        # https://bugzilla.redhat.com/show_bug.cgi?id=601952
        self.check_filter("""
            <hostRequires>
                <and>
                    <pool op="==" value="" />
                </and>
            </hostRequires>
            """,
            present=[system_0],
            absent=[system_a, system_ab, system_b])
        self.check_filter("""
            <hostRequires>
                <and>
                    <pool op="!=" value="" />
                </and>
            </hostRequires>
            """,
            present=[system_a, system_ab, system_b],
            absent=[system_0])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1387795
    def test_compatible_with_distro(self):
        distro_tree = data_setup.create_distro_tree(arch=u'ppc64le',
                osmajor=u'RedHatEnterpriseLinux7', osminor=u'4')
        excluded_osmajor = data_setup.create_system(arch=u'ppc64le',
                exclude_osmajor=[distro_tree.distro.osversion.osmajor])
        excluded_osversion = data_setup.create_system(arch=u'ppc64le',
                exclude_osversion=[distro_tree.distro.osversion])
        wrong_arch = data_setup.create_system(arch=u'i386')
        compatible = data_setup.create_system(arch=u'ppc64le')
        self.check_filter("""
            <hostRequires>
                <system>
                    <compatible_with_distro
                        osmajor="RedHatEnterpriseLinux7"
                        osminor="4"
                        arch="ppc64le"/>
                </system>
            </hostRequires>
            """,
            present=[compatible],
            absent=[excluded_osmajor, excluded_osversion, wrong_arch])

        # osminor attribute is optional
        self.check_filter("""
            <hostRequires>
                <system>
                    <compatible_with_distro
                        osmajor="RedHatEnterpriseLinux7"
                        arch="ppc64le"/>
                </system>
            </hostRequires>
            """,
            present=[compatible],
            absent=[excluded_osmajor, excluded_osversion, wrong_arch])

FakeFlavor = namedtuple('FakeFlavor', ['disk', 'ram', 'vcpus'])

class OpenstackFlavorFilteringTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.lc = data_setup.create_labcontroller()

    def tearDown(self):
        session.commit()

    def check_filter(self, filterxml, lab_controller=None, present=[], absent=[]):
        if lab_controller is None:
            lab_controller = self.lc
        matched_flavors = XmlHost.from_string(filterxml)\
            .filter_openstack_flavors(present + absent, lab_controller)
        self.assertItemsEqual(present, matched_flavors)

    def test_flavors_with_no_disk_are_always_excluded(self):
        # We always unconditionally exclude flavors with 0 disk because they 
        # cannot have an OS installed onto them.
        no_disk = FakeFlavor(disk=0, ram=256, vcpus=1)
        some_disk = FakeFlavor(disk=10, ram=512, vcpus=1)
        self.check_filter('<hostRequires/>',
                present=[some_disk], absent=[no_disk])

    def test_all_flavors_excluded_by_default(self):
        # There are a lot of host requirements which can never be satisfied by 
        # an OpenStack instance, so the default behaviour is to return no 
        # matching flavors. Testing <serial/> here as a representative example.
        self.check_filter("""
            <hostRequires>
                <system><serial value="123" /></system>
            </hostRequires>
            """,
            present=[], absent=[FakeFlavor(disk=10, ram=512, vcpus=1)])

    def test_labcontroller(self):
        flavors = [FakeFlavor(disk=10, ram=512, vcpus=1)]
        self.check_filter("""
            <hostRequires>
                <labcontroller value="%s"/>
            </hostRequires>
            """ % self.lc.fqdn,
            present=flavors, absent=[])
        self.check_filter("""
            <hostRequires>
                <labcontroller op="!=" value="%s"/>
            </hostRequires>
            """ % self.lc.fqdn,
            present=[], absent=flavors)

    def test_hypervisor(self):
        flavors = [FakeFlavor(disk=10, ram=512, vcpus=1)]
        self.check_filter("""
            <hostRequires>
                <hypervisor value="KVM"/>
            </hostRequires>
            """,
            present=flavors, absent=[])
        self.check_filter("""
            <hostRequires>
                <hypervisor op="!=" value="KVM"/>
            </hostRequires>
            """,
            present=[], absent=flavors)
        self.check_filter("""
            <hostRequires>
                <hypervisor value=""/>
            </hostRequires>
            """,
            present=[], absent=flavors)

    def test_system_type(self):
        flavors = [FakeFlavor(disk=10, ram=512, vcpus=1)]
        self.check_filter("""
            <hostRequires>
                <system_type value="Machine" />
            </hostRequires>
            """,
            present=flavors, absent=[])
        self.check_filter("""
            <hostRequires>
                <system_type value="Prototype" />
            </hostRequires>
            """,
            present=[], absent=flavors)

    def test_memory(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <memory op="&gt;" value="1000" />
            </hostRequires>
            """,
            present=[large_flavor], absent=[small_flavor])

    def test_cpu_processors(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <cpu><processors op="&gt;" value="1" /></cpu>
            </hostRequires>
            """,
            present=[large_flavor], absent=[small_flavor])

    def test_cpu_cores(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <cpu><cores op="&gt;" value="1" /></cpu>
            </hostRequires>
            """,
            present=[large_flavor], absent=[small_flavor])

    def test_disk_size(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <disk><size op="&gt;" value="15" /></disk>
            </hostRequires>
            """,
            present=[large_flavor], absent=[small_flavor])

    def test_disk_model(self):
        # All other disk criteria aside from size cannot be satisfied by a VM.
        flavors = [FakeFlavor(disk=10, ram=512, vcpus=1)]
        self.check_filter("""
            <hostRequires>
                <disk><model value="Oceanfence Velocipenguin" /></disk>
            </hostRequires>
            """,
            present=[], absent=flavors)

    def test_system_arch(self):
        flavors = [FakeFlavor(disk=10, ram=512, vcpus=1)]
        self.check_filter("""
            <hostRequires>
                <system><arch value="x86_64"/></system>
            </hostRequires>
            """,
            present=flavors, absent=[])
        self.check_filter("""
            <hostRequires>
                <system><arch value="i386"/></system>
            </hostRequires>
            """,
            present=flavors, absent=[])
        self.check_filter("""
            <hostRequires>
                <system><arch value="ia64"/></system>
            </hostRequires>
            """,
            present=[], absent=flavors)

    def test_or(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        medium_flavor = FakeFlavor(disk=15, ram=1024, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <or>
                    <memory value="512" />
                    <memory value="2048" />
                </or>
            </hostRequires>
            """,
            present=[small_flavor, large_flavor], absent=[medium_flavor])

    def test_and(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        medium_flavor = FakeFlavor(disk=15, ram=1024, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <and>
                    <cpu><cores value="1" /></cpu>
                    <memory value="512" />
                </and>
            </hostRequires>
            """,
            present=[small_flavor], absent=[medium_flavor, large_flavor])

    def test_not(self):
        small_flavor = FakeFlavor(disk=10, ram=512, vcpus=1)
        large_flavor = FakeFlavor(disk=20, ram=2048, vcpus=2)
        self.check_filter("""
            <hostRequires>
                <not><pool value="somepool"/></not>
                <not><memory op="&lt;" value="2048"/></not>
            </hostRequires>
            """,
            present=[large_flavor], absent=[small_flavor])

class VirtualisabilityTestCase(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def check_filter(self, filterxml, virtualisable_expected):
        result = XmlHost.from_string(filterxml).virtualisable()
        self.assertEquals(result, virtualisable_expected)

    def test_not_virtualisable_by_default(self):
        # There are a lot of host requirements which can never be satisfied by 
        # an OpenStack instance, so the default behaviour is to return False. 
        # Testing <serial/> here as a representative example.
        self.check_filter("""
            <hostRequires>
                <system><serial value="123" /></system>
            </hostRequires>
            """,
            False)

    def test_labcontroller(self):
        # <labcontroller/> can match, if it is the LC which OpenStack is 
        # associated with
        self.check_filter("""
            <hostRequires>
                <labcontroller value="anything"/>
            </hostRequires>
            """,
            True)

    def test_hypervisor(self):
        self.check_filter("""
            <hostRequires>
                <hypervisor value="KVM"/>
            </hostRequires>
            """,
            True)
        self.check_filter("""
            <hostRequires>
                <hypervisor op="!=" value="KVM"/>
            </hostRequires>
            """,
            False)
        self.check_filter("""
            <hostRequires>
                <hypervisor value=""/>
            </hostRequires>
            """,
            False)

    def test_system_type(self):
        self.check_filter("""
            <hostRequires>
                <system_type value="Machine" />
            </hostRequires>
            """,
            True)
        self.check_filter("""
            <hostRequires>
                <system_type value="Prototype" />
            </hostRequires>
            """,
            False)

    def test_memory(self):
        # <memory/> can match depending on the flavors available in OpenStack
        self.check_filter("""
            <hostRequires>
                <memory op="&gt;" value="1000" />
            </hostRequires>
            """,
            True)

    def test_cpu_processors(self):
        # <processors/> can match depending on the flavors available in OpenStack
        self.check_filter("""
            <hostRequires>
                <cpu><processors op="&gt;" value="1" /></cpu>
            </hostRequires>
            """,
            True)

    def test_cpu_cores(self):
        # <cores/> can match depending on the flavors available in OpenStack
        self.check_filter("""
            <hostRequires>
                <cpu><cores op="&gt;" value="1" /></cpu>
            </hostRequires>
            """,
            True)

    def test_disk(self):
        self.check_filter("""
            <hostRequires>
                <disk><size op="&gt;" value="15" /></disk>
            </hostRequires>
            """,
            True)
        self.check_filter("""
            <hostRequires>
                <disk><model value="Oceanfence Velocipenguin" /></disk>
            </hostRequires>
            """,
            False)

    def test_system_arch(self):
        self.check_filter("""
            <hostRequires>
                <system><arch value="x86_64"/></system>
            </hostRequires>
            """,
            True)
        self.check_filter("""
            <hostRequires>
                <system><arch value="i386"/></system>
            </hostRequires>
            """,
            True)
        self.check_filter("""
            <hostRequires>
                <system><arch value="ia64"/></system>
            </hostRequires>
            """,
            False)

    def test_or(self):
        # <disk/> cannot match but <memory/> can, therefore True
        self.check_filter("""
            <hostRequires>
                <or>
                    <memory value="512" />
                    <disk><model value="Oceanfence Velocipenguin" /></disk>
                </or>
            </hostRequires>
            """,
            True)

    def test_and(self):
        # <memory/> can match but <disk/> cannot, therefore False
        self.check_filter("""
            <hostRequires>
                <and>
                    <memory value="512" />
                    <disk><model value="Oceanfence Velocipenguin" /></disk>
                </and>
            </hostRequires>
            """,
            False)

    def test_not(self):
        self.check_filter("""
            <hostRequires>
                <not>
                    <pool value="somepool"/>
                </not>
            </hostRequires>
            """,
            True)
