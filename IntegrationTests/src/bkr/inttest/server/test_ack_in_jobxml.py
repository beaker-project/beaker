
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction, DatabaseTestCase

class TestAckJobXml(DatabaseTestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_completed_job()

    def test_ack_jobxml(self):
        with session.begin():
            rs = self.job.recipesets[0]
            self.assertEqual(rs.waived, False)
        jobxml = self.job.to_xml(clone=False)
        for xmlrecipeSet in jobxml.xpath('recipeSet'):
            response = xmlrecipeSet.get('response', None)
            self.assertEqual(response, 'ack')

    def test_ack_jobxml_clone(self):
        """
        Unline test_ack_jobxml, we do _not_ want to see our response in here
        """
        jobxml = self.job.to_xml(clone=True)
        for xmlrecipeSet in jobxml.xpath('recipeSet'):
            response = xmlrecipeSet.get('response', None)
            self.assertEqual(response, None)
