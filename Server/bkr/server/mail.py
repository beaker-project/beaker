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


from turbogears import config, url
import turbomail
import logging
from bkr.server.util import absolute_url

log = logging.getLogger(__name__)


def send_mail(sender, to, subject, body, **kwargs):
    from turbomail import MailNotEnabledException
    message = turbomail.Message(sender, to, subject, **kwargs)
    message.plain = body
    try:
        #log.debug("Sending mail: %s" % message.plain)
        turbomail.send(message)
    except MailNotEnabledException:
        log.warning("TurboMail is not enabled!")
    except Exception, e:
        log.exception("Exception thrown when trying to send mail")

def failed_recipes(job):
    msg = "JobID: %s Status: %s Result: %s <%s>\n" % \
             (job.id, job.status, job.result, absolute_url('/jobs/%s' % job.id))
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
    """ Send a completion notification to job owner, and to job CC list if any. """
    if not sender:
        sender = config.get('beaker_email')
    if not sender:
        log.warning("beaker_email not defined in app.cfg; unable to send mail")
        return
    send_mail(sender=sender, to=job.owner.email_address, cc=job.cc,
              subject='[Beaker Job Completion] [%s] %s %s' % (job.id, job.status, job.result),
              body=failed_recipes(job),
              headers=[('X-Beaker-Notification', 'job-completion'),
                       ('X-Beaker-Job-ID', job.id)])

def system_problem_report(system, description, recipe=None, reporter=None):
    if reporter is not None:
        sender = u'%s (via Beaker) <%s>' % (reporter.display_name, reporter.email_address)
    else:
        sender = config.get('beaker_email')
    if not sender:
        log.warning("beaker_email not defined in app.cfg; unable to send mail")
        return
    body = [_(u'A Beaker user has reported a problem with system \n%s <%s>.')
            % (system.fqdn, absolute_url('/view/%s' % system.fqdn)), '']
    if reporter is not None:
        body.append(_(u'Reported by: %s') % reporter.display_name)
    if recipe is not None:
        body.append(_(u'Related to: %s <%s>') % (recipe.t_id,
                absolute_url('/recipes/%s' % recipe.id)))
    body.extend(['', unicode(_(u'Problem description:')), description])
    send_mail(sender, system.owner.email_address,
            _(u'Problem reported for %s') % system.fqdn, '\n'.join(body),
            cc=system.cc,
            headers=[('X-Beaker-Notification', 'system-problem'),
                     ('X-Beaker-System', system.fqdn)])

def broken_system_notify(system, reason, recipe=None):
    sender = config.get('beaker_email')
    if not sender:
        log.warning("beaker_email not defined in app.cfg; unable to send mail")
        return
    body = [_(u'Beaker has automatically marked system \n%s <%s> \nas broken, due to:')
            % (system.fqdn, absolute_url('/view/%s' % system.fqdn)), '', reason, '',
            unicode(_(u'Please investigate this error and take appropriate action.')), '']
    if recipe:
        body.extend([_(u'Failure occurred in %s <%s>') % (recipe.t_id,
                absolute_url('/recipes/%s' % recipe.id)), ''])
    if system.power:
        body.extend([_(u'Power type: %s') % system.power.power_type.name,
                     _(u'Power address: %s') % system.power.power_address,
                     _(u'Power id: %s') % system.power.power_id])
    send_mail(sender, system.owner.email_address,
            _(u'System %s automatically marked broken') % system.fqdn,
            '\n'.join(body),
            cc=system.cc,
            headers=[('X-Beaker-Notification', 'system-broken'),
                     ('X-Beaker-System', system.fqdn)])
