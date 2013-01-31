import unittest
import subprocess
import os
from turbogears import config
from turbogears.database import session as tg_session, get_engine
from bkr.server.model import RecipeTask, Recipe, TaskStatus, RecipeSet, Job
from bkr.inttest import data_setup
from bkr.inttest import CONFIG_FILE
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if os.path.exists('../.git'):
    # Looks like we are in a git checkout
    _command = '../Server/bkr/server/tools/cleanup_unfinished_recipesets.py'
else:
    _command = '/usr/bin/beaker-cleanup-recipesets'

class TestUnfinishedRecipeSets(unittest.TestCase):

    @classmethod
    def update_status(cls, rt, current_session):
        import bkr
        old_session = bkr.server.model.session
        # Hack!
        bkr.server.model.session = current_session
        rt.pass_('/', 100, 'blah')
        rt.stop()
        bkr.server.model.session = old_session

    def setUp(self):
        tg_session.begin()
        t1 = data_setup.create_task(name=data_setup.unique_name('/rmancy/test%s'))
        self.recipe1 = data_setup.create_recipe(task_list=[t1])
        self.recipe2 = data_setup.create_recipe(task_list=[t1])
        data_setup.create_job_for_recipes([self.recipe1, self.recipe2])
        data_setup.mark_recipe_running(self.recipe1)
        data_setup.mark_recipe_running(self.recipe2)
        engine = get_engine()

        tg_session.commit()
        tg_session.close()
        tg_session.expunge_all()

        SessionFactory = sessionmaker(bind=engine)
        session1 = SessionFactory()
        session2 = SessionFactory()
        # This initial query on recipe is needed because
        # the repeatable read version is not created
        # until we first select it
        session2.query(Recipe).filter(Recipe.id == self.recipe1.id).one()

        r1t = self.recipe1.tasks[0]
        r2t = self.recipe2.tasks[0]
        self.update_status(session1.query(RecipeTask).filter(RecipeTask.id==r1t.id).first(), session1)
        session1.commit()
        session1.close()
        self.update_status(session2.query(RecipeTask).filter(RecipeTask.id==r2t.id).first(), session2)
        session2.commit()
        session2.close()

        # Check that have not completed up the task chain
        self.assertEquals(TaskStatus.running,
            tg_session.query(RecipeSet.status). \
            filter(RecipeSet.id == self.recipe1.recipeset.id).one()[0],
            'Recipe has unexpectedly been updated')
        self.assertEquals(TaskStatus.running,
            tg_session.query(Job.status). \
            filter(Job.id == self.recipe1.recipeset.job.id).one()[0],
            'Job has unexpectedly been updated')

    def test_cleanup_recipes(self):
        r1_id = self.recipe1.id
        r2_id = self.recipe2.id
        r1_system_fqdn = self.recipe1.resource.system.fqdn
        r2_system_fqdn = self.recipe2.resource.system.fqdn

        args=[_command, '-c', CONFIG_FILE, '--debug',]
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=dict(os.environ.items() +
                                      [('PYTHONUNBUFFERED', '1')]))
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertTrue('Releasing system %s for recipe %s' % (r1_system_fqdn, r1_id) in err)
        self.assertTrue('Releasing system %s for recipe %s' % (r2_system_fqdn, r2_id) in err)

        # Check that our status has been updated correctly
        self.assertEquals(TaskStatus.completed,
            tg_session.query(RecipeSet.status). \
            filter(RecipeSet.id == self.recipe1.recipeset.id).one()[0])

        self.assertEquals(TaskStatus.completed,
            tg_session.query(Job.status). \
            filter(Job.id == self.recipe1.recipeset.job.id).one()[0])

