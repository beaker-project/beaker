import unittest
from threading import Thread
from turbogears.database import session
from nose.plugins.skip import SkipTest
from bkr.inttest import data_setup
from bkr.labcontroller.proxy import Watchdog
from bkr.labcontroller.message_bus import LabBeakerBus
from bkr.labcontroller.config import get_conf
from bkr.server.model import RetentionTag
from bkr.inttest.message_bus import TestServerBeakerBus
from time import sleep


class TestWatchdog(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        conf = get_conf()
        cls.using_qpid = conf.get('QPID_BUS')
        cls.watchdog = Watchdog(conf=conf)
        cls.watchdog.hub._login()

    def _qpid_send_receive(self):
        while True:
            from qpid.messaging.exceptions import NotFound
            msg = self.receiver.fetch()
            self.ssn.acknowledge()
            msg_kw, address = self.bb._service_queue_worker_logic(msg)
            try:
                self.bb._send_service_response_logic(msg_kw, address, self.ssn)
            except NotFound, e:
                continue #maybe an old message?
            break


    #https://bugzilla.redhat.com/show_bug.cgi?id=733543
    def test_qpid_toobigtofail(self):
        self.qpid_active_watchdog(300)

    def test_qpid_active_watchdog(self):
        self.qpid_active_watchdog(5)

    def qpid_active_watchdog(self, number_of_jobs):
        if not self.using_qpid:
            raise SkipTest('Not using qpid for watchdogs')
        self.bb = TestServerBeakerBus()
        self.ssn = self.bb.conn.session()
        self.receiver = self.bb._create_service_receiver(self.ssn)
        lbb = LabBeakerBus(watchdog=self.watchdog)
        tag = RetentionTag.by_tag(u'scratch')
        owner = data_setup.create_user()
        session.flush()
        from bkr.inttest.labcontroller import lc
        lbb.lc = lc.fqdn
        all_jobs = []
        for i in range(number_of_jobs):
            j = data_setup.create_job(retention_tag=tag, owner=owner)
            session.flush()
            all_jobs.append(j)
            data_setup.mark_job_waiting(j,user=owner)
            for r in j.all_recipes:
                r.system.lab_controller = lc
            data_setup.mark_job_active(j)
        session.flush()
        # Get active watchdogs
        t = Thread(target=self._qpid_send_receive)
        t.start()
        active_watchdogs = lbb.rpc.recipes.tasks.watchdogs('active', lbb.lc)
        all_recipes = []
        for j in all_jobs:
            for r in j.all_recipes:
                all_recipes.append(r)
        expected_watchdogs_set = set([(r.id,r.system.fqdn) for r in all_recipes])
        active_watchdogs_set = set([(aw['recipe_id'], aw['system']) for aw in active_watchdogs])
        self.assert_(expected_watchdogs_set.issubset(active_watchdogs_set))

        # Apply active watchdogs
        self.watchdog.active_watchdogs(active_watchdogs, purge=False)
        t.join()
