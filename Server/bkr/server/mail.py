
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
mail methods for Beaker
"""

from turbogears import config
import turbomail
import logging
from bkr.server.util import absolute_url
from datetime import datetime
from jinja2 import Environment, PackageLoader
# configure Jinja2 to load email templates
template_env = Environment(loader=PackageLoader('bkr.server', 'mail-templates'), trim_blocks=True)

log = logging.getLogger(__name__)


def send_mail(sender, to, subject, body, bulk=True, **kwargs):
    from turbomail import MailNotEnabledException
    try:
        message = turbomail.Message(sender, to, subject, **kwargs)
        if bulk:
            message.headers.extend([
                ('Auto-Submitted', 'auto-generated'),
                ('Precedence', 'bulk'),
            ])
        message.plain = body
        turbomail.send(message)
    except MailNotEnabledException:
        log.warning("TurboMail is not enabled!")
    except Exception:
        log.exception("Exception thrown when trying to send mail")

def failed_recipes(job):
    msg = "JobID: %s Status: %s Result: %s <%s>\n" % \
             (job.id, job.status, job.result, absolute_url('/jobs/%s' % job.id))
    for recipeset in job.recipesets:
        if recipeset.is_failed():
            msg = "%s\tRecipeSetID: %s\n" % ( msg, recipeset.id )
            for recipe in recipeset.recipes:
                if recipe.is_failed():
                    distro_name = recipe.installation.distro_name if recipe.installation.distro_name else \
                        recipe.distro_tree.distro.name if recipe.distro_tree else "Unknown"
                    arch = recipe.installation.arch.arch if recipe.installation.arch else recipe.distro_tree.arch.arch \
                        if recipe.distro_tree else "Unknown"
                    msg = "%s\t\tRecipeID: %s Arch: %s System: %s Distro: %s Status: %s Result: %s <%s>\n" \
                          % (msg, recipe.id, arch, recipe.resource, distro_name, recipe.status, recipe.result,
                             absolute_url('/recipes/%s' % recipe.id))

                    for task in recipe.tasks:
                        if task.is_failed():
                            msg = "%s\t\t\tTaskID: %s TaskName: %s StartTime: %s Duration: %s Status: %s Result: %s\n" \
                               % (msg, task.id, task.name, task.start_time, task.duration,
                                  task.status, task.result)
    return msg

def job_notify(job, sender=None):
    """ Send a completion notification to job owner, and to job CC list if any. """
    if job.owner.notify_job_completion:
        if not sender:
            sender = config.get('beaker_email')
        if not sender:
            log.warning("beaker_email not defined in app.cfg; unable to send mail")
            return
        send_mail(sender=sender, to=job.owner.email_address, cc=job.cc,
                  subject='[Beaker Job Completion] [%s/%s] %s%s%s' % (job.status,
                        job.result, job.id, job.whiteboard and u': ' or u'', job.whiteboard or u''),
                  body=failed_recipes(job),
                  headers=[('X-Beaker-Notification', 'job-completion'),
                           ('X-Beaker-Job-ID', job.id)])

def _sender_details(user):
    return u'%s (via Beaker) <%s>' % (user.display_name, user.email_address)

def system_loan_request(system, message, requester, requestee_email):
    sender = _sender_details(requester)
    body = [_(u'A Beaker user has requested you loan them the system\n%s <%s>.\n'
        'Here is a copy of their request:\n'
        '%s\n Requested by: %s')
        % (system.fqdn, absolute_url('/view/%s' % system.fqdn),
        message, requester.display_name), '']

    headers=[('X-Beaker-Notification', 'loan-request'),
        ('X-Beaker-System', system.fqdn),
        ('X-Lender', system.lender or ''),
        ('X-Owner', system.owner),
        ('X-Location', system.location or ''),
        ('X-Lab-Controller', system.lab_controller or ''),
        ('X-Vendor', system.vendor or ''),
        ('X-Type', system.type)]

    arch_headers = [('X-Arch', arch) for arch in system.arch]
    headers.extend(arch_headers)
    cc = [requester.email_address] + system.cc
    send_mail(sender, requestee_email, _(u'Loan request for %s') % system.fqdn,
        '\n'.join(body), cc=cc, bulk=False, headers=headers)

def system_problem_report(system, description, recipe=None, reporter=None):
    if reporter is not None:
        sender = _sender_details(reporter)
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
    headers=[('X-Beaker-Notification', 'system-problem'),
        ('X-Beaker-System', system.fqdn),
        ('X-Lender', system.lender or ''),
        ('X-Owner', system.owner),
        ('X-Location', system.location or ''),
        ('X-Lab-Controller', system.lab_controller or ''),
        ('X-Vendor', system.vendor or ''),
        ('X-Type', system.type)]
    arch_headers = [('X-Arch', arch) for arch in system.arch]
    headers.extend(arch_headers)
    cc = []
    if reporter is not None:
        cc.append(reporter.email_address)
    cc.extend(system.cc)
    send_mail(sender, system.owner.email_address,
            _(u'Problem reported for %s') % system.fqdn, '\n'.join(body),
            cc=cc, bulk=False, headers=headers)

def broken_system_notify(system, reason, recipe=None):
    if system.owner.notify_broken_system:
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
                         ('X-Beaker-System', system.fqdn),
                         ('X-Lender', system.lender or ''),
                         ('X-Owner', system.owner),
                         ('X-Location', system.location or ''),
                         ('X-Lab-Controller', system.lab_controller or ''),
                         ('X-Vendor', system.vendor or ''),
                         ('X-Type', system.type)] +
                        [('X-Arch', arch) for arch in system.arch])


def system_loan_notify(system, loanee, agent):
    if not system.owner.notify_system_loan:
        return
    if system.owner == agent:
        # No need to inform them about their own actions
        return
    sender = config.get('beaker_email')
    if not sender:
        log.warning("beaker_email not defined in app.cfg; unable to send mail")
        return
    # loanee None means that the loan has been returned
    if loanee is None:
        subject = _(u'System %s loan returned') % system.fqdn
    else:
        subject = _(u'System %s loaned to %s') % (system.fqdn, loanee.user_name)
    template = template_env.get_template('system-loan.txt')
    body = template.render(system=system, loanee=loanee, agent=agent, absolute_url=absolute_url)
    send_mail(sender=sender, to=system.owner.email_address, cc=system.cc,
              subject=subject, body=body,
              headers=[('X-Beaker-Notification', 'system-loan'),
                       ('X-Beaker-System', system.fqdn)])


def group_membership_notify(user, group, agent, action):
    """ Send a group membership change notification to the user """
    if user.notify_group_membership:
        sender = config.get('beaker_email')
        if not sender:
            log.warning("beaker_email not defined in app.cfg; unable to send mail")
            return

        email_data = {'Added': {'Subject':'Added to Beaker group %s' % group.group_name,
                                'Body': 'You have been %s to %s group by %s <%s>.'
                                % (action.lower(), group.group_name, agent.user_name, agent.email_address)
                                },
                      'Removed': {'Subject':'Removed from Beaker group %s' % group.group_name,
                                  'Body': 'You have been %s from %s group by %s <%s>.'
                                  % (action.lower(), group.group_name, agent.user_name, agent.email_address)
                                  }}
        try:
            subject = email_data[action]['Subject']
            body = email_data[action]['Body']
        except KeyError:
            raise ValueError('Unknown action: %s. (Expected one of %r)' %
                             (action, email_data.keys()))
        else:
            send_mail(sender=sender, to=user.email_address,
                      subject='[Group Membership] %s' % subject,
                      body=body,
                      headers=[('X-Beaker-Notification', 'group-membership'),
                               ('X-Beaker-Group', group.group_name),
                               ('X-Beaker-Group-Action',action)])

def reservesys_notify(recipe):
    """ Send a system reservation notification to 
    job owner, and to job CC list if any. """
    job = recipe.recipeset.job
    if job.owner.notify_reservesys:
        owner = job.owner.email_address
        sender = config.get('beaker_email')
        if not sender:
            log.warning("beaker_email not defined in app.cfg; unable to send mail")
            return
        subject = '[Beaker System Reserved] %s' % recipe.resource.fqdn
        template = template_env.get_template('reservesys.txt')
        body = template.render(recipe=recipe, job=job, absolute_url=absolute_url)
        send_mail(sender=sender, to=owner, cc=job.cc, subject=subject, body=body,
                  headers=[('X-Beaker-Notification', 'system-reservation'),
                           ('X-Beaker-Job-ID', job.id)])

def send_usage_reminder(user, data={}, testing=False):
    sender = config.get('beaker_email')
    if not sender:
        log.warning("beaker_email not defined in app.cfg; unable to send mail")
        return
    template = template_env.get_template('beaker-usage.txt')
    recipient = user.email_address
    subject = u'[Beaker] Usage report for %s (%s)' % (user.user_name, datetime.utcnow().strftime("%Y-%m-%d"))
    body = template.render(data)
    if testing:
        print "From: %s\nTo: %s\nSubject: %s\nBody: %s\n\n" % (sender, recipient, subject, body)
    else:
        send_mail(sender=sender, to=recipient, subject=subject, body=body,
                  headers=[('X-Beaker-Notification', 'usage-report')])
