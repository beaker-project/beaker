
import unittest
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.server.test import data_setup
from bkr.server.model import TaskStatus, Watchdog

class TestUpdateStatus(unittest.TestCase):

    def setUp(self):
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.user = data_setup.create_user()
        data_setup.create_distro(name=u'BlueShoeLinux5-5')
        data_setup.create_task(name=u'/distribution/install')
        session.flush()

    def test_abort_recipe_bubbles_status_to_job(self):
        xmljob = XmlJob(xmltramp.parse('''
            <job>
                <whiteboard>job </whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            '''))
        waiting = TaskStatus.by_name(u'Waiting')
        aborted = TaskStatus.by_name(u'Aborted')
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()
        for recipeset in job.recipesets:
            for recipe in recipeset.recipes:
                recipe.process()
                recipe.queue()
                recipe.schedule()
                recipe.waiting()

        # Abort the first recipe.
        job.recipesets[0].recipes[0].abort()

        # Verify that it and its children are aborted.
        self.assertEquals(job.recipesets[0].recipes[0].status, aborted)
        for task in job.recipesets[0].recipes[0].tasks:
            self.assertEquals(task.status, aborted)

        # Verify that the second recipe and its children are still waiting.
        self.assertEquals(job.recipesets[1].recipes[0].status, waiting)
        for task in job.recipesets[1].recipes[0].tasks:
            self.assertEquals(task.status, waiting)

        # Verify that the job still shows waiting.
        self.assertEquals(job.status, waiting)

        # Abort the second recipe now.
        job.recipesets[1].recipes[0].abort()

        # Verify that the whole job shows aborted now.
        self.assertEquals(job.status, aborted)

    def test_update_status_can_be_roundtripped_40214(self):
        complete_job_xml = pkg_resources.resource_string('bkr.server.test', 'job_40214.xml')
        xmljob = XmlJob(xmltramp.parse(complete_job_xml))

        data_setup.create_tasks(xmljob)
        
        # Import the job xml
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()

        # Mark job waiting
        data_setup.mark_job_waiting(job, self.user)
        session.flush()

        # watchdog's should exist 
        self.assertNotEqual(Watchdog.query().count(), 0)

        # Play back the original jobs results and status
        data_setup.playback_job_results(job, xmljob)
        session.flush()
        
        print 'J:%s %s %s' % (job.id, job.status, job.result)
        for i, recipeset in enumerate(xmljob.iter_recipeSets()):
            print '\tRS:%s %s %s' % (job.recipesets[i].id, job.recipesets[i].status,
                                     job.recipesets[i].result)
            for j, recipe in enumerate(recipeset.iter_recipes()):
                print '\t\tR:%s %s %s' % (job.recipesets[i].recipes[j].id, 
                                          job.recipesets[i].recipes[j].status,
                                          job.recipesets[i].recipes[j].result)
                for k, task in enumerate(recipe.iter_tasks()):
                    print '\t\t\tT:%s %s %s %s' % (job.recipesets[i].recipes[j].tasks[k].id,
                                                job.recipesets[i].recipes[j].tasks[k].task.name,
                                                job.recipesets[i].recipes[j].tasks[k].status,
                                                job.recipesets[i].recipes[j].tasks[k].result)
                for l, guest in enumerate(recipe.iter_guests()):
                    print '\t\t\tG:%s %s %s' % (job.recipesets[i].recipes[j].guests[l].id, 
                                                job.recipesets[i].recipes[j].guests[l].status,
                                                job.recipesets[i].recipes[j].guests[l].result)
                    for k, task in enumerate(guest.iter_tasks()):
                        print '\t\t\t\tT:%s %s %s %s' % (job.recipesets[i].recipes[j].guests[l].tasks[k].id,
                                                      job.recipesets[i].recipes[j].guests[l].tasks[k].task.name,
                                                      job.recipesets[i].recipes[j].guests[l].tasks[k].status,
                                                      job.recipesets[i].recipes[j].guests[l].tasks[k].result)

        # Verify that the original status and results match
        self.assertEquals(xmljob.wrappedEl('status'), job.status.status)
        self.assertEquals(xmljob.wrappedEl('result'), job.result.result)
        for i, recipeset in enumerate(xmljob.iter_recipeSets()):
            for j, recipe in enumerate(recipeset.iter_recipes()):
                self.assertEquals(recipe.wrappedEl('status'), job.recipesets[i].recipes[j].status.status)
                self.assertEquals(recipe.wrappedEl('result'), job.recipesets[i].recipes[j].result.result)
                for k, task in enumerate(recipe.iter_tasks()):
                    self.assertEquals(task.status, job.recipesets[i].recipes[j].tasks[k].status.status)
                    self.assertEquals(task.result, job.recipesets[i].recipes[j].tasks[k].result.result)

        # No watchdog's should exist when the job is complete
        self.assertEquals(Watchdog.query().count(), 0)
