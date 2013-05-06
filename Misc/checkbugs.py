#!/usr/bin/python

"""
Just a little script to report on the status of bugs slated against a given 
release.

Before running this, make sure that you have set your username in 
~/.bugzillarc:

[bugzilla.redhat.com]
user = someone@redhat.com

and that you have obtained a Bugzilla session cookie by executing:

$ bugzilla login
"""

BUGZILLA_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'
GERRIT_HOSTNAME = 'gerrit.beaker-project.org'
GERRIT_SSH_PORT = 29418

import sys
import os
import subprocess
from itertools import chain
import simplejson as json
from optparse import OptionParser
import bugzilla # yum install python-bugzilla

# These are in Python 2.6
def any(iterable):
    for x in iterable:
        if x:
            return True
    return False
def all(iterable):
    for x in iterable:
        if not x:
            return False
    return True

def get_bugs(milestone, release, sprint, states):
    bz = bugzilla.Bugzilla(url=BUGZILLA_URL)
    # Make sure the user has logged themselves in properly, otherwise we might 
    # accidentally omit private bugs from the list
    if not bz.user:
        raise RuntimeError('Configure your username in ~/.bugzillarc')
    if bz._proxy.User.valid_cookie(dict(login=bz.user))['cookie_isvalid'] != 1:
        raise RuntimeError('Invalid BZ credentials, try running "bugzilla login"')
    criteria = {'product': 'Beaker'}
    if milestone:
        criteria['target_milestone'] = milestone
    if sprint:
        criteria['devel_whiteboard'] = sprint
    if release:
        criteria['flag'] = ['beaker-%s+' % release]
    if states:
        criteria['status'] = list(states)
    return bz.query(bz.build_query(**criteria))

def get_gerrit_changes(bug_ids):
    p = subprocess.Popen(['ssh',
            '-o', 'StrictHostKeyChecking=no', # work around ssh bug on RHEL5
            '-p', str(GERRIT_SSH_PORT), GERRIT_HOSTNAME,
            'gerrit', 'query', '--format=json', '--current-patch-set',
            ' OR '.join('bug:%d' % bug_id for bug_id in bug_ids)],
            stdout=subprocess.PIPE)
    stdout, _ = p.communicate()
    assert p.returncode == 0, p.returncode
    retval = []
    for line in stdout.splitlines():
        obj = json.loads(line)
        if obj.get('type') == 'stats':
            continue
        retval.append(obj)
    return retval

def changes_for_bug(changes, bug_id):
    for change in changes:
        change_bugs = [int(t['id']) for t in change['trackingIds'] if t['system'] == 'Bugzilla']
        if bug_id in change_bugs:
            yield change

def abbrev_user(user):
    if user.endswith('@redhat.com'):
        return user[:-len('@redhat.com')]

def _git_call(*args):
    command = ['git']
    command.extend(args)
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError("Git call failed: %s" % stderr)
    return stdout

_revlist = None
def build_git_revlist():
    global _revlist
    git_status = _git_call('status')
    if "branch is behind" in git_status:
        raise RuntimeError("Git clone is not up to date")
    _revlist = _git_call('rev-list', 'HEAD').splitlines()

def git_commit_reachable(sha):
    return sha in _revlist

def problem(message):
    if os.isatty(sys.stdout.fileno()):
        print '\033[1m\033[91m** %s\033[0m' % message
    else:
        print '** %s' % message

_status_order = [
    'NEW',
    'ASSIGNED',
    'POST',
    'MODIFIED',
    'ON_QA',
    'VERIFIED',
    'RELEASE_PENDING',
    'CLOSED'
]
_status_keys = dict((v, str(k)) for k, v in enumerate(_status_order))

def bug_sort_key(bug):
    status_key = _status_keys.get(bug.status, bug.status)
    return status_key, bug.assigned_to, bug.bug_id

