import re
import unittest
import lxml.etree
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client


class TaskDetailsTest(unittest.TestCase):

    def test_task_details_xml(self):
        with session.begin():
            task=data_setup.create_task(path='/testing/path',
                                        description='blah',
                                        exclude_arch=['i386','ppc'],
                                        exclude_osmajor=['MajorFoo', 'WunderFooBar'],
                                        requires=['2+2', 'Tofudebeast'],
                                        runfor=['philip', 'bradley'],
                                        type=['type3', 'type4'],
                                        )

        # regular xml
        out = run_client(['bkr', 'task-details', '--xml', task.name])

        task_elem = lxml.etree.fromstring(re.sub(task.name, '', out, count=1))
        self.assert_(task_elem.get('version') == task.version)
        self.assert_(task_elem.get('nda')  == task.nda or 'False')
        self.assert_(task_elem.get('name') == task.name)
        self.assert_(task_elem.get('destructive') == task.destructive or 'False')
        self.assert_(task_elem.find('description').text == task.description)
        self.assert_(task_elem.find('owner').text == task.owner)
        self.assert_(task_elem.find('path').text == task.path)

        self.assert_(len(task_elem.xpath("types/type[text()='type3']")) == 1)
        self.assert_(len(task_elem.xpath("types/type[text()='type4']")) == 1)
        self.assert_(len(task_elem.xpath("requires/package[text()='Tofudebeast']")) == 1)
        self.assert_(len(task_elem.xpath("requires/package[text()='2+2']")) == 1)
        self.assert_(len(task_elem.xpath("runFor/package[text()='philip']")) == 1)
        self.assert_(len(task_elem.xpath("runFor/package[text()='bradley']")) == 1)
        self.assert_(len(task_elem.xpath("excludedDistroFamilies/distroFamily[text()='MajorFoo']")) == 1)
        self.assert_(len(task_elem.xpath("excludedDistroFamilies/distroFamily[text()='WunderFooBar']")) == 1)
        self.assert_(len(task_elem.xpath("excludedArches/arch[text()='i386']")) == 1)
        self.assert_(len(task_elem.xpath("excludedArches/arch[text()='ppc']")) == 1)

        # pretty xml
        pretty_out = run_client(['bkr', 'task-details', '--prettyxml', task.name])
        pretty_minus_leading_name = re.sub(task.name, '', pretty_out, count=1)
        task_elem_pretty = lxml.etree.tostring(task_elem, pretty_print=True)
        self.assert_(task_elem_pretty.strip() == 
            pretty_minus_leading_name.strip())

    # https://bugzilla.redhat.com/show_bug.cgi?id=624417
    def test_details_include_owner_and_priority(self):
        with session.begin():
            owner = data_setup.create_user(user_name=u'besitzer@leo.org')
            task = data_setup.create_task(owner=owner, priority=u'Low')
        out = run_client(['bkr', 'task-details', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['owner'], u'besitzer@leo.org')
        self.assertEquals(details['priority'], u'Low')

    def test_details_without_owner(self):
        # We no longer permit empty Owner but older tasks may still lack it
        with session.begin():
            task = data_setup.create_task()
            task.owner = None
        out = run_client(['bkr', 'task-details', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['owner'], None)

    def test_details_without_uploader(self):
        # We now always record Uploader, but older tasks may lack it
        with session.begin():
            task = data_setup.create_task()
            task.uploader = None
        out = run_client(['bkr', 'task-details', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['uploader'], None)

    def test_details_invalid_tasks(self):
        with session.begin():
            task = data_setup.create_task(name='invalid_task', valid=False)
            task.uploader = None
        out = run_client(['bkr', 'task-details', '--invalid', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['name'], 'invalid_task')

    def test_details_without_destructive(self):
        with session.begin():
            task = data_setup.create_task()
            task.destructive = None
        out = run_client(['bkr', 'task-details', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['destructive'], None)

        # output in xml format
        out = run_client(['bkr', 'task-details', '--xml', task.name])

        task_elem = lxml.etree.fromstring(re.sub(task.name, '', out, count=1))
        self.assert_(task_elem.get('destructive') == None)

    def test_details_without_nda(self):
        with session.begin():
            task = data_setup.create_task()
            task.nda = None
        out = run_client(['bkr', 'task-details', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['nda'], None)

        # output in xml format
        out = run_client(['bkr', 'task-details', '--xml', task.name])

        task_elem = lxml.etree.fromstring(re.sub(task.name, '', out, count=1))
        self.assert_(task_elem.get('nda') == None)
