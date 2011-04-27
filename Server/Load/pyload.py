#  Copyright (c) 2008-2009 Corey Goldberg (corey@goldb.org)
#
#  Multithreaded HTTP Load Generator


import time
from datetime import datetime, timedelta
import sys
import os
import re
import httplib
from threading import Thread
from multiprocessing import Process, Queue
from request import RequestFactory, FAILED, PASSED, Request, LoadProcessor
import ConfigParser
from lxml import etree

now = datetime.now

def main():
    manager = LoadManager()
    manager.start()


class LoadManager:


    def __init__(self):
        self.start_time = now()
        self.agents = []
        self._build_agents()

    def _build_agents(self):
        """Builds agents that generate load

           Agents are built from Request types (i.e XMLRPC, Client, QPID), 
           which are a sub class of multipriocessing.Process.
           the type is determined from the 'type' attribute in the <request/> of the
           load.xml
        """
        dom = etree.parse(open('load.xml'))
        config = dom.xpath('//config')[0]
        config_options = {}
        for section in config.getchildren():
            setattr(Request, section.tag, section.get('value', None))
        sessions = dom.xpath('//session')
        for session in sessions:
            the_session = LoadProcessor.process(session)
            for request in session.getchildren():
                the_request = LoadProcessor.process(request)
                for elem in request.getchildren(): 
                    if elem.tag == 'param':
                        the_request['params'] = LoadProcessor.process(elem)
                type = the_request['type']
                del the_request['type']
                agent = LoadAgent(RequestFactory.create(type, **the_request), the_session['duration_minutes'], the_request['interval_seconds'])
                self.agents.append(agent)

    def start(self, threads=1, interval=0, rampup=0, verify_regex='.*'):
        """Run all LoadAgents
           
        Each LoadAgent runs as a sepereate Process and will generate 
        requests (load) upon the server,
        It will have it's own individual timing that duration that 
        it needs to adhere to (as dictated by the load.xml)

        """
        # start the agent threads
        for agent in self.agents:
            print 'Starting new agent' #FIXME add in detail here
            agent.start()

class LoadAgent(Process):

    def __init__(self, request, duration_minutes, interval_seconds):
        Process.__init__(self)
        self.duration = timedelta(minutes=duration_minutes)
        self.interval = timedelta(seconds=interval_seconds)
        self.request = request
                   
    def run(self):
        """Runs individual request/hit as thread

        Keeps track of duration and timing interval to ensure that
        requests are generated according to expectexd request hit rate and
        duration. 
        """
        self.expiration_time = now() + self.duration
        # expiration time might be milliseconds behind expected due to start being
        # a different value
        while True:
            run_thread = Thread(target=self.request.run)
            run_thread.setDaemon(True)
            try:
                start = now()
                print '%s Making Request' % start
                run_thread.start()
                #res = Request.results_queue.get(True)
                #print res
            except Exception, e:
                print e
            interval_wait = self.interval.total_seconds() 
            if self.expiration_time < now():
                break #We are finished
            print 'Waiting for  %s' % interval_wait
            time.sleep(interval_wait)
                
    def __send(self, msg):
        if USE_SSL:
            conn = httplib.HTTPSConnection(msg[0])
        else:
            conn = httplib.HTTPConnection(msg[0])
        try:
            #conn.set_debuglevel(1)
            conn.request('GET', msg[1])
            resp = conn.getresponse()
            resp_body = resp.read()
            resp_code = resp.status
        except Exception, e:
            raise Exception('Connection Error: %s' % e)
        finally:
            conn.close()
        return (resp_body, resp_code)
    

    def __verify(self, resp_body, resp_code, compiled_verify_regex):
        if resp_code >= 400:
            raise ValueError('Response Error: HTTP %d Response' % resp_code)
        if not re.search(compiled_verify_regex, resp_body):
            raise Exception('Verification Error: Regex Did Not Match Response')
        return True      



class ResultWriter(Thread):
    def __init__(self, q, start_time):
        Thread.__init__(self)
        self.q = q
        self.start_time = start_time
    
    def run(self):
        f = open('results.csv', 'a')
        while True:
            print 'Queue size in ResultWriter is %s' % self.q.qsize()
            q_tuple = self.q.get(True)
            trans_end_time, response_time, status, output = q_tuple
            elapsed = (trans_end_time - self.start_time)
            response_time_seconds = response_time.total_seconds()
            elapsed_seconds = elapsed.total_seconds()
            f.write('%.3f,%.3f,%s,%s\n' % (elapsed_seconds, response_time_seconds, status, output))
            f.flush()
            print '%.3f' % response_time_seconds



if __name__ == '__main__':
    main()
