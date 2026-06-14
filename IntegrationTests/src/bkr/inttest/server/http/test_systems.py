# vim: set fileencoding=utf-8:

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import uuid
import requests
from six import text_type
from bkr.server.database import session
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.server.model import Cpu, Job, Disk, SystemPermission
from bkr.inttest.server.requests_utils import patch_json, login as requests_login


class IpxeScriptHTTPTest(DatabaseTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller(fqdn='lab.ipxescript.httptest')

    def test_unknown_uuid(self):
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % uuid.uuid4())
        self.assertEqual(response.status_code, 404)

    def test_invalid_uuid(self):
        response = requests.get(get_server_base() +
                'systems/by-uuid/blerg/ipxe-script')
        self.assertEqual(response.status_code, 404)

    def test_recipe_not_provisioned_yet(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe, virt=True, lab_controller=self.lc)
            # VM is created but recipe.provision() hasn't been called yet
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        self.assertEqual(response.status_code, 503)

    def test_lab_incompatible_URLs(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(
                arch=u'x86_64', osmajor=u'Fedora20',
                lab_controllers=[self.lc],
                urls=[u'nfs://example.nfs.test:/path/to/os'])
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        self.assertEqual(response.status_code, 404)
        self.assertMultiLineEqual(
            response.text,
            'Lab lab.ipxescript.httptest does not provide HTTP or FTP URLs for distro tree: %s'
            % distro_tree.id)

    def test_recipe_provision_with_custom_distro(self):
        with session.begin():
            recipe = data_setup.create_recipe(custom_distro=True)
            self.assertIsNone(recipe.distro_tree)
            recipe.installation.tree_url = 'http://mydistro.dummylab.test/os/'
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        response.raise_for_status()
        self.assertMultiLineEqual(response.text, """#!ipxe
kernel http://mydistro.dummylab.test/os/pxeboot/vmlinuz console=tty0 console=ttyS0,115200n8 inst.ks=%s noverifyssl netboot_method=ipxe
initrd http://mydistro.dummylab.test/os/pxeboot/initrd
boot
""" % recipe.installation.rendered_kickstart.link)  # noqa: E501

    def test_recipe_provision_with_custom_distro_and_incompatible_url(self):
        with session.begin():
            recipe = data_setup.create_recipe(custom_distro=True)
            self.assertIsNone(recipe.distro_tree)
            recipe.installation.tree_url = 'nfs://mydistro.dummylab.test:/os/'
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        self.assertEqual(response.status_code, 404)
        self.assertMultiLineEqual(
            response.text,
            'Given tree URL nfs://mydistro.dummylab.test:/os/ incompatible with iPXE')

    def test_recipe_provisioned(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(
                    arch=u'x86_64', osmajor=u'Fedora20',
                    lab_controllers=[self.lc],
                    urls=[u'nfs://example.nfs.test:/path/to/os',
                          u'http://example.com/ipxe-test/F20/x86_64/os/'])
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        response.raise_for_status()
        self.assertEqual(response.text, """#!ipxe
kernel http://example.com/ipxe-test/F20/x86_64/os/pxeboot/vmlinuz console=tty0 console=ttyS0,115200n8 ks=%s ksdevice=bootif noverifyssl netboot_method=ipxe
initrd http://example.com/ipxe-test/F20/x86_64/os/pxeboot/initrd
boot
""" % recipe.installation.rendered_kickstart.link)  # noqa: E501

class SystemHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for systems: /systems/<fqdn>.

    Note that other system-related HTTP APIs are tested elsewhere
    (e.g. /systems/<fqdn>/commands/ in test_system_commands.py).
    """
    maxDiff = None

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.lab_controller = data_setup.create_labcontroller()
            self.system = data_setup.create_system(owner=self.owner, shared=False,
                    lab_controller=self.lab_controller)
            self.policy = self.system.custom_access_policy
            self.policy.add_rule(everybody=True, permission=SystemPermission.reserve)
            self.privileged_group = data_setup.create_group()
            self.policy.add_rule(group=self.privileged_group,
                                 permission=SystemPermission.edit_system)

    def test_get_system(self):
        response = requests.get(get_server_base() + '/systems/%s/' % self.system.fqdn,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['fqdn'], self.system.fqdn)

    def test_get_system_with_running_hardware_scan_recipe(self):
        # The bug was a circular reference from system -> recipe -> system
        # which caused JSON serialization to fail.
        with session.begin():
            Job.inventory_system_job(data_setup.create_distro_tree(),
                    owner=self.owner, system=self.system)
            recipe = self.system.find_current_hardware_scan_recipe()
            data_setup.mark_recipe_running(recipe, system=self.system)
        response = requests.get(get_server_base() + '/systems/%s/' % self.system.fqdn,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        in_progress_scan = response.json()['in_progress_scan']
        self.assertEqual(in_progress_scan['recipe_id'], recipe.id)
        self.assertEqual(in_progress_scan['status'], u'Running')
        self.assertEqual(in_progress_scan['job_id'], recipe.recipeset.job.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1386074
    def test_get_system_returns_correct_id(self):
        # The bug was that Power.id was overwriting System.id.
        with session.begin():
            # The bug is not observable if the system and power rows both
            # happen to have the same id, which is likely in the test suite
            # since we always create system and power rows together. Create
            # a throwaway system row without power, to ensure the autoincrement
            # ids are not in sync.
            data_setup.create_system(with_power=False)
            system = data_setup.create_system(owner=self.owner)
            self.assertNotEqual(system.id, system.power.id)
            # The bug is only observable to users with access to view power settings.
            self.assertTrue(system.can_view_power(self.owner))
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        response = s.get(get_server_base() + '/systems/%s/' % system.fqdn,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['id'], system.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1386074
    def test_updating_power_returns_correct_id(self):
        # The bug was that Power.id was overwriting System.id
        with session.begin():
            system = data_setup.create_system(with_power=False, owner=self.owner)
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'power_type': 'ilo', 'power_address': 'nowhere'})
        response.raise_for_status()
        self.assertEqual(response.json()['id'], system.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206033
    def test_system_details_includes_disks(self):
        with session.begin():
            disk = Disk(model='Seagate Old', size=1024, sector_size=512, phys_sector_size=512)
            session.add(disk)
            self.system.disks.append(disk)

        expected = [{
            u'phys_sector_size': disk.phys_sector_size,
            u'sector_size': disk.sector_size,
            u'size': disk.size,
            u'model': disk.model,
        }]

        response = requests.get(
            get_server_base() + 'systems/%s' % self.system.fqdn)

        self.assertIn('disks', response.json())
        self.assertEqual(expected, response.json()['disks'])

    def test_set_active_policy_from_pool(self):
        with session.begin():
            user = data_setup.create_user()
            pool = data_setup.create_system_pool()
            pool.systems.append(self.system)
            pool.access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user)

        with session.begin():
            self.assertFalse(self.system.active_access_policy.grants
                             (user, SystemPermission.edit_system))

        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password='theowner')
        response = patch_json(get_server_base() +
                              'systems/%s/' % self.system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
                         )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.active_access_policy.grants
                            (user, SystemPermission.edit_system))

        # attempt to set active policy to a pool policy when the system
        # is not in the pool
        with session.begin():
            pool = data_setup.create_system_pool()
            session.expire_all()
        response = patch_json(get_server_base() +
                              'systems/%s/' % self.system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
                        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                          'To use a pool policy, the system must be in the pool first')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206034
    def test_system_details_includes_cpus(self):
        with session.begin():
            cpu = Cpu(cores=5,
                      family=6,
                      model=7,
                      model_name='Intel',
                      flags=['beer', 'frob'],
                      processors=6,
                      sockets=2,
                      speed=24,
                      stepping=2,
                      vendor='Transmeta')
            session.add(cpu)
            self.system.cpu = cpu

        response = requests.get(
            get_server_base() + 'systems/%s' % self.system.fqdn)
        json = response.json()
        self.assertEqual([u'beer', u'frob'], json['cpu_flags'])
        self.assertEqual(5, json['cpu_cores'])
        self.assertEqual(6, json['cpu_family'])
        self.assertEqual(7, json['cpu_model'])
        self.assertEqual(u'Intel', json['cpu_model_name'])
        self.assertEqual(True, json['cpu_hyper'])
        self.assertEqual(6, json['cpu_processors'])
        self.assertEqual(2, json['cpu_sockets'])
        self.assertEqual(24, json['cpu_speed'])
        self.assertEqual(2, json['cpu_stepping'])
        self.assertEqual('Transmeta', json['cpu_vendor'])

    def test_set_active_policy_to_custom_policy(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            self.system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user1)
            pool = data_setup.create_system_pool()
            pool.access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user2)
            self.system.active_access_policy = pool.access_policy

        self.assertFalse(self.system.active_access_policy.grants
                        (user1, SystemPermission.edit_system))
        self.assertTrue(self.system.active_access_policy.grants
                         (user2, SystemPermission.edit_system))

        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password='theowner')
        response = patch_json(get_server_base() +
                              'systems/%s/' % self.system.fqdn, session=s,
                              data={'active_access_policy': {'custom': True}},
                         )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.active_access_policy.grants \
                            (user1, SystemPermission.edit_system))

    # https://bugzilla.redhat.com/show_bug.cgi?id=980352
    def test_condition_report_length_is_enforced(self):
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password='theowner')
        response = patch_json(get_server_base() + 'systems/%s/' % self.system.fqdn,
                session=s, data={'status': 'Broken', 'status_reason': 'reallylong' * 500})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'System condition report is longer than 4000 characters')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_can_update_active_access_policy_with_edit_policy_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_policy, user=user)
            pool = data_setup.create_system_pool(systems=[system])
        s = requests.Session()
        requests_login(s, user=user.user_name, password='password')
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(system.active_access_policy, pool.access_policy)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_cannot_update_active_access_policy_with_edit_system_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user)
            pool = data_setup.create_system_pool(systems=[system])
        s = requests.Session()
        requests_login(s, user=user.user_name, password='password')
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot edit system access policy', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_cannot_update_system_details_with_edit_policy_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_policy, user=user)
        s = requests.Session()
        requests_login(s, user=user.user_name, password='password')
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'fqdn': u'newfqdn'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot edit system', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_records_activity_on_changing_access_policy(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            pool.systems.append(system)
        # change the system active access policy to pool access policy
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy, pool.access_policy)
            self.assertEqual(system.activity[-1].field_name, 'Active Access Policy')
            self.assertEqual(system.activity[-1].action, 'Changed')
            self.assertEqual(system.activity[-1].old_value, 'Custom access policy')
            self.assertEqual(system.activity[-1].new_value, 'Pool policy: %s' % text_type(pool))
        # change the system active access policy back to custom access policy
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'custom': True}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy, system.custom_access_policy)
            self.assertEqual(system.activity[-2].field_name, 'Active Access Policy')
            self.assertEqual(system.activity[-2].action, 'Changed')
            self.assertEqual(system.activity[-2].old_value, 'Pool policy: %s' % text_type(pool))
            self.assertEqual(system.activity[-2].new_value, 'Custom access policy')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_updating_access_policy_with_no_change_should_not_record_activity(self):
        with session.begin():
            system = data_setup.create_system()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'custom': True}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy, system.custom_access_policy)
            self.assertEqual(system.activity, [])

    #  https://bugzilla.redhat.com/show_bug.cgi?id=1323885
    def test_update_lab_controller_with_lab_controller_object(self):
        with session.begin():
            system = data_setup.create_system()
            lc = data_setup.create_labcontroller()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'lab_controller': {'fqdn': lc.fqdn}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.lab_controller, lc)
            self.assertEqual(system.activity[-1].field_name, 'Lab Controller')
            self.assertEqual(system.activity[-1].action, 'Changed')
            self.assertEqual(system.activity[-1].old_value, None)
            self.assertEqual(system.activity[-1].new_value, lc.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1387109
    def test_can_set_zero_quiescent_period(self):
        with session.begin():
            system = data_setup.create_system()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'power_quiescent_period': 0})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(system.power.power_quiescent_period, 0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_give_to_deleted_user(self):
        with session.begin():
            system = data_setup.create_system()
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'owner': {'user_name': deleted_user.user_name}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot change owner to deleted user %s' % deleted_user.user_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1591391
    def test_system_owner_username_is_truncated(self):
        with session.begin():
            system = data_setup.create_system()
            max_new_value_length = 60
            long_username = 'z' * max_new_value_length + 's'
            user_with_long_username = data_setup.create_user(user_name=long_username)
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'owner': {'user_name': user_with_long_username.user_name}})
        self.assertEqual(response.status_code, 200)
        with session.begin():
            self.assertEqual(system.activity[0].field_name, u'Owner')
            self.assertEqual(system.activity[0].action, u'Changed')
            self.assertEqual(system.activity[0].new_value, u'z' * max_new_value_length)
