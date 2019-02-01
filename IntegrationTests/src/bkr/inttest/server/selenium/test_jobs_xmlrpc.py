
# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import logging
import xmlrpclib
import datetime
from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import Job, Distro, ConfigItem, User, TaskBase

class JobUploadTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
        self.server = self.get_server()
        self.server.auth.login_password(self.user.user_name, 'password')

    def test_ignore_missing_tasks(self):
        job_tid = self.server.jobs.upload('''
            <job>
                <whiteboard>job with nonexistent task</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                        <task name="/asdf/notexist" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''',
            True # ignore_missing_tasks
        )
        self.assert_(job_tid.startswith('J:'))
        with session.begin():
            job = Job.by_id(int(job_tid[2:]))
            self.assertEqual(job.ttasks, 2) # not 3
            recipe = job.recipesets[0].recipes[0]
            self.assertEqual(len(recipe.tasks), 2)
            self.assertEqual(recipe.tasks[0].task.name, u'/distribution/check-install')
            # /asdf/notexist is silently dropped
            self.assertEqual(recipe.tasks[1].task.name, u'/distribution/reservesys')

    # https://bugzilla.redhat.com/show_bug.cgi?id=601170
    def test_error_message_lists_all_invalid_tasks(self):
        job_xml = '''
            <job>
                <whiteboard>job with multiple nonexistent tasks</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                            <distro_arch op="=" value="i386" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                        <task name="/asdf/notexist1" />
                        <task name="/asdf/notexist2" />
                        <task name="/asdf/notexist3" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        try:
            self.server.jobs.upload(job_xml)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('/asdf/notexist1, /asdf/notexist2, /asdf/notexist3'
                    in e.faultString)

    def test_reject_expired_root_password(self):
        with session.begin():
            ConfigItem.by_name(u'root_password_validity').set(90,
                    user=User.by_user_name(data_setup.ADMIN_USER))
            self.user.root_password = 'donttellanyone'
            self.user.rootpw_changed = datetime.datetime.utcnow() - datetime.timedelta(days=99)
        job_xml = '''
            <job>
                <whiteboard>job for user with expired password</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                            <distro_arch op="=" value="i386" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        try:
            self.server.jobs.upload(job_xml)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('root password has expired' in e.faultString)

    # https://bugzilla.redhat.com/show_bug.cgi?id=768167
    def test_doesnt_barf_on_xml_encoding_declaration(self):
        job_tid = self.server.jobs.upload(u'''<?xml version="1.0" encoding="utf-8"?>
            <job>
                <whiteboard>job with encoding in XML declaration яяя</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            '''.encode('utf8'))
        self.assert_(job_tid.startswith('J:'))

    def test_external_tasks(self):
        job_tid = self.server.jobs.upload('''
            <job>
                <whiteboard>job with external task</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                        <task name="/distribution/example">
                            <fetch url="git://example.com/externaltasks/example#master"/>
                        </task>
                        <task>
                            <fetch url="git://example.com/externaltasks/example2#master"/>
                        </task>
                        <task name="/distribution/example3">
                            <fetch url="git://example.com/externaltasks#master"
                                   subdir="examples/3" />
                        </task>
                        <task>
                            <fetch url="git://example.com/externaltasks#master"
                                   subdir="examples/4" />
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        self.assert_(job_tid.startswith('J:'))
        with session.begin():
            job = TaskBase.get_by_t_id(job_tid)
            recipe = job.recipesets[0].recipes[0]
            self.assertEquals(len(recipe.tasks), 5)
            self.assertEquals(recipe.tasks[0].name, u'/distribution/check-install')
            self.assertEquals(recipe.tasks[0].task.name, u'/distribution/check-install')
            self.assertEquals(recipe.tasks[0].fetch_url, None)
            self.assertEquals(recipe.tasks[1].name, u'/distribution/example')
            self.assertEquals(recipe.tasks[1].task, None)
            self.assertEquals(recipe.tasks[1].fetch_url,
                     'git://example.com/externaltasks/example#master')
            self.assertEquals(recipe.tasks[2].name,
                    u'git://example.com/externaltasks/example2#master')
            self.assertEquals(recipe.tasks[2].task, None)
            self.assertEquals(recipe.tasks[2].fetch_url,
                    u'git://example.com/externaltasks/example2#master')
            self.assertEquals(recipe.tasks[3].name, u'/distribution/example3')
            self.assertEquals(recipe.tasks[3].task, None)
            self.assertEquals(recipe.tasks[3].fetch_url,
                    u'git://example.com/externaltasks#master')
            self.assertEquals(recipe.tasks[3].fetch_subdir, u'examples/3')
            self.assertEquals(recipe.tasks[4].name,
                    u'git://example.com/externaltasks#master examples/4')
            self.assertEquals(recipe.tasks[4].task, None)
            self.assertEquals(recipe.tasks[4].fetch_url,
                    u'git://example.com/externaltasks#master')
            self.assertEquals(recipe.tasks[4].fetch_subdir, u'examples/4')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1140912
    def test_invalid_user(self):
        job_xml = '''
            <job user="notexist">
                <whiteboard>job submitted for invalid user</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                            <distro_arch op="=" value="i386" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        try:
            self.server.jobs.upload(job_xml)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assertIn('notexist is not a valid user name', e.faultString)

class JobFilterTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    def test_can_filter_by_whiteboard(self):
        with session.begin():
            excluded_job = data_setup.create_completed_job(whiteboard=u'whiteboard')
            included_job = data_setup.create_completed_job(whiteboard=u'blackboard')
        result = self.server.jobs.filter(dict(whiteboard=u'blackboard'))
        self.assertItemsEqual(result, [included_job.t_id])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1229937
    def test_can_filter_by_whiteboard_in_combination_with_other_filters(self):
        with session.begin():
            job_owner = data_setup.create_user()
            excluded_job = data_setup.create_completed_job(whiteboard=u'blackboard')
            included_job = data_setup.create_completed_job(whiteboard=u'blackboard',
                    owner=job_owner)
        result = self.server.jobs.filter(
                dict(whiteboard=u'blackboard', owner=job_owner.user_name))
        self.assertItemsEqual(result, [included_job.t_id])
