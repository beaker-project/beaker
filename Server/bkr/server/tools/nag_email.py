
# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
import datetime
from sqlalchemy.sql import and_
from sqlalchemy.orm import contains_eager, joinedload
from bkr.log import log_to_stream
from bkr.server.model import System, Reservation
from bkr.server.util import load_config
from turbogears import config
from turbogears.database import get_engine
from turbomail.control import interface
from bkr.server import mail
from optparse import OptionParser
import logging

log = logging.getLogger(__name__)

__version__ = '0.1'
__description__ = 'Beaker nag mail script'

USAGE_TEXT="""Usage: nag_email --threshold <hours>
"""

def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option('-r', '--reservation-type', default=u'manual',
            help='Send nag e-mails for this type of reservation (manual, recipe) [default: %default]')
    parser.add_option("-t","--threshold", default=3, type=int,
                      help="This is the number of days after a reservation of a machine takes place, that the nag emails will commence")
    parser.add_option("-c","--config-file",dest="configfile",default=None)
    parser.add_option("-d", "--dry-run", action="store_true", dest="testing")

    return parser

def usage():
    print USAGE_TEXT
    sys.exit(-1)
    
def main(): 
    current_date = None
    parser = get_parser() 
    opts,args = parser.parse_args()
    threshold = opts.threshold
    reservation_type = opts.reservation_type.decode(sys.stdin.encoding or 'utf8')
    testing   = opts.testing
    configfile = opts.configfile
    load_config(configfile)
    log_to_stream(sys.stderr)
    interface.start(config)
    get_engine()
    if testing:
        print 'Dry run only, nothing will be sent\n'
    identify_nags(threshold, reservation_type, testing)

def identify_nags(threshold, reservation_type, testing):
    query = System.query.options(joinedload(System.user))\
            .join(System.open_reservation).filter(and_(
            Reservation.start_time <= datetime.datetime.utcnow()
                - datetime.timedelta(days=threshold),
            Reservation.type == reservation_type,
            # Only get those systems are not owner==user
            Reservation.user_id != System.owner_id))\
            .options(contains_eager(System.open_reservation))
    for system in query:
        recipient =  system.user.email_address
        subject = "[Beaker Reminder]: System %s" % system.fqdn
        body = "You have had this System since %s, please return it if you are no longer using it." % system.open_reservation.start_time
        sender = config.get('beaker_email')
        if not sender:
            log.warning("beaker_email not defined in app.cfg; unable to send mail")
            return
        if testing:
            print "From: %s\nTo: %s\nSubject: %s\nBody: %s\n\n" % (sender,recipient,subject,body)
        else:
            mail.send_mail(sender=sender,to=recipient,subject=subject,body=body)

if __name__ == "__main__":
    main()
