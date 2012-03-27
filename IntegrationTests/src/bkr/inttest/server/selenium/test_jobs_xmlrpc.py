
# Beaker
#
# Copyright (C) 2010 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import unittest
import logging
import xmlrpclib
from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import Job, Distro

class JobUploadTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            if not Distro.by_name(u'BlueShoeLinux5-5'):
                data_setup.create_distro(name=u'BlueShoeLinux5-5')
            data_setup.create_task(name=u'/distribution/install')
            data_setup.create_task(name=u'/distribution/reservesys')
            user = data_setup.create_user(password=u'password')
        self.server = self.get_server()
        self.server.auth.login_password(user.user_name, 'password')

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
                        <task name="/distribution/install" />
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
            self.assertEqual(recipe.tasks[0].task.name, u'/distribution/install')
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
                        <task name="/distribution/install" />
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
