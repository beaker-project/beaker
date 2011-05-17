from request import RequestFactory, FAILED, PASSED
from load_session import Session as ParentSession
from report.graphite_report import report

class Session(ParentSession):

    id = 'job-submit'

    def __init__(self, *args, **kw):
        super(Session, self).__init__(*args, **kw)
        cmd = 'bkr job-submit'
        self.request = RequestFactory.create('client', 
            cmd=cmd, args=['new_job.xml'], keep_return=True)

    @report
    def run(self):
        return self.request.run()
