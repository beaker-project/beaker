
from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup

class TaskactionsTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
        self.server = self.get_server()
        self.server.auth.login_password(self.user.user_name, 'password')

    def test_running_status(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user)
            data_setup.mark_job_running(job)
        self.assertEquals(self.server.taskactions.task_info(job.t_id)['state'],
                'Running')
        self.assertEquals(self.server.taskactions.task_info(
                job.recipesets[0].t_id)['state'],
                'Running')
        self.assertEquals(self.server.taskactions.task_info(
                job.recipesets[0].recipes[0].t_id)['state'],
                'Running')
        self.assertEquals(self.server.taskactions.task_info(
                job.recipesets[0].recipes[0].tasks[0].t_id)['state'],
                'Running')
