
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import datetime
from time import sleep
from bkr.server.model import Job, System, User
import sqlalchemy.orm
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.assertions import assert_datetime_within, \
        assert_durations_not_overlapping

class TestGroupXml(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.distro_tree = data_setup.create_distro_tree(arch=u'i386')
        self.user = data_setup.create_user()

    @with_transaction
    def _test_group(self, test_op, test_name, matching_ids):
        """
        Check the group selector

        Arguments:

        test_op      - operator to use ("=", "==" or "!=")
        test_name    - use group name as value when evaluates to True,
                       empty string otherwise
        matching_ids - list of system ids expected to match.
                       Should be a subset of ("a", "b", "ab", "_")

        """
        group_a = data_setup.create_group()
        self.user.groups.append(group_a)
        system_a = data_setup.create_system(arch=u'i386', shared=True)
        system_a.lab_controller = self.lc
        system_a.groups.append(group_a)
        system_0 = data_setup.create_system(arch=u'i386', shared=True)
        system_0.lab_controller = self.lc
        group_b = data_setup.create_group()
        self.user.groups.append(group_b)
        system_ab = data_setup.create_system(arch=u'i386', shared=True)
        system_ab.lab_controller = self.lc
        system_ab.groups.append(group_a)
        system_ab.groups.append(group_b)
        system_b = data_setup.create_system(arch=u'i386', shared=True)
        system_b.lab_controller = self.lc
        system_b.groups.append(group_b)
        all_systems = dict(a=system_a, ab=system_ab, b=system_b, _=system_0)
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <group op="%s" value="%s" />
                </and>
            </hostRequires>
            """ % (test_op, (test_name and group_a.group_name or ""))))
        for system_id in all_systems.keys():
            if system_id in matching_ids:
                self.assert_(all_systems[system_id] in systems)
            else:
                self.assert_(all_systems[system_id] not in systems)

    def test_group(self):
        """test <group = value/> case"""
        self._test_group("=", "a", ("a", "ab"))

    def test_not_in_group(self):
        """test <group != value/> case"""
        self._test_group("!=", "a", ("b", "_"))

    # https://bugzilla.redhat.com/show_bug.cgi?id=601952
    def test_member_of_no_groups(self):
        """test <group == ""/> case"""
        self._test_group("==", "", ("_",))

    def test_member_of_any_group(self):
        """test <group != ""/> case"""
        self._test_group("!=", "", ("a", "ab", "b"))

