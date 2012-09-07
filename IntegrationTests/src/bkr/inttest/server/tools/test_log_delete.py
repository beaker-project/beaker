import unittest, datetime, os, errno, shutil
import tempfile
import subprocess
from bkr.server.model import LogRecipe, TaskBase, Job
from bkr.inttest import data_setup, with_transaction, Process
from bkr.server.tools import log_delete
from turbogears.database import session

class LogDelete(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.password=u'p'
        self.user = data_setup.create_user(password=self.password)
        self.job_to_delete = data_setup.create_completed_job() #default tag, scratch
        self.job_to_delete.owner = self.user

    def check_dir_not_there(self, dir):
        if os.path.exists(dir):
            raise AssertionError('%s should have been deleted' % dir)

    def make_dir(self, dir):
        try:
            os.makedirs(dir)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

    def _assert_logs_not_in_db(self, job):
        for rs in job.recipesets:
            for r in rs.recipes:
                self.assert_(r.logs == [])
                for rt in r.tasks:
                    self.assert_(rt.logs == [])
                    for rtr in rt.results:
                        self.assert_(rtr.logs == [])

    def test_log_not_delete(self):
        # Job that is not within it's expiry time
        with session.begin():
            job_not_delete = data_setup.create_completed_job(
                    start_time=datetime.datetime.utcnow() - datetime.timedelta(days=60),
                    finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=29))
        job_not_delete.recipesets[0].recipes[0].logs.append(LogRecipe(filename=u'test.log'))
        r_not_delete = job_not_delete.recipesets[0].recipes[0]
        dir_not_delete = os.path.join(r_not_delete.logspath ,r_not_delete.filepath)
        self.make_dir(dir_not_delete)
        ft = open(os.path.join(dir_not_delete,'test.log'), 'w')
        ft.close()
        session.flush()
        log_delete.log_delete()
        self.assertRaises(AssertionError, self._assert_logs_not_in_db, self.job_to_delete)
        try:
            self.check_dir_not_there(dir_not_delete)
            raise Exception('%s was deleted when it shold not have been' % dir_not_delete)
        except AssertionError:
            pass

    def test_log_delete_expired(self):
        with session.begin():
            job_to_delete = data_setup.create_completed_job(
                    start_time=datetime.datetime.utcnow() - datetime.timedelta(days=60),
                    finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=31))
            self.job_to_delete.owner = self.user
            job_to_delete.recipesets[0].recipes[0].logs.append(LogRecipe(filename=u'test.log'))
            r_delete = job_to_delete.recipesets[0].recipes[0]
            dir_delete = os.path.join(r_delete.logspath ,r_delete.filepath)

        self.make_dir(dir_delete)
        fd = open(os.path.join(dir_delete,'test.log'), 'w')
        fd.close()
        log_delete.log_delete()
        self._assert_logs_not_in_db(Job.by_id(job_to_delete.id))
        self.check_dir_not_there(dir_delete)

    def test_log_delete_to_delete(self):
        with session.begin():
            self.job_to_delete.to_delete = datetime.datetime.utcnow()
            self.job_to_delete.recipesets[0].recipes[0].logs.append(LogRecipe(filename=u'test.log'))
        r_ = self.job_to_delete.recipesets[0].recipes[0]
        dir = os.path.join(r_.logspath ,r_.filepath)
        self.make_dir(dir)
        f = open(os.path.join(dir,'test.log'), 'w')
        f.close()
        log_delete.log_delete()
        self._assert_logs_not_in_db(Job.by_id(self.job_to_delete.id))
        self.check_dir_not_there(dir)

class RemoteLogDeletionTest(unittest.TestCase):

    def setUp(self):
        self.logs_dir = tempfile.mkdtemp(prefix='beaker-test-log-delete')
        self.archive_server = Process('archive_server.py',
                args=[os.path.join(os.path.dirname(__file__), '..', '..', 'archive_server.py'),
                      '--base', self.logs_dir])
        self.archive_server.start()

    def tearDown(self):
        self.archive_server.stop()
        shutil.rmtree(self.logs_dir, ignore_errors=True)

    def create_deleted_job_with_log(self, path, filename):
        with session.begin():
            job = data_setup.create_completed_job()
            job.to_delete = datetime.datetime.utcnow()
            session.flush()
            job.recipesets[0].recipes[0].log_server = u'localhost:19998'
            job.recipesets[0].recipes[0].logs[:] = [
                    LogRecipe(server=u'http://localhost:19998/%s' % path, filename=filename)]
            for rt in job.recipesets[0].recipes[0].tasks:
                rt.logs[:] = []

    def test_deletion(self):
        os.mkdir(os.path.join(self.logs_dir, 'recipe'))
        open(os.path.join(self.logs_dir, 'recipe', 'dummy.txt'), 'w').write('dummy')
        os.mkdir(os.path.join(self.logs_dir, 'dont_tase_me_bro'))
        self.create_deleted_job_with_log(u'recipe/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
        self.assert_(not os.path.exists(os.path.join(self.logs_dir, 'recipe')))
        self.assert_(os.path.exists(os.path.join(self.logs_dir, 'dont_tase_me_bro')))

    def test_301_redirect(self):
        os.mkdir(os.path.join(self.logs_dir, 'recipe'))
        open(os.path.join(self.logs_dir, 'recipe', 'dummy.txt'), 'w').write('dummy')
        self.create_deleted_job_with_log(u'redirect/301/recipe/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
        self.assert_(not os.path.exists(os.path.join(self.logs_dir, 'recipe')))

    def test_302_redirect(self):
        os.mkdir(os.path.join(self.logs_dir, 'recipe'))
        open(os.path.join(self.logs_dir, 'recipe', 'dummy.txt'), 'w').write('dummy')
        self.create_deleted_job_with_log(u'redirect/302/recipe/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
        self.assert_(not os.path.exists(os.path.join(self.logs_dir, 'recipe')))

    def test_404(self):
        self.create_deleted_job_with_log(u'notexist/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
