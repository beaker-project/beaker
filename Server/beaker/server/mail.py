"""
mail methods for Beaker

Copyright 2008-2009, Red Hat, Inc
Bill Peck <bpeck@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import turbomail

from turbogears import config
import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
#logging.getLogger('sqlalchemy.orm.unitofwork').setLevel(logging.DEBUG)

log = logging.getLogger(__name__)


def send_mail(sender, to, subject, body):
    from turbomail import MailNotEnabledException
    message = turbomail.Message(sender, to, subject)
    message.plain = body
    try:
        #log.debug("Sending mail: %s" % message.plain)
        turbomail.send(message)
    except MailNotEnabledException:
        log.warning("TurboMail is not enabled!")
    except Exception, e:
        log.error("Exception thrown when trying to send mail: %s" % str(e))

def failed_recipes(job):
    msg = "JobID: %s Status: %s Result: %s\n" % \
             (job.id, job.status, job.result)
    for recipeset in job.recipesets:
        if recipeset.is_failed():
            msg = "%s\tRecipeSetID: %s\n" % ( msg, recipeset.id )
            for recipe in recipeset.recipes:
                if recipe.is_failed():
                    msg = "%s\t\tRecipeID: %s Arch: %s System: %s Distro: %s OSVersion: %s Status: %s Result: %s\n" \
                           % (msg, recipe.id, recipe.distro.arch, recipe.system, recipe.distro,
                              recipe.distro.osversion, recipe.status, recipe.result)
                    for task in recipe.tasks:
                        if task.is_failed():
                            msg = "%s\t\t\tTaskID: %s TaskName: %s StartTime: %s Duration: %s Status: %s Result: %s\n" \
                               % (msg, task.id, task.task.name, task.start_time, task.duration,
                                  task.status, task.result)
    return msg

def job_notify(job, sender=None):
    """ Send a completion notification to job owner """
    if not sender:
        sender = config.get('beaker_email')
    if not sender:
        log.warning("beaker_email not defined in app.cfg; unable to send mail")
        return
    send_mail(sender, 
              job.owner.email_address,
              '[Beaker Job Completion] [%s] %s %s' % (job.id, job.status, job.result),
              failed_recipes(job))
