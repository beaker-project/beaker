
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import logging
import xmlrpclib
from turbogears.database import session

from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup

class TestJobDelete(XmlRpcTestCase):

    @classmethod
    def setUpClass(cls):
        with session.begin():
            cls.product_one = data_setup.create_product()
            cls.product_two = data_setup.create_product()
            cls.distro_tree = data_setup.create_distro_tree(osmajor=u'customosmajor')
            cls.password = u'password'
            cls.user = data_setup.create_user(password=cls.password)
            cls.scratch_job = data_setup.create_completed_job(
                    retention_tag=u'scratch', owner=cls.user,
                    product=cls.product_one, distro_tree=cls.distro_tree)
            cls.sixty_days_job = data_setup.create_completed_job(
                    retention_tag=u'60Days', product=cls.product_two,
                    owner=cls.user)
        cls.server = cls.get_server()
        cls.server.auth.login_password(cls.user.user_name, cls.password)

    def test_by_tag(self):
        output = self.server.jobs.delete_jobs([],[self.scratch_job.retention_tag.tag],None,None,True,None)
        if self.sixty_days_job.t_id in output:
            self.fail("Found %s when deleting by 'scratch'" % self.sixty_days_job.t_id)
        if self.scratch_job.t_id not in output:
            self.fail("Did not find %s when deleting by 'scratch'" % self.scratch_job.t_id)

    def test_by_product(self):
        output = self.server.jobs.delete_jobs([],None,None,None,True,[self.product_one.name])
        if self.sixty_days_job.t_id in output:
            self.fail("Found %s when deleting by '%s'" % (self.sixty_days_job.t_id, self.product_one.name))
        if self.scratch_job.t_id not in output:
            self.fail("Did not find %s when deleting by '%s'" % (self.scratch_job.t_id, self.product_one.name))

    def test_by_family(self):
        output = self.server.jobs.delete_jobs([],None,None,u'customosmajor',True,None)
        if self.sixty_days_job.t_id in output:
            self.fail("Found %s when deleting by family" % self.sixty_days_job.t_id)
        if self.scratch_job.t_id not in output:
            self.fail("Did not find %s when deleting by family" % (self.scratch_job.t_id))

    def test_by_job(self):
        output = self.server.jobs.delete_jobs([self.sixty_days_job.t_id,self.scratch_job.t_id],None,None,None,True,None)
        if self.sixty_days_job.t_id not in output:
            self.fail("Did not find %s by family job-id" % self.sixty_days_job.t_id)
        if self.scratch_job.t_id not in output:
            self.fail("Did not find %s when deleting by job-id" % (self.scratch_job.t_id))

    @classmethod
    def tearDownClass(cls):
        pass
