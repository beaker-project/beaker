import sys
from bkr.server.model import *
from bkr.server.util import load_config
from turbogears import config
from turbogears.database import session, get_engine
from turbomail.control import interface
from bkr.server import mail
from optparse import OptionParser

__version__ = '0.1'
__description__ = 'Beaker nag mail script'

USAGE_TEXT="""Usage: nag_email --threshold <hours>
"""

def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option("-s","--service", default='WEBUI',
                      help="Report on this service (WEBUI,SCHEDULER), Default is WEBUI")
    parser.add_option("-t","--threshold", default=3,
                      help="This is the number of days after a reservation of a machine takes place, that the nag emails will commence")
    parser.add_option("-c","--config-file",dest="configfile",default=None)
    return parser

def usage():
    print USAGE_TEXT
    sys.exit(-1)
    
def main():
    current_date = None
    parser = get_parser() 
    opts,args = parser.parse_args()
    threshold = opts.threshold
    service   = opts.service
    
    configfile = opts.configfile

    load_config(configfile)
    interface.start(config)
    get_engine()
    identify_nags(threshold, service)

def identify_nags(threshold, service):
    sys_activities = System.reserved_via(service)
    for activity in sys_activities: 
        date_reserved =  activity.created
        date_now = datetime.fromtimestamp(time.time())
        threshold_delta = timedelta(days=threshold)
        if date_reserved + threshold_delta > date_now: #Let's send them a reminder
            system = System.query().filter_by(id=activity.system_id).one()
            recipient =  system.user.email_address
            subject = "[Beaker Reminder]: System %s" % system.fqdn
            body = "You have had this System since %s, please return it if you are no longer using it" % activity.created 
            sender = config.get('beaker_email')
            mail.send_mail(sender=sender,to=recipient,subject=subject,body=body)

if __name__ == "__main__":
    main()
