
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import lxml.etree
from turbogears.database import session
from bkr.server.bexceptions import BX
from bkr.inttest import data_setup, DatabaseTestCase

class TestTasks(DatabaseTestCase):

    def setUp(self):
        session.begin()
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.task = data_setup.create_task(name=u'/fake/task/here')
        distro_tree = data_setup.create_distro_tree()
        self.user = data_setup.create_user()
        self.xmljob = lxml.etree.fromstring('''
            <job>
                <whiteboard>job with fake task</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="%s" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="%s" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            ''' % (distro_tree.distro.name, self.task.name))
        session.flush()

    def tearDown(self):
        session.rollback()

    def test_enable_task(self):
        self.task.valid = True
        session.flush()
        self.controller.process_xmljob(self.xmljob, self.user)

    def test_disable_task(self):
        self.task.valid = False
        session.flush()
        self.assertRaises(BX, lambda: self.controller.process_xmljob(self.xmljob, self.user))
