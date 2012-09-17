#!/usr/bin/python

__requires__ = ['TurboGears']

import sys
from turbogears import database, config as tg_config
from bkr.server.util import load_config


def feature(feature_type):
    def inner(f):
        f.feature_type = feature_type
        return f
    return inner

@feature('qpid connection')
def for_qpid():
    errors = []
    try:
        import qpid.messaging
        from qpid.log import enable, DEBUG, WARN, ERROR
        from qpid import datatypes
    except ImportError:
        errors.append('cannot load python qpid modules, please ensure they are installed')

    from bkr.server.message_bus import ServerBeakerBus
    try: #This will connect to the broker
        ServerBeakerBus()
    except Exception,e:
        errors.append('could not connect to QPID broker: %s' % str(e))

    return errors

@feature('python saslwrapper module')
def for_krb_and_qpid():
    errors=[]
    try:
        import saslwrapper
    except ImportError:
        errors.append('cannot load saslwrapper')
    return errors

@feature('sqlalchemy database connection')
def for_sqlalchemy():
    errors = []
    try:
        database.get_engine()
    except Exception,e:
        errors.append('cannot connect to database: %s' % str(e))
    return errors


def check(f):
    msg = 'Checking %s....' % (f.feature_type)
    errors = f()
    if errors:
        print msg,'\n'.join(errors)
        return 1
    else:
        print msg,'OK'
        return 0

def ignore(f):
    print 'Not using %s' % f.feature_type

def failed(yes):
    if yes:
        print 'Fail'
        sys.exit(1)
    else:
        print 'Passed'
        sys.exit(0)

def main():
    try:
        configfile = sys.argv[1]
    except IndexError:
        #No extra config
        configfile=None

    load_config(configfile)
    func_fail = False
    #Get our conf vars
    qpid = tg_config.get('beaker.qpid_enabled')
    krb_and_qpid = tg_config.get('beaker.qpid_krb_auth')

    # Now do the actual checking
    if qpid:
        qpid_fail = check(for_qpid)
        func_fail = qpid_fail | func_fail
        if qpid_fail and krb_and_qpid: # See if we can narrow down the problem
            func_fail = check(for_krb_and_qpid) | func_fail
    else:
        ignore(for_qpid)
        ignore(for_krb_and_qpid)

    func_fail = check(for_sqlalchemy) | func_fail

    print 'Finished checking'
    failed(func_fail)

if __name__ == '__main__':
    main()




