
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pkg_resources
import datetime
import os
import errno
import shutil
from unittest2 import SkipTest
import tempfile
import subprocess
import sys
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.model import LogRecipe, TaskBase, Job, Recipe, \
    RenderedKickstart, TaskStatus
from bkr.inttest import data_setup, with_transaction, Process, DatabaseTestCase
from bkr.server.tools import log_delete
from turbogears.database import session
from turbogears import config

def setUpModule():
    # It makes our tests simpler here if they only need to worry about deleting 
    # logs which they themselves have created, rather than ones which might have 
    # been left behind from earlier tests in the run.
    for job, _ in Job.expired_logs():
        job.delete()

class LogDelete(DatabaseTestCase):

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

    def test_limit(self):
        limit = 10

        def _create_jobs():
            with session.begin():
                for i in range(limit + 1):
                    job_to_delete = data_setup.create_completed_job(
                            start_time=datetime.datetime.utcnow() - datetime.timedelta(days=60),
                            finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=31))
                    job_to_delete.recipesets[0].recipes[0].logs.append(LogRecipe(filename=u'test.log'))

        def _get_output(f):
            tmp_file =  tempfile.TemporaryFile()
            sys_std_out = sys.stdout
            sys.stdout = tmp_file
            f()
            tmp_file.seek(0)
            log_delete_output = tmp_file.read()
            tmp_file.close()
            sys.stdout = sys_std_out
            return log_delete_output

        # Test with limit
        _create_jobs()
        with_limit = _get_output(lambda:
            log_delete.log_delete(dry=True, print_logs=True, limit=10))
        self.assert_(len(with_limit.splitlines()) == limit)

        # Test no limit set
        _create_jobs()
        no_limit = _get_output(lambda:
            log_delete.log_delete(dry=True, print_logs=True))
        self.assert_(len(no_limit.splitlines()) > limit)

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

    def test_rendered_kickstart_is_deleted(self):
        with session.begin():
            self.job_to_delete.to_delete = datetime.datetime.utcnow()
            recipe = self.job_to_delete.recipesets[0].recipes[0]
            ks = RenderedKickstart(kickstart=u'This is not a real kickstart.')
            recipe.installation.rendered_kickstart = ks
        log_delete.log_delete()
        with session.begin():
            session.expire_all()
            self.assertEqual(recipe.installation.rendered_kickstart, None)
            self.assertRaises(NoResultFound, RenderedKickstart.by_id, ks.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1273302
    def test_deletes_old_jobs_which_never_started(self):
        with session.begin():
            the_past = datetime.datetime.utcnow() - datetime.timedelta(days=31)
            cancelled_job = data_setup.create_job(queue_time=the_past)
            cancelled_job.cancel()
            cancelled_job.update_status()
            aborted_job = data_setup.create_job(queue_time=the_past)
            aborted_job.abort()
            aborted_job.update_status()
            self.assertEqual(cancelled_job.status, TaskStatus.cancelled)
            self.assertEqual(aborted_job.status, TaskStatus.aborted)
            self.assertIsNone(cancelled_job.recipesets[0].recipes[0].finish_time)
            self.assertIsNone(aborted_job.recipesets[0].recipes[0].finish_time)
            self.assertIsNone(cancelled_job.deleted)
            self.assertIsNone(aborted_job.deleted)
        log_delete.log_delete()
        with session.begin():
            self.assertIsNotNone(Job.by_id(cancelled_job.id).deleted)
            self.assertIsNotNone(Job.by_id(aborted_job.id).deleted)

class RemoteLogDeletionTest(DatabaseTestCase):

    def setUp(self):
        # XXX We should eventually configure these redirect tests
        # to work with apache, until then, we do this...
        test_id = self.id()
        if test_id.endswith('test_301_redirect') or \
              test_id.endswith('test_302_redirect'):
            self.force_local_archive_server = True
        else:
            self.force_local_archive_server = False

        if 'BEAKER_LABCONTROLLER_HOSTNAME' in os.environ and not \
            self.force_local_archive_server:
            self.logs_dir = config.get('basepath.logs')
            self.recipe_logs_dir = os.path.join(self.logs_dir, 'recipe')
            self.log_server = os.environ['BEAKER_LABCONTROLLER_HOSTNAME']
            self.log_server_url = 'http://%s/logs' % self.log_server
            self.addCleanup(shutil.rmtree, self.recipe_logs_dir,  ignore_errors=True)
        else:
            self.logs_dir = tempfile.mkdtemp(prefix='beaker-test-log-delete')
            self.recipe_logs_dir = os.path.join(self.logs_dir, 'recipe')
            self.archive_server = Process('http_server.py', args=[sys.executable,
                        pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                        '--base', self.logs_dir, '--writable'],
                    listen_port=19998)
            self.archive_server.start()
            self.log_server = 'localhost:19998'
            self.log_server_url = 'http://%s' % self.log_server
            self.addCleanup(shutil.rmtree, self.logs_dir, ignore_errors=True)
            self.addCleanup(self.archive_server.stop)
        try:
            os.mkdir(self.recipe_logs_dir)
        except OSError, e:
            if e.errno == errno.EEXIST:
                # perhaps something else created it and did not clean it up
                pass
            else:
                raise
        if 'BEAKER_LABCONTROLLER_HOSTNAME' in os.environ and not \
            self.force_local_archive_server:
            # XXX This assumes we are running against apache, and allows
            # WebDAV to delete stuff.
            os.chmod(self.recipe_logs_dir, 02777)
            orig_umask =  os.umask(000)
            self.addCleanup(os.umask, orig_umask)

    def create_deleted_job_with_log(self, path, filename):
        with session.begin():
            job = data_setup.create_completed_job()
            job.to_delete = datetime.datetime.utcnow()
            session.flush()
            job.recipesets[0].recipes[0].log_server = self.log_server
            job.recipesets[0].recipes[0].logs[:] = [
                    LogRecipe(server='%s/%s' % (self.log_server_url, path),
                        filename=filename)]
            for rt in job.recipesets[0].recipes[0].tasks:
                rt.logs[:] = []

    def test_deletion(self):
        open(os.path.join(self.recipe_logs_dir, 'dummy.txt'), 'w').write('dummy')
        self.create_deleted_job_with_log(u'recipe/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
        self.assert_(not os.path.exists(os.path.join(self.logs_dir, 'recipe')))

    def test_301_redirect(self):
        open(os.path.join(self.recipe_logs_dir, 'dummy.txt'), 'w').write('dummy')
        self.create_deleted_job_with_log(u'redirect/301/recipe/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
        self.assert_(not os.path.exists(os.path.join(self.logs_dir, 'recipe')))

    def test_302_redirect(self):
        open(os.path.join(self.recipe_logs_dir, 'dummy.txt'), 'w').write('dummy')
        self.create_deleted_job_with_log(u'redirect/302/recipe/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
        self.assert_(not os.path.exists(os.path.join(self.logs_dir, 'recipe')))

    def test_404(self):
        self.create_deleted_job_with_log(u'notexist/', u'dummy.txt')
        self.assertEquals(log_delete.log_delete(), 0) # exit status
