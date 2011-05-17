import subprocess
import random
import load_session
import function as function_module
import xmlrpclib
import logging
import time
import Queue
from datetime import datetime, timedelta
from graphite_connector import GraphiteConnection

now = datetime.now
FAILED = 'fail'
PASSED = 'pass'

def get_in_minutes(number, unit):
    if unit == 'minute':
        return float(number)
    if unit =='hour':
        return float(number) * 60
    if unit == 'second':
        return float(number) / 60.0

def get_in_seconds(number, unit):
    if unit == 'second':
        return float(number)
    if unit == 'minute':
        return float(number) * 60
    if unit == 'hour':
        return float(number) * 3600

def get_rate_in_seconds(number, unit):
    if unit == 'second':
        return float(number)
    if unit == 'minute':
        return float(number) / 60
    if unit == 'hour':
        return float(number) / 3600

    
class RequestFactory:

    @classmethod
    def create(cls, type, *args, **kw):
        req = None
        if type == 'xmlrpc':
            req = XMLRPCRequest(*args, **kw)
        if type == 'http':
            req = HTTPRequest(*args, **kw)
        if type == 'qpid':
            req = QPIDRequest(*args, **kw)
        if type == 'client':
            req = ClientRequest(*args, **kw)
        if req is None:
            raise ValueException('% is not a value Request type' % type)
        class_name = req.__class__.__name__
        if not req.error_queue.get(class_name):
            req.error_queue[class_name] = list()
        if not req.result_queue.get(class_name):
            req.result_queue[class_name] = {}
        return req

class Request(object):

    result_queue = {}
    error_queue = {}

    #FIXME get this from a config or XML, should be simple
 
    def __init__(self, keep_return=False, *args, **kw):
        self.keep_return = keep_return
        self.id = random.random()
        pass


    def run(self, *args, **kw):
        """Prepare and execute hit on server

        run is responsible for implementing the details of how to generate an individual
        hit on a server.
        """

        raise NotImplementedError('Subclasses or Request must define their own run() method')

        
class ClientRequest(Request):

  
    def __init__(self, cmd, args=None,  keep_return=False, *a, **kw):
        super(ClientRequest, self).__init__(*a, **kw)
        self.cmd = cmd
        # FIXME setting params to '', bit of a hack ?
        self.keep_return = keep_return
        self.cmd = self.cmd.split(" ") 
        #FIXME put outside of __init__
        self.args = args or []

    def run(self):
        runnable_cmd = self.cmd
        for arg in self.args:
            if callable(arg):
                arg = arg()
            runnable_cmd.append(arg)
        logging.info('Running %s' % runnable_cmd)
        p = subprocess.Popen(runnable_cmd)
        stdout, stderr = p.communicate() #FIXME ensure these values are assigned correctly
        if self.keep_return:
            all_requests = self.result_queue[self.__class__.__name__]
            this_request = all_requests.get(self.id, None)
            if this_request is None:
                all_requests[self.id] = [stdout]
            else:
                all_requests[self.id].append(stdout)

        if stderr:
            # FIXME record error
            return FAILED, stderr
        else:
            return PASSED, stdout

class HTTPRequest(Request):

    def __init__(self, *args, **kw):
        super(HTTPRequest, self).__init__(*args, **kw)

class XMLRPCRequest(HTTPRequest):

    def __init__(self, method, param=None, *args, **kw):
        super(XMLRPCRequest, self).__init__(*args, **kw)
        self.method = method
        self.param = param
        self.headers = {'Content-Type' : 'text/xml'}

    def run(self):
        # FIXME do exception handling and params
        self.rpc = xmlrpclib.ServerProxy(self.server + self.xmlproxy, allow_none=True)
        for prop in self.method.split("."):
            self.rpc = getattr(self.rpc, prop)
        logging.debug('Calling RPC %s' % self.method)
        self.response = self.rpc(self.param) 
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
    def process_user(cls, user):
        user_deets = {}
        unit = user.get('unit')
        user_deets['load_level'] = user.get('load-level')
        user_deets['session'] = user.get('session')
        user_deets['duration_minutes'] = get_in_minutes(user.get('duration'), user.get('unit'))
        delay = user.get('delay', 0)
        user_deets['delay'] = get_in_seconds(delay, user.get('unit'))
        return user_deets

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

    @classmethod
    def process_arg(cls, arg):
        arg_deets = {}
        if arg.get('type') == 'function':
            arg_deets['function_arg'] = arg.get('value')

        elif arg.get('type') == 'file':
            # Nothing special being done with file types, if this remains so,
            # then let's remove this if statement
            arg_deets['args'] = arg.get('value')
        else:
            arg_deets['args'] = arg.get('value')
        return arg_deets 

class User(object):

    def __init__(self, duration_minutes, load_level, session_name):
        self.duration_minutes = duration_minutes
        self.session = SessionFactory.create(session_name)()
        if load_level == 'x': # if we want to blitzkreig the server
            self.interval = timedelta(seconds=0)
        else:
            # XXX do try/except for division errors
            self.interval = timedelta(seconds=self.session.baseload.get(session_name) / float(load_level))

    def run(self):
        return self.session.run()

class SessionFactory(object):

    @classmethod
    def create(cls, session_name):
        _temp = __import__('load_session', globals(), locals(), [session_name])
        session_ref = getattr(_temp, session_name)
        if session_ref is None:
            raise ValueError('%s is not a valid session' % session_name) 

        return session_ref.Session  
