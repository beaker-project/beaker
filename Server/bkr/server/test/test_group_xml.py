import unittest
import datetime
from time import sleep
from bkr.server.model import TaskStatus, Job, System, User
import sqlalchemy.orm
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.test.assertions import assert_datetime_within, \
        assert_durations_not_overlapping

class TestGroupXml(unittest.TestCase):

    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.distro = data_setup.create_distro(arch=u'i386')
        self.user = data_setup.create_user()
        session.flush()

    def test_group(self):
        group = data_setup.create_group()
        self.user.groups.append(group)
        has_groups = data_setup.create_system(arch=u'i386', shared=True)
        has_groups.lab_controller = self.lc
        has_groups.groups.append(group)
        no_groups = data_setup.create_system(arch=u'i386', shared=True)
        no_groups.lab_controller = self.lc
        session.flush()
        systems = list(self.distro.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <group op="==" value="%s" />
                </and>
            </hostRequires>
            """ % group.group_name))
        self.assert_(no_groups not in systems)
        self.assert_(has_groups in systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=601952
    def test_member_of_no_groups(self):
        group = data_setup.create_group()
        self.user.groups.append(group)
        has_groups = data_setup.create_system(arch=u'i386', shared=True)
        has_groups.lab_controller = self.lc
        has_groups.groups.append(group)
        no_groups = data_setup.create_system(arch=u'i386', shared=True)
        no_groups.lab_controller = self.lc
        session.flush()
        systems = list(self.distro.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <group op="!="/>
                </and>
            </hostRequires>
            """))
        self.assert_(has_groups not in systems)
        self.assert_(no_groups in systems)

