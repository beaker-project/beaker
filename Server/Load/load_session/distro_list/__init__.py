from request import RequestFactory, FAILED, PASSED
from load_session import Session as ParentSession
from report.graphite_report import report

class Session(ParentSession):

    id = 'distro-list'

    def __init__(self, *args, **kw):
        super(Session, self).__init__(*args, **kw)
        method = 'distros.filter'
        params = {'limit' : 10,
                  'name' :'RHEL%',
                  'treepath' : '',
                  'family' : '',
                  'arch' : '',
                  'tags' : '',}

        self.request = RequestFactory.create('xmlrpc', 
            method, param=params, keep_return=True)

    @report
    def run(self):
        return self.request.run()
