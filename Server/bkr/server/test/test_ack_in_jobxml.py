import unittest
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.model import Job, Response, RecipeSetResponse
import xmltramp
from bkr.server.jobxml import XmlJob

class TestAckJobXml(unittest.TestCase):

    def setUp(self):
        self.job = data_setup.create_completed_job()
    
    def test_ack_jobxml(self):
        _response_type = u'ack'
        rs = self.job.recipesets[0]
        rs.nacked = RecipeSetResponse(type=_response_type)
        session.flush()
        jobxml = XmlJob(xmltramp.parse(self.job.to_xml(clone=False).toprettyxml()))
        for xmlrecipeSet in jobxml.iter_recipeSets():
            response = xmlrecipeSet.get_xml_attr('response',unicode,None)
            self.assertEqual(response,_response_type)
    
    def test_ack_jobxml_clone(self):
        """
        Unline test_ack_jobxml, we do _not_ want to see our response in here
        """
        _response_type = u'ack'
        rs = self.job.recipesets[0]
        rs.nacked = RecipeSetResponse(type=_response_type)
        session.flush()
        jobxml = XmlJob(xmltramp.parse(self.job.to_xml(clone=True).toprettyxml()))
        for xmlrecipeSet in jobxml.iter_recipeSets():
            response = xmlrecipeSet.get_xml_attr('response',unicode,None)
            self.assertEqual(response,None)
        
            

