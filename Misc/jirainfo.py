#!/usr/bin/env python

"""
Helper for sprint tracking in JIRA/Greenhopper

jira-python isn't packaged for Fedora & has non-trivial dependencies
so you'll need to set up a virtual environment to use it

  yum install python-pip python-virtualenv python-virtualenvwrapper

  # Put this part in ~/.bashrc
  export WORKON_HOME=~/.virtualenvs
  export VIRTUALENVWRAPPER_VIRTUALENV_ARGS='--system-site-packages --distribute'
  source /usr/bin/virtualenvwrapper.sh
  export PIP_VIRTUALENV_BASE=$WORKON_HOME
  export PIP_RESPECT_VIRTUALENV=true
  export PIP_REQUIRE_VIRTUALENV=true

  # Run this once
  mkvirtualenv jira_python
  pip install jira-python

  # Do this to activate the virtualenv when needed
  workon jira_python

The JIRA support needs to know where to find the JIRA instance. Create a
"~/.beaker-jira.cfg" file with the following contents:

  [checkbugs]
  server=<JIRA server HTTPS URL>
  verify=<custom CA cert if needed (leave out if default cert bundle is OK)>
  username=<JIRA username>
  project=<JIRA project name>

  [bz2jira]
  server=<JIRA server HTTPS URL>
  verify=<custom CA cert if needed (leave out if default cert bundle is OK)>
  username=<JIRA username>
  project=<JIRA project name>

checkbugs only needs read-only access (if not using --syncjirainfo),
bz2jira always needs write access (hence the separate config sections)

Kerberos login is not currently supported, so checkbugs is configured to
prompt for a password with getpass
"""

import os.path
from ConfigParser import RawConfigParser as ConfigParser
from jira.client import JIRA
from collections import namedtuple

JIRA_CONFIG = os.path.expanduser("~/.beaker-jira.cfg")
CONFIG_DIR = os.path.dirname(JIRA_CONFIG)
BZ_ISSUE_CRITERIA = ('(type=Bug or type=Improvement or type="New Feature") and '
                    '(summary ~ "BZ#" or cf[10400] is not NULL)')
EXTERNAL_LINK_FIELD = "customfield_10400"
STORY_POINTS_FIELD = "customfield_10002"

TRACKING_ISSUE_DESCRIPTION = """\
[BZ#%s|%s] tracking issue created by {{Misc/bz2jira.py}}.
Use {{Misc/checkbugs.py}} to ensure bug and issue states are aligned.
"""

def relative_config_path(target):
    return os.path.normpath(os.path.join(CONFIG_DIR, target))

class IssueDetails(namedtuple("IssueDetails",
                              ["id", "status", "summary", "description",
                               "target_version", "story_points",
                               "bz_link", "bz_summary_ref", "bz_link_ref",
                               "apiref"])):
    pass

