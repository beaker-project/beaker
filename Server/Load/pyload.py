#  Copyright (c) 2008-2009 Corey Goldberg (corey@goldb.org)
#
#  Multithreaded HTTP Load Generator


import time
from datetime import datetime, timedelta
import sys
import os
import re
import httplib
import logging
from optparse import OptionParser
from threading import Thread
from multiprocessing import Process, Queue
import ConfigParser
from lxml import etree

_default_log_lvl = 'error'
now = datetime.now

def _parser():
    parser = OptionParser()
    parser.add_option('-l','--log', 
        help="sets log level")
    return parser

def main():
    parser = _parser()
    (opts, args) = parser.parse_args()
    if not opts.log:
        opts.log = _default_log_lvl
    lvl = getattr(logging, opts.log.upper(), logging.ERROR)
    logging.basicConfig(level=lvl)
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
        """
        from request import RequestFactory, FAILED, PASSED, Request, LoadProcessor, get_rate_in_seconds, User
        from load_session import Session
        dom = etree.parse(open('load.xml'))
        config = dom.xpath('//config')[0]
        config_options = {}
        for section in config.getchildren():
            # XXX use another function/class to do this work with a dispatch table or somehing
            if section.tag == 'baseload':
                Session.baseload[section.get('session')] = \
                    get_rate_in_seconds(section.get('requests'), section.get('unit'))
            elif section.tag =='server':
                setattr(Request, section.tag, section.get('value', None))
            elif section.tag == 'xmlproxy':
                 setattr(Request, section.tag, section.get('value', None))
        load_profile = dom.xpath('/root/load/user')
        for user in load_profile:
            processed_user = LoadProcessor.process(user)
            load_level = processed_user['load_level'] 
            session = processed_user['session']
            duration_minutes = processed_user['duration_minutes']
            delay = processed_user['delay'] 
            agent = LoadAgent(User(duration_minutes, load_level, session), delay)
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

    def __init__(self, user, delay=0):
        Process.__init__(self)
        self.user = user
        self.delay=delay
                   
    def run(self):
        """Runs individual request/hit as thread

        Keeps track of duration and timing interval to ensure that
        requests are generated according to expectexd request hit rate and
        duration. 
        """
        expiration_time = now() + timedelta(minutes=self.user.duration_minutes)
        # expiration time might be milliseconds behind expected due to start being
        # a different value
        interval_seconds = self.user.interval.total_seconds()
        time.sleep(self.delay)
        while True:
            run_thread = Thread(target=self.user.run)
            run_thread.setDaemon(False)
            try:
                start = now()
                print '%s Run user' % start
                run_thread.start()
            except Exception, e:
                print e
            if expiration_time < now():
                break #We are finished
            print 'Waiting for  %s' % interval_seconds
            time.sleep(interval_seconds)
                
    
class ResultWriter(Thread):
    def __init__(self, q, start_time):
        Thread.__init__(self)
        self.q = q
        self.start_time = start_time
    
    def run(self):
        f = open('results.csv', 'a')
        while True:
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
