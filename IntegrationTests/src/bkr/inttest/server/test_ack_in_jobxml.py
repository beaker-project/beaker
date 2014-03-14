
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import Job, Response, RecipeSetResponse
import xmltramp
from bkr.server.jobxml import XmlJob

class TestAckJobXml(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_completed_job()
    
    def test_ack_jobxml(self):
        _response_type = u'ack'
        with session.begin():
            rs = self.job.recipesets[0]
            rs.nacked = RecipeSetResponse(type=_response_type)
        jobxml = XmlJob(xmltramp.parse(self.job.to_xml(clone=False).toprettyxml()))
        for xmlrecipeSet in jobxml.iter_recipeSets():
            response = xmlrecipeSet.get_xml_attr('response',unicode,None)
            self.assertEqual(response,_response_type)
    
    def test_ack_jobxml_clone(self):
        """
        Unline test_ack_jobxml, we do _not_ want to see our response in here
        """
        _response_type = u'ack'
        with session.begin():
            rs = self.job.recipesets[0]
            rs.nacked = RecipeSetResponse(type=_response_type)
        jobxml = XmlJob(xmltramp.parse(self.job.to_xml(clone=True).toprettyxml()))
        for xmlrecipeSet in jobxml.iter_recipeSets():
            response = xmlrecipeSet.get_xml_attr('response',unicode,None)
            self.assertEqual(response,None)
        
            

