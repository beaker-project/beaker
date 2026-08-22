# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
import lxml.etree
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as requests_login, \
        patch_json, post_json
from bkr.server.database import session
from bkr.server.model import RecipeSetComment, TaskPriority, TaskStatus


class SystemUpdateInventoryHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for updating system inventory
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.lc = data_setup.create_labcontroller()
            self.system1 = data_setup.create_system(owner=self.owner,
                                                    arch=[u'i386', u'x86_64'])
            self.system1.lab_controller = self.lc
            self.distro_tree1 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])

    def test_submit_inventory_job(self):
        s = requests.Session()
        response = s.post(get_server_base() + 'jobs/+inventory')
        self.assertEqual(response.status_code, 401)
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        response = post_json(get_server_base() + 'jobs/+inventory',
                             session=s,
                             data={'fqdn': self.system1.fqdn})
        response.raise_for_status()
        self.assertIn('recipe_id', response.text)

        # Non-existent system
        response = post_json(get_server_base() + 'jobs/+inventory',
                             session=s,
                             data={'fqdn': 'i.donotexist.name'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('System not found: i.donotexist.name', response.text)


class JobHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by the job page.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.job = data_setup.create_job(owner=self.owner,
                                             retention_tag=u'scratch')

    def test_get_job(self):
        response = requests.get(get_server_base() + 'jobs/%s' % self.job.id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['id'], self.job.id)
        self.assertEqual(json['owner']['user_name'], self.owner.user_name)

    def test_get_job_which_does_not_have_submitter(self):
        # A job may not have a submitter prior to Beaker 14.
        # In this case, it should return the owner as the submitter.
        with session.begin():
            job = data_setup.create_job(owner=self.owner)
            job.submitter = None
        response = requests.get(get_server_base() + 'jobs/%s' % job.id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['id'], job.id)
        self.assertEqual(json['submitter']['user_name'], self.owner.user_name)

    def test_get_job_xml(self):
        response = requests.get(get_server_base() + 'jobs/%s.xml' % self.job.id)
        response.raise_for_status()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            lxml.etree.tostring(self.job.to_xml(), pretty_print=True, encoding='utf8'),
            response.content)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319#c6
    def test_get_job_xml_without_logs(self):
        response = requests.get(get_server_base() + 'jobs/%s.xml?include_logs=false' % self.job.id)
        response.raise_for_status()
        self.assertNotIn('<log', response.text)

    def test_get_junit_xml(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        response = requests.get(get_server_base() + 'jobs/%s.junit.xml' % self.job.id)
        response.raise_for_status()
        self.assertEqual(response.status_code, 200)
        junitxml = lxml.etree.fromstring(response.content)
        self.assertEqual(junitxml.tag, 'testsuites')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1169838
    def test_trailing_slash_should_return_404(self):
        response = requests.get(get_server_base() + 'jobs/%s/' % self.job.id)
        self.assertEqual(response.status_code, 404)

    def test_set_job_whiteboard(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'jobs/%s' % self.job.id,
                              session=s, data={'whiteboard': 'newwhiteboard'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.whiteboard, 'newwhiteboard')
            self.assertEqual(self.job.activity[0].field_name, u'Whiteboard')
            self.assertEqual(self.job.activity[0].action, u'Changed')
            self.assertEqual(self.job.activity[0].new_value, u'newwhiteboard')

    def test_set_retention_tag_and_product(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=True)
            product = data_setup.create_product()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': product.name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.retention_tag, retention_tag)
            self.assertEqual(self.job.product, product)
            self.assertEqual(self.job.activity[0].field_name, u'Product')
            self.assertEqual(self.job.activity[0].action, u'Changed')
            self.assertEqual(self.job.activity[0].old_value, None)
            self.assertEqual(self.job.activity[0].new_value, product.name)
            self.assertEqual(self.job.activity[1].field_name, u'Retention Tag')
            self.assertEqual(self.job.activity[1].action, u'Changed')
            self.assertEqual(self.job.activity[1].old_value, u'scratch')
            self.assertEqual(self.job.activity[1].new_value, retention_tag.tag)

    def test_cannot_set_product_if_retention_tag_does_not_need_one(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=False)
            product = data_setup.create_product()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': product.name})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            'Cannot change retention tag as it does not support a product',
            response.text)
        # Same thing, but the retention tag is already set and we are just setting the product.
        with session.begin():
            self.job.retention_tag = retention_tag
        response = patch_json(get_server_base() + 'jobs/%s' % self.job.id,
                              session=s, data={'product': product.name})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            'Cannot change product as the current retention tag does not support a product',
            response.text)

    def test_set_retention_tag_without_product(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=False)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.retention_tag, retention_tag)
            self.assertEqual(self.job.product, None)
            self.assertEqual(self.job.activity[0].field_name, u'Retention Tag')
            self.assertEqual(self.job.activity[0].action, u'Changed')
            self.assertEqual(self.job.activity[0].old_value, u'scratch')
            self.assertEqual(self.job.activity[0].new_value, retention_tag.tag)
        # Same thing, but with {product: null} which is equivalent.
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': None})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.retention_tag, retention_tag)
            self.assertEqual(self.job.product, None)

    def test_set_retention_tag_clearing_product(self):
        # The difference here compared with the test case above is that in this
        # case, the job already has a retention tag and a product set, we are
        # changing it to a different retention tag which requires the product
        # to be cleared.
        with session.begin():
            old_retention_tag = data_setup.create_retention_tag(needs_product=True)
            self.job.retention_tag = old_retention_tag
            self.job.product = data_setup.create_product()
            retention_tag = data_setup.create_retention_tag(needs_product=False)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': None})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.retention_tag, retention_tag)
            self.assertEqual(self.job.product, None)
            self.assertEqual(self.job.activity[0].field_name, u'Product')
            self.assertEqual(self.job.activity[0].action, u'Changed')
            self.assertEqual(self.job.activity[0].new_value, None)
            self.assertEqual(self.job.activity[1].field_name, u'Retention Tag')
            self.assertEqual(self.job.activity[1].action, u'Changed')
            self.assertEqual(self.job.activity[1].old_value, old_retention_tag.tag)
            self.assertEqual(self.job.activity[1].new_value, retention_tag.tag)

    def test_cannot_set_retention_tag_without_product_if_tag_needs_one(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=True)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            'Cannot change retention tag as it requires a product',
            response.text)
        # Same thing, but with {product: null} which is equivalent.
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'retention_tag': retention_tag.tag, 'product': None})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            'Cannot change retention tag as it requires a product',
            response.text)

    def test_set_product(self):
        with session.begin():
            retention_tag = data_setup.create_retention_tag(needs_product=True)
            product = data_setup.create_product()
            self.job.retention_tag = retention_tag
            self.job.product = product
            other_product = data_setup.create_product()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'product': other_product.name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.product, other_product)
            self.assertEqual(self.job.activity[0].field_name, u'Product')
            self.assertEqual(self.job.activity[0].action, u'Changed')
            self.assertEqual(self.job.activity[0].old_value, product.name)
            self.assertEqual(self.job.activity[0].new_value, other_product.name)

    def test_set_cc(self):
        with session.begin():
            self.job.cc = [u'capn-crunch@example.com']
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'jobs/%s' % self.job.id, session=s,
                              data={'cc': ['captain-planet@example.com']})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.job.cc, ['captain-planet@example.com'])
            self.assertEqual(self.job.activity[0].field_name, u'Cc')
            self.assertEqual(self.job.activity[0].action, u'Removed')
            self.assertEqual(self.job.activity[0].old_value, u'capn-crunch@example.com')
            self.assertEqual(self.job.activity[1].field_name, u'Cc')
            self.assertEqual(self.job.activity[1].action, u'Added')
            self.assertEqual(self.job.activity[1].new_value, u'captain-planet@example.com')

    def test_invalid_email_address_in_cc_is_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'jobs/%s' % self.job.id,
                              session=s, data={'cc': ['bork;one1']})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            'Invalid email address %s in cc: '
            'An email address must contain a single @' % repr(u'bork;one1'),
            response.text)

    def test_other_users_cannot_delete_job(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        self.assertEqual(response.status_code, 403)
        self.assertEqual('Insufficient permissions: Cannot delete job', response.text)

    def test_delete_job(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.job.is_deleted)

    def test_cannot_delete_running_job(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('Cannot delete running job', response.text)

    def test_cannot_delete_already_deleted_job(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
            self.job.deleted = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = s.delete(get_server_base() + 'jobs/%s' % self.job.id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual('Job has already been deleted', response.text)

    def test_anonymous_cannot_update_status(self):
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             data={'status': u'Cancelled'})
        self.assertEqual(response.status_code, 401)

    def test_other_users_cannot_update_status(self):
        with session.begin():
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEqual(response.status_code, 403)

    def test_submission_delegate_cannot_update_status(self):
        # N.B. submission delegate but *not* submitter
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEqual(response.status_code, 403)

    def test_cancel_job(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.job.update_status()
            self.assertEqual(self.job.status, TaskStatus.cancelled)
            # https://bugzilla.redhat.com/show_bug.cgi?id=995012
            self.assertEqual(self.job.activity[0].field_name, u'Status')
            self.assertEqual(self.job.activity[0].action, u'Cancelled')

    def test_submitter_can_cancel(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
            self.job.submitter = submission_delegate
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    def test_group_member_can_cancel_group_job(self):
        with session.begin():
            other_member = data_setup.create_user(password='other')
            group = data_setup.create_group()
            group.add_member(self.job.owner)
            group.add_member(other_member)
            self.job.group = group
        s = requests.Session()
        requests_login(s, user=other_member, password=u'other')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173376
    def test_clear_rows_in_system_recipe_map(self):
        with session.begin():
            system = data_setup.create_system()
            self.job.recipesets[0].recipes[0].systems[:] = [system]
        # check if rows in system_recipe_map
        self.assertNotEqual(len(self.job.recipesets[0].recipes[0].systems), 0)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() + 'jobs/%s/status' % self.job.id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.job.recipesets[0].recipes[0].systems), 0)

    def test_get_job_activity(self):
        with session.begin():
            self.job.record_activity(user=self.job.owner, service=u'testdata',
                                     field=u'green', action=u'blorp', new=u'something')
        response = requests.get(get_server_base() +
                                'jobs/%s/activity/' % self.job.id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(len(json['entries']), 1, json['entries'])
        self.assertEqual(json['entries'][0]['user']['user_name'],
                          self.job.owner.user_name)
        self.assertEqual(json['entries'][0]['field_name'], u'green')
        self.assertEqual(json['entries'][0]['action'], u'blorp')
        self.assertEqual(json['entries'][0]['new_value'], u'something')


class RecipeSetHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipe sets used by the job page.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.job = data_setup.create_job(owner=self.owner,
                                             retention_tag=u'scratch', priority=TaskPriority.normal)

    def test_get_recipeset(self):
        response = requests.get(get_server_base() +
                                'recipesets/%s' % self.job.recipesets[0].id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['t_id'], self.job.recipesets[0].t_id)

    def test_anonymous_cannot_change_recipeset(self):
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              data={'priority': u'Low'})
        self.assertEqual(response.status_code, 401)

    def test_other_users_cannot_change_recipeset(self):
        with session.begin():
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Low'})
        self.assertEqual(response.status_code, 403)

    def test_job_owner_can_reduce_priority(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Low'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            recipeset = self.job.recipesets[0]
            self.assertEqual(recipeset.priority, TaskPriority.low)
            self.assertEqual(recipeset.activity[0].field_name, u'Priority')
            self.assertEqual(recipeset.activity[0].action, u'Changed')
            self.assertEqual(recipeset.activity[0].new_value, u'Low')

    def test_job_owner_cannot_increase_priority(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Urgent'})
        self.assertEqual(response.status_code, 403)

    def check_changed_recipeset(self):
        recipeset = self.job.recipesets[0]
        self.assertEqual(recipeset.priority, TaskPriority.urgent)
        self.assertEqual(recipeset.activity[0].user.user_name,
                          data_setup.ADMIN_USER)
        self.assertEqual(recipeset.activity[0].field_name, u'Priority')
        self.assertEqual(recipeset.activity[0].action, u'Changed')
        self.assertEqual(recipeset.activity[0].new_value, u'Urgent')

    def test_admin_can_increase_priority(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'priority': u'Urgent'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.check_changed_recipeset()

    def test_job_owner_can_waive(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                              'recipesets/%s' % self.job.recipesets[0].id,
                              session=s, data={'waived': True})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            recipeset = self.job.recipesets[0]
            self.assertEqual(recipeset.waived, True)
            # https://bugzilla.redhat.com/show_bug.cgi?id=995012
            self.assertEqual(recipeset.activity[0].field_name, u'Waived')
            self.assertEqual(recipeset.activity[0].action, u'Changed')
            self.assertEqual(recipeset.activity[0].old_value, u'False')
            self.assertEqual(recipeset.activity[0].new_value, u'True')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1149977
    def test_admin_can_increase_priority_by_tid(self):
        s = requests.Session()
        requests_login(s)
        # by recipe set t_id
        response = patch_json(get_server_base() +
                              'recipesets/by-taskspec/%s' % self.job.recipesets[0].t_id,
                              session=s, data={'priority': u'Urgent'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.check_changed_recipeset()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1149977
    def test_admin_can_increase_priority_by_job_tid(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                              'recipesets/by-taskspec/%s' % self.job.t_id,
                              session=s, data={'priority': u'Urgent'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.check_changed_recipeset()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497021
    def test_group_member_can_reduce_group_job_priority_by_tid(self):
        with session.begin():
            group = data_setup.create_group()
            group_member = data_setup.create_user(password=u'member')
            group.add_member(group_member)
            self.job.group = group
        s = requests.Session()
        requests_login(s, user=group_member, password=u'member')
        response = patch_json(get_server_base() +
                              'recipesets/by-taskspec/%s' % self.job.t_id,
                              session=s, data={'priority': u'Low'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            recipeset = self.job.recipesets[0]
            self.assertEqual(recipeset.priority, TaskPriority.low)

    def test_update_containing_no_changes_should_silently_do_nothing(self):
        # PATCH request containing attributes with their existing values
        # should succeed and do nothing, including adding no activity records.
        with session.begin():
            recipeset = self.job.recipesets[0]
            recipeset.priority = TaskPriority.normal
            recipeset.waived = False
            self.assertEqual(recipeset.activity, [])
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'recipesets/%s' % recipeset.id,
                              session=s, data={'priority': u'Normal', 'waived': False})
        self.assertEqual(response.status_code, 200)
        with session.begin():
            session.expire_all()
            self.assertEqual(recipeset.priority, TaskPriority.normal)
            self.assertEqual(recipeset.waived, False)
            self.assertEqual(recipeset.activity, [])

    def test_anonymous_cannot_update_status(self):
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             data={'status': u'Cancelled'})
        self.assertEqual(response.status_code, 401)

    def test_other_users_cannot_update_status(self):
        with session.begin():
            user = data_setup.create_user(password=u'other')
        s = requests.Session()
        requests_login(s, user=user, password=u'other')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEqual(response.status_code, 403)

    def test_submission_delegate_cannot_update_status(self):
        # N.B. submission delegate but *not* submitter
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        self.assertEqual(response.status_code, 403)

    def test_cancel_recipeset(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.job.update_status()
            recipeset = self.job.recipesets[0]
            self.assertEqual(recipeset.status, TaskStatus.cancelled)
            # https://bugzilla.redhat.com/show_bug.cgi?id=995012
            self.assertEqual(recipeset.activity[0].field_name, u'Status')
            self.assertEqual(recipeset.activity[0].action, u'Cancelled')

    def test_submitter_can_cancel(self):
        with session.begin():
            submission_delegate = data_setup.create_user(password='password')
            self.owner.submission_delegates[:] = [submission_delegate]
            self.job.submitter = submission_delegate
        s = requests.Session()
        requests_login(s, user=submission_delegate, password=u'password')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    def test_group_member_can_cancel_in_group_job(self):
        with session.begin():
            other_member = data_setup.create_user(password='other')
            group = data_setup.create_group()
            group.add_member(self.job.owner)
            group.add_member(other_member)
            self.job.group = group
        s = requests.Session()
        requests_login(s, user=other_member, password=u'other')
        response = post_json(get_server_base() +
                             'recipesets/%s/status' % self.job.recipesets[0].id,
                             session=s, data={'status': u'Cancelled'})
        response.raise_for_status()

    def test_get_recipeset_comments(self):
        with session.begin():
            commenter = data_setup.create_user(user_name=u'jim')
            self.job.recipesets[0].comments.append(RecipeSetComment(
                user=commenter,
                created=datetime.datetime(2015, 11, 5, 17, 0, 55),
                comment=u'Microsoft and Red Hat to deliver new standard for '
                        u'enterprise cloud experiences'))
        response = requests.get(get_server_base() +
                                'recipesets/%s/comments/' % self.job.recipesets[0].id,
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(len(json['entries']), 1)
        self.assertEqual(json['entries'][0]['user']['user_name'], u'jim')
        self.assertEqual(json['entries'][0]['created'], u'2015-11-05 17:00:55')
        self.assertIn(u'Microsoft', json['entries'][0]['comment'])

    def test_post_recipeset_comment(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                             'recipesets/%s/comments/' % self.job.recipesets[0].id,
                             session=s, data={'comment': 'we unite on common solutions'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.job.recipesets[0].comments), 1)
            self.assertEqual(self.job.recipesets[0].comments[0].user, self.owner)
            self.assertEqual(self.job.recipesets[0].comments[0].comment,
                             u'we unite on common solutions')
            self.assertEqual(response.json()['id'],
                             self.job.recipesets[0].comments[0].id)

    def test_empty_comment_is_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                             'recipesets/%s/comments/' % self.job.recipesets[0].id,
                             session=s, data={'comment': None})
        self.assertEqual(response.status_code, 400)
        # whitespace-only comment also counts as empty
        response = post_json(get_server_base() +
                             'recipesets/%s/comments/' % self.job.recipesets[0].id,
                             session=s, data={'comment': ' '})
        self.assertEqual(response.status_code, 400)
