
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import base64
import hashlib
from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.server.selenium import XmlRpcTestCase

class LogUploadXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
            job = data_setup.create_job()
            self.recipe = job.recipesets[0].recipes[0]
            session.flush()
            self.recipe.logs = []
        self.server = self.get_server()

    def test_register_recipe_log(self):
        self.server.auth.login_password(self.lc.user.user_name, 'logmein')
        self.server.recipes.register_file('http://myserver/log.txt',
                self.recipe.id, '/', 'log.txt', '')
        with session.begin():
            session.refresh(self.recipe)
            self.assertEquals(len(self.recipe.logs), 1, self.recipe.logs)
            self.assertEquals(self.recipe.logs[0].path, u'/')
            self.assertEquals(self.recipe.logs[0].filename, u'log.txt')
            self.assertEquals(self.recipe.logs[0].server, u'http://myserver/log.txt')
        # Register it again with a different URL
        self.server.recipes.register_file('http://elsewhere/log.txt',
                self.recipe.id, '/', 'log.txt', '')
        with session.begin():
            session.refresh(self.recipe)
            self.assertEquals(len(self.recipe.logs), 1, self.recipe.logs)
            self.assertEquals(self.recipe.logs[0].path, u'/')
            self.assertEquals(self.recipe.logs[0].filename, u'log.txt')
            self.assertEquals(self.recipe.logs[0].server, u'http://elsewhere/log.txt')