class JiraInfo(object):

    def __init__(self, config_section, getpasscb=None, retrieve_info=True):
        cfg = ConfigParser({"verify": None})
        cfg_files = cfg.read(JIRA_CONFIG)
        if not cfg_files:
            raise RuntimeError("Please provide %s" % JIRA_CONFIG)
        server = cfg.get(config_section, "server")
        verify = cfg.get(config_section, "verify")
        username = cfg.get(config_section, "username")
        self._jira_project = project = cfg.get(config_section, "project")
        options = {"server": server}
        if verify:
            options["verify"] = relative_config_path(verify)
        if getpasscb is None:
            raise RuntimeError("Kerberos auth not yet supported")
        self._jira = jira = JIRA(options, basic_auth=(username, getpasscb()))
        if retrieve_info:
            self.retrieve_info()

    def retrieve_info(self):
        jira = self._jira
        project = self._jira_project
        self._versions = dict((v.name, v)
                                for v in jira.project(project).versions)
        # Retrieving every issue that references bugzilla probably won't
        # scale as the project accumulates more issues, but it'll do for now
        issues = jira.search_issues('project=%s and (%s)' %
                                          (project, BZ_ISSUE_CRITERIA),
                                          maxResults=10000)
        bz_issues = []
        for issue in issues:
            summary = issue.fields.summary.strip()
            external_link = getattr(issue.fields, EXTERNAL_LINK_FIELD) or ""
            if summary.startswith("BZ#") or "bugzilla" in external_link:
                bz_issues.append(issue)
        self._issues = bz_issues
        self._make_bz_caches()

    def _make_bz_caches(self):
        self._bz_link_cache = link_cache = {}
        self._bz_summary_cache = summary_cache = {}
        for issue in self._issues:
            issue_info = issue.fields
            # Extract summary and summary ref to BZ (if any)
            summary = issue_info.summary.strip()
            bz_summary_ref, __, __ = summary.partition(" ")
            if bz_summary_ref.startswith("BZ#"):
                bz_summary_ref = int(bz_summary_ref[3:])
            else:
                bz_summary_ref = None
            # Extract external link and link ref to BZ (if any)
            external_url = getattr(issue_info, EXTERNAL_LINK_FIELD)
            bz_link_ref = None
            if external_url is not None:
                # Currently assume all external links are to Bugzilla
                __, __, bz_link_ref_str = external_url.partition("=")
                if bz_link_ref_str:
                    bz_link_ref = int(bz_link_ref_str)
            # TODO?: Handle the case where multiple JIRA issues refer to the
            # same BZ entry (e.g. reopened bugs)
            if bz_link_ref or bz_summary_ref:
                # Extract description
                description = issue_info.description
                if description is None:
                    description = ""
                else:
                    description = description.strip()

                # Extract target version
                #   - assume at most one target version
                #   - anything in the backlog is implicitly 1.0 material
                if issue_info.fixVersions:
                    target_version = issue_info.fixVersions[0].name
                else:
                    target_version = u"1.0"

                # Extract story points
                story_points = getattr(issue_info, STORY_POINTS_FIELD)
                v = IssueDetails(issue.key, issue_info.status.name,
                                 summary, description, target_version,
                                 story_points, external_url,
                                 bz_summary_ref, bz_link_ref, issue)
                if bz_link_ref:
                    link_cache[bz_link_ref] = v
                # Catch cases where the link is not set, or disagrees with
                # the summary
                if bz_summary_ref and bz_summary_ref != bz_link_ref:
                    summary_cache[bz_summary_ref] = v

    def iter_bz_issues(self):
        for v in self._bz_link_cache.values():
            yield v
        for v in self._bz_summary_cache.values():
            yield v

    def get_bz_issue(self, bug_id):
        try:
            return self._bz_link_cache[bug_id]
        except KeyError:
            return self._bz_summary_cache[bug_id]

    def _get_target_version(self, target_milestone):
        # "N.M.x" as a milestone effectively means the same thing as "N.M.1"
        target_version = target_milestone.replace("x", "1")
        version_details = {"id": self._versions[target_version].id}
        return target_version, version_details

    def get_target_version(self, target_milestone):
        try:
            return self._get_target_version(target_milestone)[0]
        except KeyError:
            return target_milestone

    def update_description(self, issue, description):
        issue.apiref.update(description=description)

    def update_story_points(self, issue, story_points):
        issue.apiref.update(fields={STORY_POINTS_FIELD: story_points})

    def update_target_version(self, issue, target_milestone):
        target_version, version_details = self._get_target_version(target_milestone)
        issue.apiref.update(fixVersions=[version_details])

    def derive_bz_issue_details(self, bug):
        summary = bug.summary
        # Strip the two most common RFE prefixes, don't worry about others
        # TODO: copy the regex from BugBot's RFE detection
        if summary.startswith("RFE:"):
            summary = summary[4:]
        elif summary.startswith("[RFE]"):
            summary = summary[5:]
        summary = summary.strip()
        issue_summary = 'BZ#%s %s' % (bug.bug_id, summary)
        if 'FutureFeature' in bug.keywords:
            issue_type = 'Improvement'
        else:
            issue_type = 'Bug'
        story_points = bug.estimated_time if bug.estimated_time else None
        description = TRACKING_ISSUE_DESCRIPTION % (bug.bug_id, bug.weburl)
        issue_details = {
            "project": {"key": self._jira_project},
            "summary": issue_summary,
            "issuetype": {"name": issue_type},
            "description": description,
            EXTERNAL_LINK_FIELD: bug.weburl,
            STORY_POINTS_FIELD: story_points
        }

        if bug.target_milestone.startswith(u"0."):
            target_version, version_details = self._get_target_version(bug.target_milestone)
            issue_details["fixVersions"] = [version_details]
        else:
            target_version = u"1.0"
        return issue_details, target_version

    def create_bz_issue(self, bug):
        details, target_version = self.derive_bz_issue_details(bug)
        issue = self._jira.create_issue(fields=details)
        return IssueDetails(issue.key, "To Do",
                            details["summary"],
                            details["description"],
                            target_version,
                            details[STORY_POINTS_FIELD],
                            details[EXTERNAL_LINK_FIELD],
                            bug.bug_id, bug.bug_id, issue)

    def get_bz_verification_subtask(self, bug):
        issue = self.get_bz_issue(bug.bug_id).apiref
        expected_summary = "Verify BZ#%s" % bug.bug_id
        verify_subtasks = [st for st in issue.fields.subtasks
                               if st.fields.summary.startswith("Verify")]
        return verify_subtasks[0].key if verify_subtasks else None

    def create_bz_verification_subtask(self, bug):
        issue = self.get_bz_issue(bug.bug_id).apiref
        subtask_summary = "Verify BZ#%s" % bug.bug_id
        subtask_details = {
            "project": {"key": self._jira_project},
            "summary": subtask_summary,
            "issuetype": {"name": "Sub-task"},
            "parent": {"key": issue.key},
            "assignee": None,
        }
        subtask = self._jira.create_issue(fields=subtask_details)
        return subtask.key

if __name__ == "__main__":
    from getpass import getpass
    info = JiraInfo("checkbugs", getpass)
    for issue in info.iter_bz_issues():
        print tuple(issue)
