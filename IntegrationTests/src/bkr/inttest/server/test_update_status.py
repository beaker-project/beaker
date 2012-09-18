
import unittest
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.inttest import data_setup
from bkr.server.model import TaskStatus, TaskResult, Watchdog, RecipeSet, Distro

def watchdogs_for_job(job):
    return Watchdog.query.join('recipe', 'recipeset', 'job')\
            .filter(RecipeSet.job == job).all() + \
           Watchdog.query.join('recipetask', 'recipe', 'recipeset', 'job')\
            .filter(RecipeSet.job == job).all()

class TestUpdateStatus(unittest.TestCase):

    def setUp(self):
        session.begin()
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.user = data_setup.create_user()
        if not Distro.by_name(u'BlueShoeLinux5-5'):
            data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')
        session.flush()

    def tearDown(self):
        session.commit()
        session.close()

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
        self.assertEquals(job.recipesets[0].recipes[0].status, TaskStatus.aborted)
        for task in job.recipesets[0].recipes[0].tasks:
            self.assertEquals(task.status, TaskStatus.aborted)

        # Verify that the second recipe and its children are still waiting.
        self.assertEquals(job.recipesets[1].recipes[0].status, TaskStatus.waiting)
        for task in job.recipesets[1].recipes[0].tasks:
            self.assertEquals(task.status, TaskStatus.waiting)

        # Verify that the job still shows waiting.
        self.assertEquals(job.status, TaskStatus.waiting)

        # Abort the second recipe now.
        job.recipesets[1].recipes[0].abort()

        # Verify that the whole job shows aborted now.
        self.assertEquals(job.status, TaskStatus.aborted)

    def test_update_status_can_be_roundtripped_35508(self):
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'job_35508.xml')
        xmljob = XmlJob(xmltramp.parse(complete_job_xml))

        data_setup.create_tasks(xmljob)
        session.flush()
        
        # Import the job xml
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()

        # Mark job waiting
        data_setup.mark_job_waiting(job)
        session.flush()

        # watchdog's should exist 
        self.assertNotEqual(len(watchdogs_for_job(job)), 0)

        # Play back the original jobs results and status
        data_setup.playback_job_results(job, xmljob)
        session.flush()
        
        # Verify that the original status and results match
        self.assertEquals(TaskStatus.from_string(xmljob.wrappedEl('status')), job.status)
        self.assertEquals(TaskResult.from_string(xmljob.wrappedEl('result')), job.result)
        for i, recipeset in enumerate(xmljob.iter_recipeSets()):
            for j, recipe in enumerate(recipeset.iter_recipes()):
                self.assertEquals(TaskStatus.from_string(recipe.wrappedEl('status')),
                        job.recipesets[i].recipes[j].status)
                self.assertEquals(TaskResult.from_string(recipe.wrappedEl('result')),
                        job.recipesets[i].recipes[j].result)
                for k, task in enumerate(recipe.iter_tasks()):
                    self.assertEquals(TaskStatus.from_string(task.status),
                            job.recipesets[i].recipes[j].tasks[k].status)
                    self.assertEquals(TaskResult.from_string(task.result),
                            job.recipesets[i].recipes[j].tasks[k].result)

        # No watchdog's should exist when the job is complete
        self.assertEquals(len(watchdogs_for_job(job)), 0)

    def test_update_status_can_be_roundtripped_40214(self):
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'job_40214.xml')
        xmljob = XmlJob(xmltramp.parse(complete_job_xml))

        data_setup.create_tasks(xmljob)
        session.flush()
        
        # Import the job xml
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()

        # Mark job waiting
        data_setup.mark_job_waiting(job)
        session.flush()

        # watchdog's should exist 
        self.assertNotEqual(len(watchdogs_for_job(job)), 0)

        # Play back the original jobs results and status
        data_setup.playback_job_results(job, xmljob)
        session.flush()
        
        # Verify that the original status and results match
        self.assertEquals(TaskStatus.from_string(xmljob.wrappedEl('status')), job.status)
        self.assertEquals(TaskResult.from_string(xmljob.wrappedEl('result')), job.result)
        for i, recipeset in enumerate(xmljob.iter_recipeSets()):
            for j, recipe in enumerate(recipeset.iter_recipes()):
                self.assertEquals(TaskStatus.from_string(recipe.wrappedEl('status')),
                        job.recipesets[i].recipes[j].status)
                self.assertEquals(TaskResult.from_string(recipe.wrappedEl('result')),
                        job.recipesets[i].recipes[j].result)
                for k, task in enumerate(recipe.iter_tasks()):
                    self.assertEquals(TaskStatus.from_string(task.status),
                            job.recipesets[i].recipes[j].tasks[k].status)
                    self.assertEquals(TaskResult.from_string(task.result),
                            job.recipesets[i].recipes[j].tasks[k].result)

        # No watchdog's should exist when the job is complete
        self.assertEquals(len(watchdogs_for_job(job)), 0)