def main():
    parser = OptionParser('usage: %prog [options]',
            description='Reports on the state of Beaker bugs for a given milestone')
    parser.add_option('-m', '--milestone', metavar='MILESTONE',
            help='Check bugs slated for MILESTONE')
    parser.add_option('-r', '--release', metavar='RELEASE',
            help='Check bugs approved for RELEASE (using flags)')
    parser.add_option('-s', '--sprint', metavar='SPRINT',
            help='Check bugs approved for SPRINT (using devel whiteboard)')
    parser.add_option('-i', '--include', metavar='STATE', action="append",
            help='Include bugs in the specified state (may be given multiple times')
    parser.add_option('-q', '--quiet', action="store_false",
            dest="verbose", default=True,
            help='Only display problem reports')
    options, args = parser.parse_args()
    if not (options.milestone or options.release or options.sprint):
        parser.error('Specify a milestone, release or sprint')

    if options.verbose:
        print "Building git revision list for HEAD"
    build_git_revlist()
    if options.verbose:
        print "Retrieving bug list from Bugzilla"
    bugs = get_bugs(options.milestone, options.release, options.sprint,
                    options.include)
    bug_ids = set(bug.bug_id for bug in bugs)
    if options.verbose:
        print "  Retrieved %d bugs" % len(bugs)
        print "Retrieving code review details from Gerrit"
    changes = get_gerrit_changes(bug_ids)
    if options.verbose:
        print "  Retrieved %d patch reviews" % len(changes)

    for bug in sorted(bugs, key=bug_sort_key):
        if options.verbose:
            print 'Bug %-13d %-17s %-10s <%s>' % (bug.bug_id, bug.bug_status,
                    abbrev_user(bug.assigned_to), bug.url)
        bug_changes = list(changes_for_bug(changes, bug.bug_id))

        # print out summary of changes
        for change in sorted(bug_changes, key=lambda c: int(c['number'])):
            patch_set = change['currentPatchSet']
            verified = max(chain([None], (int(a['value'])
                    for a in patch_set.get('approvals', []) if a['type'] == 'VRIF'))) or 0
            reviewed = max(chain([None], (int(a['value'])
                    for a in patch_set.get('approvals', []) if a['type'] == 'CRVW'))) or 0
            if options.verbose:
                print '    Change %-6s %-17s %-10s <%s>' % (change['number'],
                        '%s (%d/%d)' % (change['status'], verified, reviewed),
                        abbrev_user(change['owner']['email']), change['url'])

        # check for inconsistencies
        if bug.bug_status in ('NEW', 'ASSIGNED') and \
                any(change['status'] != 'ABANDONED' for change in bug_changes):
            if all(change['status'] == 'MERGED' for change in bug_changes):
                problem('Bug %s should be MODIFIED, not %s' % (bug.bug_id, bug.bug_status))
            else:
                problem('Bug %s should be POST, not %s' % (bug.bug_id, bug.bug_status))
        elif bug.bug_status == 'POST' and \
                not any(change['status'] == 'NEW' for change in bug_changes):
            if bug_changes and all(change['status'] == 'MERGED' for change in bug_changes):
                problem('Bug %s should be MODIFIED, not %s' % (bug.bug_id, bug.bug_status))
            else:
                problem('Bug %s should be ASSIGNED, not %s' % (bug.bug_id, bug.bug_status))
        elif bug.bug_status in ('MODIFIED', 'ON_DEV', 'ON_QA', 'VERIFIED', 'RELEASE_PENDING', 'CLOSED'):
            if bug.bug_status == 'CLOSED' and bug.resolution == 'DUPLICATE':
                if bug.dupe_of not in bug_ids:
                    target_kind = "release" if options.release else "milestone"
                    problem('Bug %s marked as DUPLICATE of %s, which is not in this %s'
                                              % (bug.bug_id, bug.dupe_of, target_kind))
            elif not bug_changes:
                problem('Bug %s should be ASSIGNED, not %s' % (bug.bug_id, bug.bug_status))
            elif not all(change['status'] in ('ABANDONED', 'MERGED') for change in bug_changes):
                problem('Bug %s should be POST, not %s' % (bug.bug_id, bug.bug_status))
        if options.release and bug.target_milestone != options.release:
            if bug.get_flag_status("hss_hot_fix") != "+":
                problem('Bug %s target milestone should be %s, not %s' %
                                (bug.bug_id, options.release, bug.target_milestone))
            elif bug.target_milestone == "---":
                problem('Bug %s target milestone should be set for hotfix release' %
                            (bug.bug_id,))
        for change in bug_changes:
            if change['status'] == 'MERGED' and change['project'] == 'beaker':
                sha = change['currentPatchSet']['revision']
                if not git_commit_reachable(sha):
                    problem('Bug %s: Commit %s is not reachable from HEAD' % (bug.bug_id, sha))

        if options.verbose:
            print

    if options.release:
        # check for bugs which have target milestone set but aren't approved for the release
        target_bugs = get_bugs(options.release, None, None, options.include)
        approved_bug_ids = set(b.bug_id for b in bugs)
        for unapproved in [b for b in target_bugs if b.bug_id not in approved_bug_ids]:
            problem('Bug %s target milestone is set, but bug is not approved' %
                            (unapproved.bug_id,))

if __name__ == '__main__':
    main()
