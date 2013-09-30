#!/usr/bin/env python

"""
Just a little script to create JIRA tracking issues for Bugzilla bugs.

See checkbugs.py and jirainfo.py for Bugzilla and JIRA setup requirements.
"""

from optparse import OptionParser
from pprint import pprint

# Initially using basic auth, will eventually switch to Kerberos
from getpass import getpass
try:
    from jirainfo import JiraInfo
except ImportError:
    raise ImportError("Could not import jirainfo. Is the virtualenv active?")
from checkbugs import BugzillaInfo

################################################
# Creating JIRA tracking issues
################################################

# Retrieves bugs from Bugzilla (bugzilla.redhat.com)
# Ensures they have a corresponding tracking issue in JIRA

def main():
    parser = OptionParser('usage: %prog [options]',
            description='Create tracking issues in JIRA for Bugzilla bugs')
    # TODO: Allow importing specific bugs
    # parser.add_option('-b', '--bug', metavar='BUG_ID',
    #        target='bugs', action="append",
    #        help='Check/import specific bug (may be given multiple times)')
    parser.add_option('-m', '--milestone', metavar='MILESTONE',
            help='Check/import bugs slated for MILESTONE')
    parser.add_option('-r', '--release', metavar='RELEASE',
            help='Check/import bugs approved for RELEASE (using flags)')
    parser.add_option('-i', '--include', metavar='STATE', action="append",
            help='Include bugs in the specified state '
                 '(may be given multiple times)')
    # Initially, dryrun only...
    parser.add_option('--dryrun', action='store_true',
            help="Skip creating tracking issues in JIRA")
    parser.add_option('-q', '--quiet', action="store_false",
            dest="verbose", default=True,
            help='Only report newly created tracking issues')
    options, args = parser.parse_args()
    if not (options.milestone or options.release):
        parser.error('Specify a milestone or release')

    # Bugzilla bugs
    if options.verbose:
        print "Retrieving bug list from Bugzilla"
    bz_info = BugzillaInfo()
    bugs = bz_info.get_bugs(options.milestone, options.release, None,
                            options.include)
    if options.verbose:
        print "  Retrieved %d bugs" % len(bugs)

    # JIRA tracking issues
    if options.verbose:
        print "Retrieving Bugzilla tracking issues from JIRA"
    jira = JiraInfo("bz2jira", getpass)
    jira_bz_issues = list(jira.iter_bz_issues())
    if options.verbose:
        print ("  Retrieved %d issues with Bugzilla refs" %
                                                        len(jira_bz_issues))

    # Create tracking issues for any open bugs that don't already have one
    created_issues = 0
    for bug in bugs:
        if options.verbose:
           print ('Checking BZ#%s' % (bug.bug_id,))
        if bug.bug_status == 'CLOSED':
            if options.verbose:
                print ('  BZ#%s already CLOSED, skipping' % (bug.bug_id,))
            continue

        # Ensure any still open issues are listed in the JIRA backlog
        try:
            issue = jira.get_bz_issue(bug.bug_id)
        except KeyError:
            pass
        else:
            if options.verbose:
                print ('  BZ#%s already tracked as %s, skipping' %
                          (bug.bug_id, issue.id))
            continue

        # Actually create the issue
        if options.verbose:
            print ('  Creating tracking issue for BZ#%s' % (bug.bug_id,))
        created_issues += 1
        if options.dryrun:
            print ('  Dry run, not creating issue for BZ#%s' %
                      (bug.bug_id,))
            if options.verbose:
                pprint(jira.derive_bz_issue_details(bug))
        else:
            issue = jira.create_bz_issue(bug)
            print ('  BZ#%s now tracked as %s' % (bug.bug_id, issue.id))

    if options.verbose:
        if created_issues:
            print ('Created %d new tracking issues in JIRA' % created_issues)
        else:
            print ('No new tracking issues needed')

if __name__ == '__main__':
    main()
