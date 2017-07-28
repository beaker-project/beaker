
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
from datetime import datetime, timedelta
from sqlalchemy.sql import and_, or_, func
from bkr.common import __version__
from bkr.log import log_to_stream
from bkr.server.model import User, System, Reservation, Recipe, \
    RecipeSet, Job, Watchdog, RecipeTask, Task, TaskStatus, RecipeResource
from bkr.server.util import load_config_or_exit
from turbogears import config
from turbomail.control import interface
from bkr.server import mail
from sqlalchemy.orm import joinedload
from optparse import OptionParser
from bkr.server.util import absolute_url
import logging

log = logging.getLogger(__name__)

__description__ = 'Beaker usage reminder system'


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option("-c", "--config-file", dest="configfile", default=None)
    parser.add_option('--reservation-expiry', type=int, metavar='HOURS', default=24,
                      help='Warn about reservations expiring less than HOURS in the future [default: %default]')
    parser.add_option('--reservation-length', type=int, metavar='DAYS', default=3,
                      help='Report systems which have been reserved for longer than DAYS [default: %default]')
    parser.add_option('--waiting-recipe-age', type=int, metavar='HOURS', default=1,
                      help='Warn about recipes which have been waiting for longer than HOURS [default: %default]')
    parser.add_option('--delayed-job-age', type=int, metavar='DAYS', default=14,
                      help='Warn about jobs which have been queued for longer than DAYS [default: %default]')
    parser.add_option("-d", "--dry-run", action="store_true", dest="testing")
    return parser


class BeakerUsage(object):

    def __init__(self, user, reservation_expiry, reservation_length,
                 waiting_recipe_age, delayed_job_age):
        self.user = user
        self.reservation_expiry = reservation_expiry
        self.reservation_length = reservation_length
        self.waiting_recipe_age = waiting_recipe_age
        self.delayed_job_age = delayed_job_age

    def expiring_reservations(self):
        """
        Get expiring reservations
        """
        tasks = Task.by_name(u'/distribution/reservesys')
        query = Recipe.query\
            .join(Recipe.recipeset).join(RecipeSet.job).filter(Job.owner == self.user)\
            .join(Recipe.watchdog).join(Watchdog.recipetask)\
            .join(Recipe.resource)\
            .filter(or_(RecipeTask.task == tasks, Recipe.status == TaskStatus.reserved))\
            .filter(Watchdog.kill_time <= (datetime.utcnow() + timedelta(hours=self.reservation_expiry)))\
            .values(Watchdog.kill_time, RecipeResource.fqdn)
        return list(query)

    def open_in_demand_systems(self):
        """
        Get Open Loans & Reservations for In Demand Systems
        """
        # reservations for in demand systems
        waiting_recipes = System.query.join(System.queued_recipes)\
            .filter(Recipe.status == TaskStatus.queued)\
            .join(Recipe.recipeset)\
            .filter(RecipeSet.queue_time <= (datetime.utcnow() - timedelta(hours=self.waiting_recipe_age)))\
            .with_entities(System.id, func.count(System.id).label('waiting_recipes_count'))\
            .group_by(System.id).subquery()
        # For sqlalchemy < 0.7, query.join() takes an onclause as in the following:
        # query.join((target, onclause), (target2, onclause2), ...)
        query = Reservation.query.filter(Reservation.user == self.user)\
            .join(Reservation.system)\
            .join((waiting_recipes, Reservation.system_id == waiting_recipes.c.id))\
            .filter(Reservation.start_time <= (datetime.utcnow() - timedelta(days=self.reservation_length)))\
            .filter(Reservation.finish_time == None)\
            .values(Reservation.start_time, waiting_recipes.c.waiting_recipes_count, System.fqdn)

        reservations = []
        for start_time, count, fqdn in query:
            duration = (datetime.utcnow() - start_time).days
            reservations.append((duration, count, fqdn))
        # TODO: Open Loans
        return reservations

    def delayed_jobs(self):
        """
        Get Delayed Jobs
        """
        query = Job.query.filter(Job.owner == self.user)\
            .join(Job.recipesets)\
            .filter(and_(RecipeSet.queue_time <= (datetime.utcnow() - timedelta(days=self.delayed_job_age)),
                    RecipeSet.status == TaskStatus.queued))\
            .group_by(Job.id)\
            .values(func.min(RecipeSet.queue_time), Job.id)
        return [(queue_time, absolute_url('/jobs/%s' % job_id))
                for queue_time, job_id in query]


def main(*args):
    parser = get_parser()
    (options, args) = parser.parse_args(*args)
    load_config_or_exit(options.configfile)
    log_to_stream(sys.stderr)
    interface.start(config)
    reservation_expiry = options.reservation_expiry
    reservation_length = options.reservation_length
    waiting_recipe_age = options.waiting_recipe_age
    delayed_job_age = options.delayed_job_age
    testing = options.testing

    if testing:
        print 'Dry run only, nothing will be sent\n'

    for user in User.query:
        beaker_usage = BeakerUsage(user, reservation_expiry, reservation_length,
                                   waiting_recipe_age, delayed_job_age)
        expiring_reservations = beaker_usage.expiring_reservations()
        open_in_demand_systems = beaker_usage.open_in_demand_systems()
        delayed_jobs = beaker_usage.delayed_jobs()
        if (expiring_reservations or open_in_demand_systems or delayed_jobs):
            data = {
                'user_name': user.user_name,
                'current_date': datetime.utcnow().strftime("%Y-%m-%d"),
                'beaker_fqdn': absolute_url('/'),
                'reservation_expiry': reservation_expiry,
                'reservation_length': reservation_length,
                'waiting_recipe_age': waiting_recipe_age,
                'delayed_job_age': delayed_job_age,
                'expiring_reservations': expiring_reservations,
                'open_reservations': open_in_demand_systems,
                'delayed_jobs': delayed_jobs
            }
            mail.send_usage_reminder(user, data, testing)
    return

if __name__ == '__main__':
    sys.exit(main())
