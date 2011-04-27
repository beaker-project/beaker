import subprocess
import xmlrpclib
import time
from datetime import datetime
from graphite_connector import GraphiteConnection

now = datetime.now
FAILED = 'fail'
PASSED = 'pass'

def get_in_minutes(duration, unit):
    if unit == 'minute':
        return duration
    if unit =='hour':
        return duration * 60
    if unit == 'seconds':
        return float(duration) / 60.0

def get_in_seconds(duration, unit):
    if unit == 'seconds':
        return duration
    if unit == 'minute':
        return duration * 60
    if unit == 'hour':
        return duration * 3600

def report(f):
 
    def the_run(instance, *args):
        """Sends data to graphite server
        sends error count, hit count, and response times
        """
        start = now() 
        try:
            result, output = f(instance,*args)
        except Exception, e:
            print 'Thrown Exception'
            instance.result_server.send('beaker.load.error.%s 1 %d\n' % (instance.id, int(time.time())))
            return
            
        finish = now()
        response_time = (finish - start)
        instance.result_server.send('beaker.load.response.%s %f %d\n' % (instance.id, response_time.total_seconds(), int(time.time())))
        instance.result_server.send('beaker.load.hit.single.%s 1 %s\n' % (instance.id, int(time.time())))

    return the_run
    
class RequestFactory:

    @classmethod
    def create(cls, type, **kw):
        if type == 'xmlrpc':
            return XMLRPCRequest(**kw)
        if type == 'http':
            return HTTPRequest(**kw)
        if type == 'qpid':
            return QPIDRequest(**kw)
        if type == 'client':
            return ClientRequest(**kw)

class Request(object):


    #FIXME get this from a config or XML, should be simple
    _server = 'dell-pe1950-01.rhts.eng.bos.redhat.com'
 
    def __init__(self, id=None, *args, **kw):
        if id is None:
            raise ValueException('Identifier cannot be None')
        self.id = id
        self.result_server = GraphiteConnection(self._server, port=2023) #This is the aggregator port

    def run(self, *args, **kw):
        """Prepare and execute hit on server

        run is responsible for implementing the details of how to generate an individual
        hit on a server. If the response time needs to be reported, decorate with @report
        """

        raise NotImplementedError('Subclasses or Request must define their own run() method')

        
class ClientRequest(Request):


    def __init__(self, cmd, params=None, keep_return=False,*args, **kw):
        super(ClientRequest, self).__init__(*args, **kw)
        self.cmd = cmd
        # FIXME setting params to '', bit of a hack ?
        self.params = ''
        self.keep_return = keep_return
        self.runnable_cmd = self.cmd.split(" ") + self.params.split(" ")

    @report
    def run(self):
        p = subprocess.Popen(self.runnable_cmd)
        self.stdout, self.stderr = p.communicate() #FIXME ensure these values are assigned correctly
        if self.keep_return:
            pass # FIXME put this data on a Queue() somewhere
        if self.stderr:
            # FIXME record error against this cmd perhaps in dict?
            return FAILED, self.stderr
        else:
            return PASSED, self.stdout

class HTTPRequest(Request):

    def __init__(self, *args, **kw):
        super(HTTPRequest, self).__init__(*args, **kw)

class XMLRPCRequest(HTTPRequest):

    def __init__(self, method, params=None, *args, **kw):
        super(XMLRPCRequest, self).__init__(*args, **kw)
        self.method = method
        self.params = params
        self.headers = {'Content-Type' : 'text/xml'}

    @report 
    def run(self):
        # FIXME do exception handling and params
        self.rpc = xmlrpclib.ServerProxy(self.server + self.xmlproxy, allow_none=True)
        for prop in self.method.split("."):
            self.rpc = getattr(self.rpc, prop)
        self.response = self.rpc(self.params) 
        return PASSED, self.response #FIXME need to check for errors


class LoadProcessor:


    """
    LoadProcessor takes elements from the load.xml and returns the data
    we care about in a form we can deal with
    """
    
    def __init__(self, *agrs, **kw):
        pass
       

    @classmethod
    def process(cls, element):
        f = getattr(cls, 'process_%s' % element.tag, None)
        if f is None:
            raise ValueError('%s is not a recognised load element' % element.tag)
        else:
            return f(element)

    @classmethod 
    def process_session(cls,session):
        session_deets = {}
        unit = session.get('unit')
        session_deets['duration_minutes'] = get_in_minutes(float(session.get('duration')), unit)
        return session_deets

    @classmethod
    def process_request(cls, request):
        request_deets = {}
        #equest_attributes = dict(request.items()) 
        request_deets['type'] = request.get('type')
        request_deets['interval_seconds'] = get_in_seconds(
            float(request.get('interval')), request.get('unit'))
        request_deets.update(dict([(k,v) for k,v in request.items() if k not in ['type', 'interval', 'unit']]))
        return request_deets

    @classmethod
    def process_param(cls, param):
        param_deets = {}
        param_deets[param.get('name')] = param.get('value')
        return param_deets 
