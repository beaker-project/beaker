import unittest, datetime, os, errno, shutil
from bkr.server.model import LogRecipe, TaskBase
from bkr.inttest import data_setup, with_transaction
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

        log_delete.log_delete()

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
        self.check_dir_not_there(dir_delete)

    def test_log_delete_to_delete(self):
        with session.begin():
            job_to_delete = self.job_to_delete
            job_to_delete.to_delete = datetime.datetime.utcnow()
            job_to_delete.recipesets[0].recipes[0].logs.append(LogRecipe(filename=u'test.log'))

        r_ = job_to_delete.recipesets[0].recipes[0]
        dir = os.path.join(r_.logspath ,r_.filepath)
        self.make_dir(dir)
        f = open(os.path.join(dir,'test.log'), 'w')
        f.close()
        log_delete.log_delete()
        self.check_dir_not_there(dir)

