
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import requests
import datetime
import xmlrpclib
from threading import Thread, Event
from turbogears.database import session
from sqlalchemy.orm.exc import NoResultFound

from bkr.inttest.server.selenium import XmlRpcTestCase, \
    WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest.server.requests_utils import login as web_login
from bkr.inttest import data_setup, get_server_base,\
    fix_beakerd_repodata_perms, DatabaseTestCase
from bkr.inttest.server.requests_utils import patch_json, post_json
from bkr.inttest.assertions import assert_datetime_within
from bkr.server.model import Distro, DistroTree, Arch, ImageType, Job, \
    System, SystemStatus, TaskStatus, Command, CommandStatus, \
    KernelType, LabController, User, OSMajor, OSVersion, LabControllerActivity, \
    Group, Installation
from bkr.server.tools import beakerd
from bkr.server.wsgi import app
from bkr.server import identity


class LabControllerCreateTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def _add_lc(self, lc_name, lc_email=None, lc_username=None):
        lc_email = lc_email or data_setup.unique_name('me@my%s.com')
        lc_username = lc_username or data_setup.unique_name('host/myname%s')
        b = self.browser
        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_class_name('labcontroller-add').click()
        b.find_element_by_name('fqdn').send_keys(lc_name)
        b.find_element_by_name('email_address').send_keys(lc_email)
        b.find_element_by_name('user_name').send_keys(lc_username)
        b.find_element_by_class_name('edit-labcontroller').submit()

    def test_lab_controller_add(self):
        b = self.browser
        lc_name = data_setup.unique_name(u'lc%s.com')
        lc_email = data_setup.unique_name(u'me@my%s.com')
        lc_username = data_setup.unique_name(u'operator%s')
        self._add_lc(lc_name, lc_email, lc_username)
        b.find_element_by_xpath('//li[contains(., "%s")]' % lc_name)

        # check activity
        with session.begin():
            lc = LabController.by_name(lc_name)
            self.assertEquals(lc.activity[0].field_name, u'Disabled')
            self.assertEquals(lc.activity[0].action, u'Changed')
            self.assertEquals(lc.activity[0].new_value, u'False')
            self.assertEquals(lc.activity[1].field_name, u'User')
            self.assertEquals(lc.activity[1].action, u'Changed')
            self.assertEquals(lc.activity[1].new_value, lc_username)
            self.assertEquals(lc.activity[2].field_name, u'FQDN')
            self.assertEquals(lc.activity[2].action, u'Changed')
            self.assertEquals(lc.activity[2].new_value, lc_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=998374
    def test_cannot_add_duplicate_lc(self):
        with session.begin():
            existing_lc = data_setup.create_labcontroller()
        self._add_lc(existing_lc.fqdn, existing_lc.user.email_address)
        b = self.browser
        self.assertEquals(b.find_element_by_class_name('alert-error').text,
                          'CONFLICT: Lab Controller %s already exists' % existing_lc.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1064710
    def test_cannot_add_lc_with_used_username(self):
        with session.begin():
            existing_lc = data_setup.create_labcontroller()
        self._add_lc(data_setup.unique_name('lc.dummy.%s.com'), lc_username=existing_lc.user.user_name)
        b = self.browser
        expected = re.compile(r'User %s is already associated with lab controller %s' % (
            existing_lc.user.user_name, existing_lc.fqdn))
        self.assertRegexpMatches(
            b.find_element_by_class_name('alert-error').text, expected)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290266
    def test_can_edit_labcontroller_after_adding(self):
        b = self.browser
        lc_name = data_setup.unique_name('lc%s.com')
        lc_email = data_setup.unique_name('me@my%s.com')
        lc_username = data_setup.unique_name('operator%s')
        self._add_lc(lc_name, lc_email, lc_username)

        b.find_element_by_xpath(
            '//li[contains(., "%s")]//button[contains(., "Edit")]' % lc_name).click()
        b.find_element_by_name('fqdn').send_keys('test')
        b.find_element_by_class_name('edit-labcontroller').submit()

        # should be successful, therefore no modal being present
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal-backdrop")])]')


class LabControllerViewTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
        self.browser = self.get_browser()
        login(self.browser)

    # https://bugzilla.redhat.com/show_bug.cgi?id=998374
    def test_cannot_change_fqdn_to_duplicate(self):
        with session.begin():
            other_lc = data_setup.create_labcontroller()
        b = self.browser
        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Edit")]' % self.lc.fqdn).click()
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys(other_lc.fqdn)
        b.find_element_by_class_name('edit-labcontroller').submit()
        self.assertEquals(
            b.find_element_by_class_name('alert-error').text,
                'BAD REQUEST: FQDN %s already in use' % other_lc.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1064710
    def test_cannot_change_username_to_duplicate(self):
        # Changing an LC's username to an existing user account is okay, but 
        # you can't change it to a user account that is already being used by 
        # another LC.
        with session.begin():
            other_lc = data_setup.create_labcontroller()
        b = self.browser
        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Edit")]' % self.lc.fqdn).click()
        b.find_element_by_name('user_name').clear()
        b.find_element_by_name('user_name').send_keys(other_lc.user.user_name)
        b.find_element_by_class_name('edit-labcontroller').submit()
        expected = re.compile(r'User %s is already associated with lab controller %s' % (
            other_lc.user.user_name, other_lc.fqdn))
        self.assertRegexpMatches(
            b.find_element_by_class_name('alert-error').text, expected)

    def test_lab_controller_remove(self):
        b = self.browser
        with session.begin():
            # When an LC is removed, we de-associate all systems, set them to
            # broken, cancel all running recipes, and remove all distro tree
            # associations. So this test creates a system, job, and distro tree
            # in the lab to cover all those cases.
            sys = data_setup.create_system(lab_controller=self.lc)
            sys.action_power(action='clear_logs')
            sys.action_power(action='configure_netboot')
            sys.action_power(action='reboot')

            job = data_setup.create_running_job(lab_controller=self.lc)
            distro_tree = data_setup.create_distro_tree(lab_controllers=[self.lc])

        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Remove")]' % self.lc.fqdn).click()
        b.find_element_by_xpath('//button[@type="button" and .//text()="OK"]').click()
        # Wait for the 'remove' request to finish by waiting for the 'Restore' button to appear
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Restore")]' % self.lc.fqdn)
        with session.begin():
            session.expire_all()
            # system set to broken?
            self.assertEquals(sys.status, SystemStatus.broken)

            # check lc activity
            self.assertEquals(self.lc.activity[0].field_name, u'Removed')
            self.assertEquals(self.lc.activity[0].action, u'Changed')
            self.assertEquals(self.lc.activity[0].new_value, u'True')
            self.assertEquals(self.lc.activity[1].field_name, u'Disabled')
            self.assertEquals(self.lc.activity[1].action, u'Changed')
            self.assertEquals(self.lc.activity[1].new_value, u'True')

            # check system activity
            self.assertEquals(sys.activity[0].field_name, u'Lab Controller')
            self.assertEquals(sys.activity[0].action, u'Changed')
            self.assertEquals(sys.activity[0].new_value, None)

            # Check that queued commands are aborted when lab controller removed
            # https://bugzilla.redhat.com/show_bug.cgi?id=1362371
            self.assertEquals(sys.activity[1].field_name, u'Power')
            self.assertEquals(sys.activity[1].action, u'clear_logs')
            self.assertEquals(sys.activity[1].new_value, u'Aborted: System disassociated from lab controller')

            self.assertEquals(sys.activity[2].field_name, u'Power')
            self.assertEquals(sys.activity[2].action, u'configure_netboot')
            self.assertEquals(sys.activity[2].new_value, u'Aborted: System disassociated from lab controller')

            self.assertEquals(sys.activity[3].field_name, u'Power')
            self.assertEquals(sys.activity[3].action, u'off')
            self.assertEquals(sys.activity[3].new_value, u'Aborted: System disassociated from lab controller')

            self.assertEquals(sys.activity[4].field_name, u'Power')
            self.assertEquals(sys.activity[4].action, u'on')
            self.assertEquals(sys.activity[4].new_value, u'Aborted: System disassociated from lab controller')

            self.assertEquals(sys.activity[5].field_name, u'Status')
            self.assertEquals(sys.activity[5].action, u'Changed')
            self.assertEquals(sys.activity[5].new_value, 'Broken')

            # check that the status duration reflects the new system status
            self.assertEquals(sys.status_durations[0].status, SystemStatus.broken)
            # check job status
            job.update_status()
            self.assertEquals(job.status, TaskStatus.cancelled)
            # check distro tree activity
            self.assertEquals(distro_tree.activity[0].field_name,
                              u'lab_controller_assocs')
            self.assertEquals(distro_tree.activity[0].action, u'Removed')

    def test_remove_and_restore(self):
        with session.begin():
            system = data_setup.create_system()
            system.lab_controller = self.lc
            distro_tree = data_setup.create_distro_tree(lab_controllers=[self.lc])
        self.assert_(any(lca.lab_controller == self.lc
                         for lca in distro_tree.lab_controller_assocs))

        # Remove and wait until the request has finished by waiting for the
        # 'Restore' button to appear
        b = self.browser
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath(
            '//li[contains(., "%s")]//button[contains(., "Remove")]' % self.lc.fqdn).click()
        b.find_element_by_xpath('//button[@type="button" and .//text()="OK"]').click()
        b.find_element_by_xpath(
            '//li[contains(., "%s")]//button[contains(., "Restore")]' % self.lc.fqdn)
        with session.begin():
            session.refresh(self.lc)
            self.assertTrue(self.lc.removed)
            session.refresh(system)
            self.assert_(system.lab_controller is None)
            session.refresh(distro_tree)
            self.assert_(not any(lca.lab_controller == self.lc
                                 for lca in distro_tree.lab_controller_assocs))

        # Restore
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath(
            '//li[contains(., "%s")]//button[contains(., "Restore")]' % self.lc.fqdn).click()
        # Lab Controller is restored identified by Edit and 'Remove' buttons
        b.find_element_by_xpath(
            '//li[contains(., "%s")]//button[contains(., "Remove")]' % self.lc.fqdn)
        b.find_element_by_xpath(
            '//li[contains(., "%s")]//button[contains(., "Edit")]' % self.lc.fqdn)

    def test_shows_list_when_permissions_insufficient(self):
        with session.begin():
            self.user = data_setup.create_user(password='asdf')

        b = self.get_browser()
        login(b, user=self.user.user_name, password='asdf')
        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_xpath('//body[not(.//li[contains(., "%s")]//button[contains(., "Remove")])]' % self.lc.fqdn)

    def test_updates_labcontroller(self):
        new_values = dict(
            fqdn=data_setup.unique_name('lc.foo.%s.com'),
            user_name=data_setup.unique_name('user1%s'),
            password='asdf',
            email_address='new_user_test@beaker-project.org',
        )
        b = self.browser
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Edit")]' % self.lc.fqdn).click()
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys(new_values['fqdn'])
        b.find_element_by_name('user_name').clear()
        b.find_element_by_name('user_name').send_keys(new_values['user_name'])
        b.find_element_by_name('email_address').clear()
        b.find_element_by_name('email_address').send_keys(new_values['email_address'])
        b.find_element_by_name('password').send_keys(new_values['password'])
        b.find_element_by_class_name('edit-labcontroller').submit()
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Edit")]' % new_values['fqdn'])

        with session.begin():
            session.refresh(self.lc)
            self.assertEqual(self.lc.fqdn, new_values['fqdn'])
            self.assertEqual(self.lc.user.user_name, new_values['user_name'])
            self.assertEqual(self.lc.user.email_address, new_values['email_address'])
            self.assertFalse(self.lc.removed)
            self.assertFalse(self.lc.disabled)

    def test_disables_labcontroller(self):
        b = self.browser
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath('//li[contains(., "%s")]//button[contains(., "Edit")]' % self.lc.fqdn).click()
        b.find_element_by_name('disabled').click()
        b.find_element_by_class_name('edit-labcontroller').submit()
        b.find_element_by_xpath('//li[contains(., "%s")]//small[text()="Disabled"]' % self.lc.fqdn)

        with session.begin():
            session.refresh(self.lc)
            self.assertTrue(self.lc.disabled)


class AddDistroTreeXmlRpcTest(XmlRpcTestCase):

    distro_data = dict(
            name='RHEL-6-U1',
            arches=['i386', 'x86_64'], arch='x86_64',
            osmajor='RedHatEnterpriseLinux6', osminor='1',
            variant='Workstation', tree_build_time=1305067998.6483951,
            urls=[u'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/',
                  u'http://example.invalid/RHEL-6-Workstation/U1/x86_64/os/'],
            repos=[
                dict(repoid=u'Workstation', type='os', path=u''),
                dict(repoid=u'ScalableFileSystem', type='addon', path=u'ScalableFileSystem/'),
                dict(repoid=u'optional', type='addon', path=u'../../optional/x86_64/os/'),
                dict(repoid=u'debuginfo', type='debug', path=u'../debug/'),
            ],
            images=[
                dict(type='kernel', path=u'images/pxeboot/vmlinuz'),
                dict(type='initrd', path=u'images/pxeboot/initrd.img'),
            ],
            tags=['RELEASED'])

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
            self.lc2 = data_setup.create_labcontroller()
            self.lc2.user.password = u'logmein'
        self.server = self.get_server()

    def test_add_distro_tree(self):
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(self.distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            self.assertEquals(distro.osversion.osmajor.osmajor, u'RedHatEnterpriseLinux6')
            self.assertEquals(distro.osversion.osminor, u'1')
            self.assertEquals(distro.osversion.arches,
                    [Arch.by_name(u'i386'), Arch.by_name(u'x86_64')])
            self.assertEquals(distro.date_created,
                    datetime.datetime(2011, 5, 10, 22, 53, 18))
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.date_created,
                    datetime.datetime(2011, 5, 10, 22, 53, 18))
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs'),
                              u'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.repo_by_id('Workstation').path,
                    '')
            self.assertEquals(distro_tree.repo_by_id('ScalableFileSystem').path,
                    'ScalableFileSystem/')
            self.assertEquals(distro_tree.repo_by_id('optional').path,
                    '../../optional/x86_64/os/')
            self.assertEquals(distro_tree.repo_by_id('debuginfo').path,
                    '../debug/')
            self.assertEquals(distro_tree.image_by_type(ImageType.kernel,
                    KernelType.by_name(u'default')).path,
                    'images/pxeboot/vmlinuz')
            self.assertEquals(distro_tree.image_by_type(ImageType.initrd,
                    KernelType.by_name(u'default')).path,
                    'images/pxeboot/initrd.img')
            self.assertEquals(distro_tree.activity[0].field_name, u'lab_controller_assocs')
            self.assertEquals(distro_tree.activity[0].action, u'Added')
            self.assert_(self.lc.fqdn in distro_tree.activity[0].new_value,
                    distro_tree.activity[0].new_value)
            del distro, distro_tree

        # another lab controller adds the same distro tree
        self.server.auth.login_password(self.lc2.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(self.distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.url_in_lab(self.lc2, scheme='nfs'),
                              u'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.activity[0].field_name, u'lab_controller_assocs')
            self.assertEquals(distro_tree.activity[0].action, u'Added')
            self.assert_(self.lc2.fqdn in distro_tree.activity[0].new_value,
                    distro_tree.activity[0].new_value)
            del distro, distro_tree

    def test_change_url(self):
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(self.distro_data)

        # add it again, but with different urls
        new_distro_data = dict(self.distro_data)
        new_distro_data['urls'] = [
            # nfs:// is not included here, so it shouldn't change
            u'nfs+iso://example.invalid:/RHEL-6-Workstation/U1/x86_64/iso/',
            u'http://moved/',
        ]
        self.server.labcontrollers.add_distro_tree(new_distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs'),
                    u'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs+iso'),
                    u'nfs+iso://example.invalid:/RHEL-6-Workstation/U1/x86_64/iso/')
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='http'),
                    u'http://moved/')
            del distro, distro_tree

    # https://bugzilla.redhat.com/show_bug.cgi?id=825913
    def test_existing_distro_row_with_incorrect_osversion(self):
        # We want to add 'RHEL6-bz825913' with osversion
        # 'RedHatEnterpriseLinux6.1'. But that distro already exists
        # with osversion 'RedHatEnterpriseLinux6.0'.
        name = 'RHEL6-bz825913'
        with session.begin():
            data_setup.create_distro(name=name,
                    osmajor=u'RedHatEnterpriseLinux6', osminor=u'0')
        distro_data = dict(self.distro_data)
        distro_data.update({
            'name': name,
            'osmajor': 'RedHatEnterpriseLinux6',
            'osminor': '1',
        })
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(distro_data)
        with session.begin():
            distro = Distro.by_name(name)
            self.assertEquals(distro.osversion.osmajor.osmajor,
                    u'RedHatEnterpriseLinux6')
            self.assertEquals(distro.osversion.osminor, u'1')

    def add_distro_trees_concurrently(self, distro_data1, distro_data2):
        # This doesn't actually call through XML-RPC, it calls the 
        # controller directly in two separate threads, in order to simulate two 
        # lab controllers importing the same distro tree at the same instant.
        from bkr.server.labcontroller import LabControllers
        controller = LabControllers()
        class DistroImportThread(Thread):
            def __init__(self, lc_user_name=None, distro_data=None, **kwargs):
                super(DistroImportThread, self).__init__(**kwargs)
                self.lc_user_name = lc_user_name
                self.distro_data = distro_data
                self.ready_evt = Event()
                self.start_evt = Event()
                self.commit_evt = Event()
                self.success = False
            def run(self):
                with app.test_request_context('/RPC2'):
                    session.begin()
                    self.ready_evt.set()
                    self.start_evt.wait()
                    lc_user = User.by_user_name(self.lc_user_name)
                    identity.set_authentication(lc_user)
                    controller.add_distro_tree(self.distro_data)
                    self.commit_evt.wait()
                    session.commit()
                self.success = True

        thread1 = DistroImportThread(name='add_distro_trees_thread1',
                lc_user_name=self.lc.user.user_name,
                distro_data=distro_data1)
        thread2 = DistroImportThread(name='add_distro_trees_thread2',
                lc_user_name=self.lc2.user.user_name,
                distro_data=distro_data2)
        thread1.start()
        thread2.start()
        thread1.ready_evt.wait()
        thread2.ready_evt.wait()
        # If you're debugging this test, uncommenting these prints and sleeps, 
        # and enabling logging for sqlalchemy.engine, will help.
        #print '\n\n\n*********** THREAD 1 GO'
        thread1.start_evt.set()
        #time.sleep(1)
        #print '\n\n\n*********** THREAD 2 GO'
        thread2.start_evt.set()
        #time.sleep(1)
        #print '\n\n*********** THREAD 1 COMMIT'
        thread1.commit_evt.set()
        #time.sleep(1)
        #print '\n\n*********** THREAD 2 COMMIT'
        thread2.commit_evt.set()
        thread1.join()
        thread2.join()
        self.assert_(thread1.success)
        self.assert_(thread2.success)

    # https://bugzilla.redhat.com/show_bug.cgi?id=874386
    def test_concurrent_different_trees(self):
        distro_data = dict(self.distro_data)
        # ensure osmajor, osversion, and distro already exist
        with session.begin():
            osmajor = OSMajor.lazy_create(osmajor=distro_data['osmajor'])
            osversion = OSVersion.lazy_create(osmajor=osmajor,
                    osminor=distro_data['osminor'])
            osversion.arches = [Arch.lazy_create(arch=arch)
                    for arch in distro_data['arches']]
            Distro.lazy_create(name=distro_data['name'], osversion=osversion)
        # ensure two different trees
        distro_data['variant'] = u'Workstation'
        distro_data2 = dict(distro_data)
        distro_data2['variant'] = u'Server'
        self.add_distro_trees_concurrently(distro_data, distro_data2)

    def test_concurrent_same_tree(self):
        distro_data = dict(self.distro_data)
        # ensure osmajor, osversion, and distro already exist
        with session.begin():
            osmajor = OSMajor.lazy_create(osmajor=distro_data['osmajor'])
            osversion = OSVersion.lazy_create(osmajor=osmajor,
                    osminor=distro_data['osminor'])
            osversion.arches = [Arch.lazy_create(arch=arch)
                    for arch in distro_data['arches']]
            Distro.lazy_create(name=distro_data['name'], osversion=osversion)
        self.add_distro_trees_concurrently(distro_data, distro_data)

    def test_concurrent_new_distro(self):
        distro_data = dict(self.distro_data)
        # ensure osmajor and osversion already exist
        with session.begin():
            osmajor = OSMajor.lazy_create(osmajor=distro_data['osmajor'])
            osversion = OSVersion.lazy_create(osmajor=osmajor,
                    osminor=distro_data['osminor'])
            osversion.arches = [Arch.lazy_create(arch=arch)
                    for arch in distro_data['arches']]
        # ... but distro is new
        distro_data['name'] = 'concurrent-new-distro'
        self.add_distro_trees_concurrently(distro_data, distro_data)

    def test_concurrent_new_osversion(self):
        distro_data = dict(self.distro_data)
        # ensure osmajor already exists
        with session.begin():
            osmajor = OSMajor.lazy_create(osmajor=distro_data['osmajor'])
        # ... but osversion is new
        distro_data['osminor'] = '6969'
        self.add_distro_trees_concurrently(distro_data, distro_data)

    def test_concurrent_new_osmajor(self):
        distro_data = dict(self.distro_data)
        # ensure osmajor is new
        distro_data['osmajor'] = 'ConcurrentEnterpriseLinux6'
        self.add_distro_trees_concurrently(distro_data, distro_data)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173368
    def test_empty_osmajor_is_invalid(self):
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        distro_data = dict(self.distro_data)
        # set osmajor empty
        distro_data['osmajor'] = ''
        try:
            self.server.labcontrollers.add_distro_tree(distro_data)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
             self.assertIn('OSMajor cannot be empty', e.faultString)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173368
    def test_empty_name_is_invalid(self):
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        distro_data = dict(self.distro_data)
        # set distro name empty
        distro_data['name'] = ''
        try:
            self.server.labcontrollers.add_distro_tree(distro_data)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
             self.assertIn('Distro name cannot be empty', e.faultString)


class GetDistroTreesXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
            self.other_lc = data_setup.create_labcontroller()
        self.server = self.get_server()

    def test_get_all_distro_trees(self):
        with session.begin():
            # one distro which is in the lab
            dt_in  = data_setup.create_distro_tree(
                    lab_controllers=[self.other_lc, self.lc])
            # ... and another which is not
            dt_out = data_setup.create_distro_tree(
                    lab_controllers=[self.other_lc])
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        result = self.server.labcontrollers.get_distro_trees()
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['distro_tree_id'], dt_in.id)
        for lc, url in result[0]['available']:
            self.assertEquals(lc, self.lc.fqdn)

    def test_filter_by_arch(self):
        with session.begin():
            # one distro which has the desired arch
            dt_in  = data_setup.create_distro_tree(arch=u'i386',
                    lab_controllers=[self.other_lc, self.lc])
            # ... and another which does not
            dt_out = data_setup.create_distro_tree(arch=u'ppc64',
                    lab_controllers=[self.other_lc, self.lc])
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        result = self.server.labcontrollers.get_distro_trees(
                {'arch': ['i386', 'x86_64']})
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['distro_tree_id'], dt_in.id)

class CommandQueueXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
        self.server = self.get_server()
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_queued_commands_with_user_defined_metadata(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            installation = Installation(tree_url='ftp://dummylab.example.com/distros/MyAwesomeLinux1/',
                                        initrd_path='pxeboot/initrd', kernel_path='pxeboot/vmlinuz',
                                        arch=Arch.by_name('i386'), system=system, kernel_options=u'anwesha')
            system.configure_netboot(installation=installation, service=u'testdata')
        queued_commands = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(queued_commands[1]['action'], 'configure_netboot')
        self.assertEquals(queued_commands[1]['fqdn'], system.fqdn)
        self.assertEquals(queued_commands[1]['netboot']['arch'], 'i386')
        self.assertEquals(queued_commands[1]['netboot']['distro_tree_id'], None)
        self.assertEquals(queued_commands[1]['netboot']['kernel_url'],
                          'ftp://dummylab.example.com/distros/MyAwesomeLinux1/pxeboot/vmlinuz')
        self.assertEquals(queued_commands[1]['netboot']['initrd_url'],
                          'ftp://dummylab.example.com/distros/MyAwesomeLinux1/pxeboot/initrd')
        self.assertEquals(queued_commands[1]['netboot']['kernel_options'], u'anwesha')

    def setup_system_with_queued_commands(self):
        with session.begin():
            system = data_setup.create_system(arch=[u'i386', u'x86_64'],
                                              lab_controller=self.lc,
                                              status=SystemStatus.automated, shared=True)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            installation = Installation(distro_tree=distro_tree, system=system,
                    kernel_options=u'')
            system.configure_netboot(installation=installation, service=u'testdata')
            system.action_power(action='reboot', installation=installation, service=u'testdata')

        self.assertEqual(4, len(system.command_queue))
        return system

    def test_obeys_max_running_commands_limit(self):
        with session.begin():
            for _ in xrange(15):
                system = data_setup.create_system(lab_controller=self.lc)
                system.action_power(action=u'on', service=u'testdata')
        commands = self.server.labcontrollers.get_queued_command_details()
        # 10 is the configured limit in server-test.cfg
        self.assertEquals(len(commands), 10, commands)

    def test_clear_running_commands(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            command = Command(
                    user=None, service=u'testdata', action=u'on',
                    status=CommandStatus.running)
            system.command_queue.append(command)
            other_system = data_setup.create_system()
            other_command = Command(
                    user=None, service=u'testdata', action=u'on',
                    status=CommandStatus.running)
            other_system.command_queue.append(other_command)
        self.server.labcontrollers.clear_running_commands(u'Staleness')
        with session.begin():
            session.refresh(command)
            self.assertEquals(command.status, CommandStatus.aborted)
            self.assertIsNone(command.start_time)
            self.assertIsNone(command.finish_time)
            self.assertEquals(other_command.status, CommandStatus.running)

    def test_purge_stale_running_commands(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            # Helper to build the commands
            def _make_command(lc, creation_date=None):
                job = data_setup.create_job(distro_tree=distro_tree)
                recipe = job.recipesets[0].recipes[0]
                system = data_setup.create_system(lab_controller=lc)
                data_setup.mark_recipe_waiting(recipe, system=system)
                command = Command(
                        user=None, service=u'testdata', action=u'on',
                        status=CommandStatus.running)
                command.installation = recipe.installation
                if creation_date is not None:
                    command.queue_time = creation_date
                system.command_queue.append(command)
                return recipe.tasks[0], command
            # Normal command for the current LC
            recent_task, recent_command = _make_command(lc=self.lc)
            # Old command for a different LC
            other_lc = data_setup.create_labcontroller()
            backdated = datetime.datetime.utcnow()
            backdated -= datetime.timedelta(days=1, minutes=1)
            old_task, old_command = _make_command(lc=other_lc, creation_date=backdated)

        self.server.labcontrollers.clear_running_commands(u'Staleness')
        with session.begin():
            session.expire_all()
            # Recent commands have their callback invoked
            self.assertEquals(recent_command.status, CommandStatus.aborted)
            self.assertEquals(recent_task.status, TaskStatus.aborted)
            # Stale commands just get dropped on the floor
            self.assertEquals(old_command.status, CommandStatus.aborted)
            self.assertEquals(old_task.status, TaskStatus.waiting)

    def test_add_completed_command(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            fqdn = system.fqdn
        queued = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(len(queued), 0, queued)
        expected = u'Arbitrary command!'
        self.server.labcontrollers.add_completed_command(fqdn, expected)
        queued = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(len(queued), 0, queued)
        with session.begin():
            completed = list(Command.query
                             .join(Command.system)
                             .filter(System.fqdn == fqdn))
            self.assertEquals(len(completed), 1, completed)
            self.assertEquals(completed[0].action, expected)
            assert_datetime_within(completed[0].start_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())
            assert_datetime_within(completed[0].finish_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())

    def test_automated_system_marked_broken_on_power_failure(self):
        with session.begin():
            automated_system = data_setup.create_system(fqdn=u'broken1.example.org',
                                                        lab_controller=self.lc,
                                                        status = SystemStatus.automated)
            automated_system.action_power(u'on')
            command = automated_system.command_queue[0]
        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')
        with session.begin():
            session.refresh(automated_system)
            self.assertEqual(automated_system.status, SystemStatus.broken)
            system_activity = automated_system.activity[0]
            self.assertEqual(system_activity.action, 'on')
            self.assertTrue(system_activity.new_value.startswith('Failed'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=916302
    def test_system_not_marked_broken_for_failed_interrupt_commands(self):
        """The recipe is not aborted if the action command is interrupt which is
        only supported by ipmilan power types."""
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc,
                                              status=SystemStatus.automated)
            system.action_power(u'interrupt')
            command = system.command_queue[0]

        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                                                       u'needs moar powa')
        with session.begin():
            self.assertEqual(SystemStatus.automated, system.status)
            self.assertNotEqual(SystemStatus.broken, system.status)

    # https://bugzilla.redhat.com/show_bug.cgi?id=720672
    def test_manual_system_status_not_changed_on_power_failure(self):
        with session.begin():
            manual_system = data_setup.create_system(fqdn = u'broken2.example.org',
                                                     lab_controller=self.lc,
                                                     status = SystemStatus.manual)
            manual_system.action_power(u'on')
            command = manual_system.command_queue[0]
        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')
        with session.begin():
            session.refresh(manual_system)
            self.assertEqual(manual_system.status, SystemStatus.manual)
            system_activity = manual_system.activity[0]
            self.assertEqual(system_activity.action, 'on')
            self.assertTrue(system_activity.new_value.startswith('Failed'))

    def test_broken_power_aborts_recipe(self):
        # Start a recipe, let it be provisioned, mark the power command as failed,
        # and the recipe should be aborted.
        with session.begin():
            job = data_setup.create_job()
            recipe = job.recipesets[0].recipes[0]
            data_setup.mark_recipe_scheduled(recipe, lab_controller=self.lc)
            recipe.provision()
            recipe.waiting()
            system = recipe.resource.system
            command = system.command_queue[0]
            self.assertEquals(command.action, 'on')

        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')

        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEqual(recipe.status, TaskStatus.aborted)

    def test_abort_commands(self):
        with session.begin():
            job = data_setup.create_job()
            recipe = job.recipesets[0].recipes[0]
            data_setup.mark_recipe_scheduled(recipe, lab_controller=self.lc)
            recipe.provision()
            system = recipe.resource.system
            self.assertEqual(4, len(system.command_queue))

        for command in system.command_queue:
                self.server.labcontrollers.mark_command_running(command.id)
        running_command_ids = self.server.labcontrollers.get_running_command_ids()
        self.assertEqual(4, len(running_command_ids))
        for id in running_command_ids:
            self.server.labcontrollers.mark_command_aborted(id, "Command orphaned, aborting")
        self.assertEqual(0, len(self.server.labcontrollers.get_running_command_ids()))

        with session.begin():
            session.expire_all()
            for command in system.command_queue:
                self.assertEqual(CommandStatus.aborted, command.status)

    def test_failure_in_configure_netboot_aborts_recipe(self):
        with session.begin():
            job = data_setup.create_job()
            recipe = job.recipesets[0].recipes[0]
            data_setup.mark_recipe_scheduled(recipe, lab_controller=self.lc)
            recipe.provision()
            recipe.waiting()
            system = recipe.resource.system
            command = system.command_queue[2]
            self.assertEquals(command.action, 'configure_netboot')

        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                u'oops it borked')

        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEqual(recipe.status, TaskStatus.aborted)

    def test_netboot_config_arch(self):
        with session.begin():
            system = data_setup.create_system(arch=[u'i386', u'x86_64'],
                                              lab_controller=self.lc,
                                              status=SystemStatus.automated, shared=True)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            installation = Installation(distro_tree=distro_tree, system=system, arch=Arch.by_name('i386'),
                                        kernel_options=u'')
            system.configure_netboot(installation=installation, service=u'testdata')
        queued_commands = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(queued_commands[1]['action'], 'configure_netboot')
        self.assertEquals(queued_commands[1]['fqdn'], system.fqdn)
        self.assertEquals(queued_commands[1]['netboot']['arch'], 'i386')
        self.assertEquals(queued_commands[1]['netboot']['distro_tree_id'],
                          distro_tree.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1322235
    def test_s390_configure_netboot_commands_use_ftp_urls(self):
        with session.begin():
            system = data_setup.create_system(arch=u's390x', lab_controller=self.lc)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora23', arch=u's390x',
                    lab_controllers=[self.lc], urls=[
                        u'http://mylabmirror.example.invalid/Fedora23/s390x/',
                        u'ftp://mylabmirror.example.invalid/Fedora23/s390x/',
                    ])
            installation = Installation(distro_tree=distro_tree, system=system,
                    kernel_options=u'', arch=Arch.by_name('s390x'),
                    initrd_path='pxeboot/initrd', kernel_path='pxeboot/vmlinuz')
            system.configure_netboot(installation=installation, service=u'testdata')
        queued_commands = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(queued_commands[1]['action'], 'configure_netboot')
        self.assertEquals(queued_commands[1]['fqdn'], system.fqdn)
        self.assertEquals(queued_commands[1]['netboot']['arch'], 's390x')
        self.assertEquals(queued_commands[1]['netboot']['kernel_url'],
                u'ftp://mylabmirror.example.invalid/Fedora23/s390x/pxeboot/vmlinuz')
        self.assertEquals(queued_commands[1]['netboot']['initrd_url'],
                u'ftp://mylabmirror.example.invalid/Fedora23/s390x/pxeboot/initrd')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1568217
    def test_netboot_parameters_for_pre_beaker_25_recipes(self):
        with session.begin():
            job = data_setup.create_job(arch=u's390x')
            recipe = job.recipesets[0].recipes[0]
            data_setup.mark_recipe_scheduled(recipe, lab_controller=self.lc)
            recipe.provision()
            recipe.waiting()
            # Recipes which were provisioned prior to Beaker 25 but still had 
            # queued commands at the time of the upgrade, will be missing 
            # values for these newer columns.
            recipe.installation.tree_url = None
            recipe.installation.initrd_path = None
            recipe.installation.kernel_path = None
            recipe.installation.distro_name = None
            recipe.installation.osmajor = None
            recipe.installation.osminor = None
            recipe.installation.variant = None
            recipe.installation.arch = None
        queued_commands = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(queued_commands[1]['action'], 'configure_netboot')
        self.assertEquals(queued_commands[1]['netboot']['arch'], 's390x')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1348018
    def test_after_reboot_watchdog_killtime_extended(self):
        with session.begin():
            job = data_setup.create_job()
            recipe = job.recipesets[0].recipes[0]
            system = data_setup.create_system(lab_controller=self.lc)
            data_setup.mark_recipe_scheduled(recipe, system=system)
            recipe.provision()
            recipe.waiting()

        def step_by_one_cmd(cmd, action):
            self.assertEqual(cmd.action, action)
            self.server.labcontrollers.mark_command_running(cmd.id)
            self.server.labcontrollers.mark_command_completed(cmd.id)

        step_by_one_cmd(system.command_queue[3], 'clear_logs')
        with session.begin():
            session.refresh(recipe.watchdog)
            self.assertIsNone(recipe.watchdog.kill_time)

        step_by_one_cmd(system.command_queue[2], 'configure_netboot')
        with session.begin():
            session.refresh(recipe.watchdog)
            self.assertIsNone(recipe.watchdog.kill_time)

        step_by_one_cmd(system.command_queue[1], 'off')
        with session.begin():
            session.refresh(recipe.watchdog)
            self.assertIsNone(recipe.watchdog.kill_time)

        step_by_one_cmd(system.command_queue[0], 'on')

        with session.begin():
            session.refresh(recipe.watchdog)
            self.assertIsNotNone(recipe.watchdog.kill_time)
            assert_datetime_within(
                recipe.watchdog.kill_time,
                tolerance=datetime.timedelta(seconds=10),
                reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=3000))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1366442
    def test_initial_watchdog_killtime_based_on_first_task(self):
        with session.begin():
            long_task = data_setup.create_task(avg_time=604800)
            recipe = data_setup.create_recipe(task_list=[long_task])
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe, lab_controller=self.lc)
            system = recipe.resource.system
            recipe.provision()
            recipe.waiting()
        cmd = system.command_queue[0]
        self.assertEquals(cmd.action, u'on')
        self.server.labcontrollers.mark_command_running(cmd.id)
        self.server.labcontrollers.mark_command_completed(cmd.id)
        with session.begin():
            session.refresh(recipe.watchdog)
            self.assertIsNotNone(recipe.watchdog.kill_time)
            assert_datetime_within(
                    recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow()
                              + datetime.timedelta(seconds=604800 + 1800))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1318524
    def test_start_time_is_recorded(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            system.action_power(u'on')
            command = system.command_queue[0]
        self.server.labcontrollers.mark_command_running(command.id)
        with session.begin():
            session.refresh(command)
            self.assertEquals(command.status, CommandStatus.running)
            assert_datetime_within(command.start_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1318524
    def test_finish_time_is_recorded(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            system.action_power(u'on')
            command = system.command_queue[0]
        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_completed(command.id)
        with session.begin():
            session.refresh(command)
            self.assertEquals(command.status, CommandStatus.completed)
            assert_datetime_within(command.finish_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1318524
    def test_finish_time_is_recorded_for_failures(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            system.action_power(u'on')
            command = system.command_queue[0]
        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id)
        with session.begin():
            session.refresh(command)
            self.assertEquals(command.status, CommandStatus.failed)
            assert_datetime_within(command.finish_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())


    # https://bugzilla.redhat.com/show_bug.cgi?id=1318524
    def test_off_and_on_commands_abort_if_configure_netboot_fails(self):
        system = self.setup_system_with_queued_commands()
        clear_logs = system.command_queue[3]
        configure_netboot = system.command_queue[2]
        off = system.command_queue[1]
        on = system.command_queue[0]
        self.assertEqual('clear_logs', clear_logs.action)
        self.assertEqual('configure_netboot', configure_netboot.action)
        self.assertEqual('off', off.action)
        self.assertEqual('on', on.action)

        self.server.labcontrollers.mark_command_running(clear_logs.id)
        self.server.labcontrollers.mark_command_completed(clear_logs.id)
        self.server.labcontrollers.mark_command_running(configure_netboot.id)
        self.server.labcontrollers.mark_command_failed(configure_netboot.id)

        with session.begin():
            session.expire_all()

            # Check that on and off are marked as aborted
            self.assertEqual(CommandStatus.aborted, off.status)
            self.assertEqual(CommandStatus.aborted, on.status)

            # verify that other commands do not change to aborted
            self.assertEqual(CommandStatus.completed, clear_logs.status)
            self.assertEqual(CommandStatus.failed, configure_netboot.status)


class LabControllerHTTPTest(DatabaseTestCase):

    def setUp(self):
        self.lc_fqdn = u'lab.domain.com'
        with session.begin():
            self.lc_user = data_setup.create_admin(password='theowner')
            self.user_password = '_'
            self.user = data_setup.create_user(password=self.user_password)
            self.lc = data_setup.create_labcontroller(fqdn=self.lc_fqdn,
                                                      user=self.lc_user)

    def test_no_labcontroller(self):
        """Not existing lab controller results in a 404."""
        response = requests.get(
            get_server_base() + 'labcontrollers/doesnotexist',
            headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.text.endswith('does not exist'))

    def test_creates_labcontroller_with_new_user(self):
        """Verify that we can create a new lab controller."""
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        data = {'fqdn': fqdn,
                'user_name': 'mjia',
                'password': '',
                'email_address': 'mjia@beaker-project.org'}
        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)

        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()['id'])
        with session.begin():
            lc = LabController.query.filter_by(fqdn=data['fqdn']).one()
            self.assertEqual(lc.user.user_name, data['user_name'])
            self.assertEqual(lc.user.email_address, data['email_address'])
            self.assertIn(Group.by_name(u'lab_controller'), lc.user.groups)

    def test_creates_labcontroller_with_existing_user(self):
        """Verify that a new lab controller is created with an existing user."""
        with session.begin():
            user_name = 'Frank'
            display_name = 'Beaker Boyz'
            data_setup.create_user(user_name=user_name,
                                   display_name=display_name,
                                   email_address='bbz@beaker-project.org')

        s = requests.Session()
        web_login(s)
        response = post_json(
            get_server_base() + '/labcontrollers/',
            session=s,
            data={'fqdn': 'lc1.beer.newtest',
                  'user_name': user_name,
                  'email_address': 'different@redhat.com',
            })

        self.assertEqual(response.status_code, 201)
        with session.begin():
            lc = LabController.query.filter_by(fqdn='lc1.beer.newtest').one()
            self.assertEqual(lc.user.user_name, user_name)
            # The existing user's display name and email address should be overridden.
            self.assertEqual(lc.user.display_name, lc.fqdn)
            self.assertEqual(lc.user.email_address, 'different@redhat.com' )
            self.assertIn(Group.by_name(u'lab_controller'), lc.user.groups)

    def test_creates_labcontroller_with_existing_labcontroller_user(self):
        """Verifies adding a new lab controller with a user associated to an
        existing lab controller results in an error."""
        s = requests.Session()
        web_login(s)
        data = {'fqdn': 'lc1.beer.newtest',
                'user_name': self.lc.user.user_name}

        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertTrue(re.search('is already associated with lab controller', response.text))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_labcontroller_with_invalid_email_address(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        user_name = data_setup.unique_name('user%s')
        data = {'fqdn': fqdn,
                'user_name': user_name,
                'password': '',
                'email_address': 'asdf'}
        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid email address', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_labcontroller_with_empty_email_address(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        user_name = data_setup.unique_name('user%s')
        data = {'fqdn': fqdn,
                'user_name': user_name,
                'password': '',
                'email_address': ''}
        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email address must not be empty', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_labcontroller_without_email_address(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        data = {'fqdn': fqdn,
                'user_name': data_setup.unique_name('user%s')}

        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email address must not be empty', response.text)

    def test_get_labcontroller_json(self):
        """Can successfully retrieve lab controller details in JSON."""
        response = requests.get(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            headers={'Accept': 'application/json'}
        )
        expected = {
            u'fqdn': self.lc.fqdn,
            u'id': self.lc.id,
            u'disabled': self.lc.disabled,
            u'is_removed': bool(self.lc.removed),
            u'removed': self.lc.removed,
            u'display_name': self.lc.user.display_name,
            u'email_address': self.lc.user.email_address,
            u'user_name': self.lc.user.user_name
        }
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(expected, response.json())

    def test_no_change_with_incorrect_data(self):
        """Lab controllers don't change if different data is passed."""
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'ignored': '_'})
        self.assertEquals(response.status_code, 200)

    def test_no_permission(self):
        """Authorised users with improper permissions can not change the lab
        controller.
        """
        # guard so we can be sure the test does pass because this user got all
        # of a sudden admin rights
        self.assertFalse(self.lc.can_edit(self.user))

        s = requests.Session()
        web_login(s, self.user, password=self.user_password)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'user_name': self.user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(re.search('Cannot edit lab controller', response.text))

    def test_renames_successfully(self):
        """Renames the lab controller successfully."""
        data = {'fqdn': data_setup.unique_name('lc%s.com'),
                'user_name': self.lc.user.user_name,
                'email_address': self.lc.user.email_address}

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn, session=s, data=data)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['fqdn'], data['fqdn'])
        self.assertEqual(get_server_base() + 'labcontrollers/%s' % data['fqdn'],
                         response.headers['Location'])
        with session.begin():
            lc = LabController.by_name(data['fqdn'])
            self.assertRaises(NoResultFound, LabController.by_name, self.lc.fqdn)
            session.refresh(lc.user)
            self.assertEqual(self.lc.user.display_name, data['fqdn'])
            self.assertTrue(lc)

    def test_renames_duplicated_labcontroller_errors(self):
        """Verify that we get a useful error message if we rename to an
        existing lab controller."""
        with session.begin():
            lc = data_setup.create_labcontroller()

        s = requests.Session()
        web_login(s)
        response = patch_json(get_server_base() + 'labcontrollers/' + self.lc.fqdn,
                              session=s,
                              data={'fqdn': lc.fqdn})

        self.assertEqual(response.status_code, 400)
        self.assertRegexpMatches(
            response.text,
            re.compile(r'FQDN %s already in use' % lc.fqdn)
        )

    def test_disables_labcontroller_successfully(self):
        with session.begin():
            session.refresh(self.lc)
            self.assertFalse(self.lc.disabled)

        s = requests.Session()
        web_login(s)
        response = patch_json(get_server_base() + 'labcontrollers/' + self.lc.fqdn,
                              session=s,
                              data={'disabled': True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['disabled'])

        with session.begin():
            session.refresh(self.lc)
            self.assertTrue(self.lc.disabled)
            self.assertEqual(self.lc.activity[0].action, 'Changed')
            self.assertEqual(self.lc.activity[0].field_name, 'disabled')

    def test_changes_user_successfully(self):
        """Changes the lab controller credentials successfully."""
        with session.begin():
            group = Group.by_name('lab_controller')
            self.assertNotIn(group, self.user.groups)

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'user_name': self.user.user_name})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            for obj in [self.lc, self.user, group]:
                session.refresh(obj)

            self.assertDictEqual({
                'id': self.lc.id,
                'fqdn': self.lc.fqdn,
                'disabled': self.lc.disabled,
                'is_removed': bool(self.lc.removed),
                'removed': self.lc.removed,
                'display_name': self.lc.fqdn,
                'email_address': self.user.email_address,
                'user_name': self.user.user_name,
            }, response.json())
            self.assertEqual(self.lc.fqdn, self.user.display_name)
            self.assertIn(group, self.lc.user.groups)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1339034
    def test_update_password(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'password': u'newpassword'})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            session.expire_all()
            self.assertTrue(self.lc.user.check_password(u'newpassword'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1339034
    def test_update_email_address(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'email_address': u'new_email_address@beaker-project.org'})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            session.expire_all()
            self.assertEquals(self.lc.user.email_address, u'new_email_address@beaker-project.org')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1339034
    def test_changes_user_and_fqdn_successfully(self):
        """Changes the lab controller credentials and FQDN at the same time successfully."""
        with session.begin():
            fqdn = data_setup.unique_name('lc%s.com')
            user = data_setup.create_user()
            group = Group.by_name('lab_controller')
            self.assertNotIn(group, user.groups)

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'fqdn': fqdn,
                  'user_name': user.user_name})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            for obj in [self.lc, user, group]:
                session.refresh(obj)

            self.assertDictEqual({
                'id': self.lc.id,
                'fqdn': fqdn,
                'disabled': self.lc.disabled,
                'is_removed': bool(self.lc.removed),
                'removed': self.lc.removed,
                'display_name': fqdn,
                'email_address': user.email_address,
                'user_name': user.user_name,
            }, response.json())
            self.assertEqual(self.lc.fqdn, user.display_name)
            self.assertIn(group, self.lc.user.groups)

    def test_removed_labcontroller_can_be_restored(self):
        """Verifies that a removed lab controller can be restored."""
        with session.begin():
            self.lc.disabled = True
            self.lc.removed = datetime.datetime.utcnow()

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + '/labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'removed': False})

        self.assertEquals(response.status_code, 200)

        with session.begin():
            session.expire_all()
            self.assertFalse(self.lc.disabled)
            self.assertIsNone(self.lc.removed)

    def test_update_labcontroller_with_empty_fqdn(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'fqdn': u''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Lab controller FQDN must not be empty', response.text)

    def test_update_labcontroller_with_invalid_fqdn(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'fqdn': u'invalid_lc_fqdn'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid FQDN for lab controller', response.text)

    # backwards compatibility
    # remove me once https://bugzilla.redhat.com/show_bug.cgi?id=1211119 is fixed
    def test_save_creates_labcontroller(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        data = {'fqdn': fqdn,
                'lusername': 'host/dev-kvm',
                'lpassword': 'testing',
                'email': 'root@dev-kvm.org'}
        response = s.post(
            get_server_base() + '/labcontrollers/save', data=data)

        self.assertEqual(response.status_code, 201)
        with session.begin():
            lc = LabController.query.filter_by(fqdn=data['fqdn']).one()
            self.assertEqual(lc.user.user_name, data['lusername'])
            self.assertEqual(lc.user.email_address, data['email'])
