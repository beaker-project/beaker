
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import datetime
from threading import Thread, Event
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, XmlRpcTestCase, \
    WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_activity_row_present
from bkr.inttest import data_setup, get_server_base, fix_beakerd_repodata_perms
from bkr.server.model import Distro, DistroTree, Arch, ImageType, Job, \
        System, SystemStatus, TaskStatus, CommandActivity, CommandStatus, \
        KernelType, LabController, Recipe, Activity, User, OSMajor, OSVersion
from bkr.server.tools import beakerd
from bkr.server.wsgi import app
from bkr.server import identity
from bkr.inttest.server.selenium.test_activity import is_activity_row_present

class LabControllerViewTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def _add_lc(self, lc_name, lc_email):
        b = self.browser
        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys(lc_name)
        b.find_element_by_name('email').send_keys(lc_email)
        b.find_element_by_name('lusername').send_keys('host/' + lc_name)
        b.find_element_by_id('form').submit()

    def test_lab_controller_add(self):
        b = self.browser
        lc_name = data_setup.unique_name('lc%s.com')
        lc_email = data_setup.unique_name('me@my%s.com')
        self._add_lc(lc_name, lc_email)
        self.assert_('%s saved' % lc_name in
            b.find_element_by_css_selector('.flash').text)

        # Search in activity
        b.get(get_server_base() + 'activity/labcontroller')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/"
            "option[@value='LabController/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']"). \
            send_keys(lc_name)
        b.find_element_by_id('searchform').submit()

        self.assert_(is_activity_row_present(b,
            object_='LabController: %s' % lc_name, via='WEBUI',
            property_='FQDN', action='Changed', new_value=lc_name))
        self.assert_(is_activity_row_present(b,
            object_='LabController: %s' % lc_name, via='WEBUI',
            property_='User', action='Changed',
            new_value='host/' + lc_name))
        self.assert_(is_activity_row_present(b,
            object_='LabController: %s' % lc_name, via='WEBUI',
            property_='Disabled', action='Changed', new_value='False'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=998374
    # https://bugzilla.redhat.com/show_bug.cgi?id=1064710
    def test_cannot_add_duplicate_lc(self):
        with session.begin():
            existing_lc = data_setup.create_labcontroller()
        self._add_lc(existing_lc.fqdn, existing_lc.user.email_address)
        b = self.browser
        self.assertEquals(b.find_element_by_xpath(
                '//input[@name="fqdn"]/following-sibling::span').text,
                'FQDN is not unique')
        self.assertEquals(b.find_element_by_xpath(
                '//input[@name="lusername"]/following-sibling::span').text,
                'Username is in use by a different lab controller')

    # https://bugzilla.redhat.com/show_bug.cgi?id=998374
    def test_cannot_change_fqdn_to_duplicate(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            other_lc = data_setup.create_labcontroller()
        b = self.browser
        b.get(get_server_base() + 'labcontrollers/edit?id=%s' % lc.id)
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys(other_lc.fqdn)
        b.find_element_by_id('form').submit()
        self.assertEquals(b.find_element_by_xpath(
                '//input[@name="fqdn"]/following-sibling::span').text,
                'FQDN is not unique')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1064710
    def test_cannot_change_username_to_duplicate(self):
        # Changing an LC's username to an existing user account is okay, but 
        # you can't change it to a user account that is already being used by 
        # another LC.
        with session.begin():
            lc = data_setup.create_labcontroller()
            other_lc = data_setup.create_labcontroller()
        b = self.browser
        b.get(get_server_base() + 'labcontrollers/edit?id=%s' % lc.id)
        b.find_element_by_name('lusername').clear()
        b.find_element_by_name('lusername').send_keys(other_lc.user.user_name)
        b.find_element_by_id('form').submit()
        self.assertEquals(b.find_element_by_xpath(
                '//input[@name="lusername"]/following-sibling::span').text,
                'Username is in use by a different lab controller')

    def test_lab_controller_remove(self):
        b = self.browser
        lc_name = data_setup.unique_name('lc%s.com')
        lc_email = data_setup.unique_name('me@my%s.com')
        self._add_lc(lc_name, lc_email)
        with session.begin():
            sys = data_setup.create_system()
            sys.lab_controller = LabController.by_name(lc_name)
        b.get(get_server_base() + 'labcontrollers')
        b.find_element_by_xpath("//table[@id='widget']/tbody/tr/"
            "td[preceding-sibling::td/a[normalize-space(text())='%s']]"
            "/a[normalize-space(text())='Remove']" % lc_name).click()
        self.assert_('%s removed' % lc_name in
            b.find_element_by_css_selector('.flash').text)

        # Search in  LC activity
        b.get(get_server_base() + 'activity/labcontroller')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/"
            "option[@value='LabController/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']"). \
            send_keys(lc_name)
        b.find_element_by_id('searchform').submit()
        self.assert_(is_activity_row_present(b,
            object_='LabController: %s' % lc_name, via='WEBUI',
            property_='Disabled', action='Changed', new_value='True'))
        self.assert_(is_activity_row_present(b,
            object_='LabController: %s' % lc_name, via='WEBUI',
            property_='Removed', action='Changed', new_value='True'))

        # Ensure System Actvity has been updated to note removal of LC
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/"
            "option[@value='System/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']"). \
            send_keys(sys.fqdn)
        b.find_element_by_id('searchform').submit()
        self.assert_(is_activity_row_present(b,
            object_='System: %s' % sys.fqdn, via='WEBUI',
            property_='lab_controller', action='Changed', new_value=''))


class AddDistroTreeXmlRpcTest(XmlRpcTestCase):

    distro_data = dict(
            name='RHEL-6-U1',
            arches=['i386', 'x86_64'], arch='x86_64',
            osmajor='RedHatEnterpriseLinux6', osminor='1',
            variant='Workstation', tree_build_time=1305067998.6483951,
            urls=['nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/',
                  'http://example.invalid/RHEL-6-Workstation/U1/x86_64/os/'],
            repos=[
                dict(repoid='Workstation', type='os', path=''),
                dict(repoid='ScalableFileSystem', type='addon', path='ScalableFileSystem/'),
                dict(repoid='optional', type='addon', path='../../optional/x86_64/os/'),
                dict(repoid='debuginfo', type='debug', path='../debug/'),
            ],
            images=[
                dict(type='kernel', path='images/pxeboot/vmlinuz'),
                dict(type='initrd', path='images/pxeboot/initrd.img'),
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
                    'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
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
                    'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
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
            'nfs+iso://example.invalid:/RHEL-6-Workstation/U1/x86_64/iso/',
            'http://moved/',
        ]
        self.server.labcontrollers.add_distro_tree(new_distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs'),
                    'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs+iso'),
                    'nfs+iso://example.invalid:/RHEL-6-Workstation/U1/x86_64/iso/')
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='http'),
                    'http://moved/')
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

    def test_obeys_max_running_commands_limit(self):
        with session.begin():
            for _ in xrange(15):
                system = data_setup.create_system(lab_controller=self.lc)
                system.action_power(action=u'on', service=u'testdata')
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        commands = self.server.labcontrollers.get_queued_command_details()
        # 10 is the configured limit in server-test.cfg
        self.assertEquals(len(commands), 10, commands)

    def test_clear_running_commands(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            command = CommandActivity(
                    user=None, service=u'testdata', action=u'on',
                    status=CommandStatus.running)
            system.command_queue.append(command)
            other_system = data_setup.create_system()
            other_command = CommandActivity(
                    user=None, service=u'testdata', action=u'on',
                    status=CommandStatus.running)
            other_system.command_queue.append(other_command)
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.clear_running_commands(u'Staleness')
        with session.begin():
            session.refresh(command)
            self.assertEquals(command.status, CommandStatus.aborted)
            self.assertEquals(other_command.status, CommandStatus.running)

    def test_purge_stale_running_commands(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            # Helper to build the commands
            def _make_command(lc=None, creation_date=None):
                job = data_setup.create_job(distro_tree=distro_tree)
                recipe = job.recipesets[0].recipes[0]
                system = data_setup.create_system(lab_controller=lc)
                data_setup.mark_recipe_waiting(recipe, system=system)
                command = CommandActivity(
                        user=None, service=u'testdata', action=u'on',
                        status=CommandStatus.running,
                        callback=u'bkr.server.model.auto_cmd_handler')
                if creation_date is not None:
                    command.created = command.updated = creation_date
                system.command_queue.append(command)
                return recipe.tasks[0], command
            # Normal command for the current LC
            recent_task, recent_command = _make_command(lc=self.lc)
            # Old command for a different LC
            backdated = datetime.datetime.utcnow()
            backdated -= datetime.timedelta(days=1, minutes=1)
            old_task, old_command = _make_command(creation_date=backdated)

        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
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
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        queued = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(len(queued), 0, queued)
        expected = u'Arbitrary command!'
        self.server.labcontrollers.add_completed_command(fqdn, expected)
        queued = self.server.labcontrollers.get_queued_command_details()
        self.assertEquals(len(queued), 0, queued)
        with session.begin():
            completed = list(CommandActivity.query
                             .join(CommandActivity.system)
                             .filter(System.fqdn == fqdn))
            self.assertEquals(len(completed), 1, completed)
            self.assertEquals(completed[0].action, expected)



class TestPowerFailures(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.lab_controller.user.password = u'logmein'
        self.server = self.get_server()
        self.server.auth.login_password(self.lab_controller.user.user_name,
                u'logmein')

    @classmethod
    def tearDownClass(cls):
        fix_beakerd_repodata_perms()

    def test_automated_system_marked_broken(self):
        with session.begin():
            automated_system = data_setup.create_system(fqdn=u'broken1.example.org',
                                                        lab_controller=self.lab_controller,
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=720672
    def test_manual_system_status_not_changed(self):
        with session.begin():
            manual_system = data_setup.create_system(fqdn = u'broken2.example.org',
                                                     lab_controller = self.lab_controller,
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
            system = data_setup.create_system(fqdn = u'broken.dreams.example.org',
                                              lab_controller = self.lab_controller,
                                              status = SystemStatus.automated,
                                              shared = True)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            command = system.command_queue[0]
            self.assertEquals(command.action, 'on')

        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')
        with session.begin():
            job = Job.query.get(job.id)
            job.update_status()
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.aborted)

    def test_failure_in_configure_netboot_aborts_recipe(self):
        with session.begin():
            system = data_setup.create_system(
                    lab_controller=self.lab_controller,
                    status=SystemStatus.automated, shared=True)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            command = system.command_queue[2]
            self.assertEquals(command.action, 'configure_netboot')

        self.server.labcontrollers.mark_command_running(command.id)
        self.server.labcontrollers.mark_command_failed(command.id,
                u'oops it borked')
        with session.begin():
            job = Job.query.get(job.id)
            job.update_status()
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.aborted)
