
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import unittest2 as unittest
from bkr.server.model import session, System, SystemType, SystemStatus, Cpu, \
        Arch, Numa, Key, Key_Value_String, Key_Value_Int, Disk
from bkr.server.needpropertyxml import XmlHost
from bkr.inttest import data_setup

class SystemFilteringTest(unittest.TestCase):

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
        included = data_setup.create_system(status=SystemStatus.automated)
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
        lc1 = data_setup.create_labcontroller(fqdn=u'lab1')
        lc2 = data_setup.create_labcontroller(fqdn=u'lab2')
        lc3 = data_setup.create_labcontroller(fqdn=u'lab3')
        included = data_setup.create_system()
        included.lab_controller = lc1
        excluded = data_setup.create_system()
        excluded.lab_controller = lc3
        self.check_filter("""
               <hostRequires>
                <or>
                 <hostlabcontroller op="=" value="lab1"/>
                 <hostlabcontroller op="=" value="lab2"/>
                </or>
               </hostRequires>
            """,
            present=[included], absent=[excluded])
        self.check_filter("""
               <hostRequires>
                <or>
                 <labcontroller op="=" value="lab1"/>
                 <labcontroller op="=" value="lab2"/>
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
            present=[big_disk], absent=[small_disk, two_disks])

        # separate <disk/> elements can match separate disks
        self.check_filter("""
            <hostRequires>
                <disk><size op="&gt;" value="10" units="GB" /></disk>
                <disk><phys_sector_size op="=" value="4" units="KiB" /></disk>
            </hostRequires>
            """,
            present=[big_disk, two_disks], absent=[small_disk])

        # <not/> combined with a negative filter can be used to filter against 
        # all disks (e.g. "give me systems with only 512-byte-sector disks")
        self.check_filter("""
            <hostRequires>
                <not><disk><sector_size op="!=" value="512" /></disk></not>
            </hostRequires>
            """,
            present=[small_disk], absent=[big_disk, two_disks])

    def test_group(self):
        group_a = data_setup.create_group()
        group_b = data_setup.create_group()
        system_0 = data_setup.create_system()
        system_a = data_setup.create_system()
        system_a.groups.append(group_a)
        system_ab = data_setup.create_system()
        system_ab.groups.append(group_a)
        system_ab.groups.append(group_b)
        system_b = data_setup.create_system()
        system_b.groups.append(group_b)
        self.check_filter("""
            <hostRequires>
                <and>
                    <group op="=" value="%s" />
                </and>
            </hostRequires>
            """ % group_a.group_name,
            present=[system_a, system_ab],
            absent=[system_b, system_0])
        self.check_filter("""
            <hostRequires>
                <and>
                    <group op="!=" value="%s" />
                </and>
            </hostRequires>
            """ % group_a.group_name,
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
