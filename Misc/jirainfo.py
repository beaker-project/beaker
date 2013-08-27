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

Kerberos login is not currently supported, so checkbugs is configured to
prompt for a password with getpass
"""

import os.path
from ConfigParser import RawConfigParser as ConfigParser
from jira.client import JIRA
from collections import namedtuple

JIRA_CONFIG = os.path.expanduser("~/.beaker-jira.cfg")
CONFIG_DIR = os.path.dirname(JIRA_CONFIG)
BZ_ISSUE_CRITERIA = 'summary ~ "BZ#" or cf[10400] is not NULL'
EXTERNAL_LINK_FIELD = "customfield_10400"

def relative_config_path(target):
    return os.path.normpath(os.path.join(CONFIG_DIR, target))

class IssueSummary(namedtuple("IssueSummary",
                              ["id", "status", "summary", "bz_link",
                               "bz_summary_ref", "bz_link_ref"])):
    pass

class JiraInfo(object):

    def __init__(self, config_section, getpasscb=None):
        cfg = ConfigParser({"verify": None})
        cfg_files = cfg.read(JIRA_CONFIG)
        if not cfg_files:
            raise RuntimeError("Please provide %s" % JIRA_CONFIG)
        server = cfg.get(config_section, "server")
        verify = cfg.get(config_section, "verify")
        username = cfg.get(config_section, "username")
        project = cfg.get(config_section, "project")
        options = {"server": server}
        if verify:
            options["verify"] = relative_config_path(verify)
        if getpasscb is None:
            raise RuntimeError("Kerberos auth not yet supported")
        self._jira = jira = JIRA(options, basic_auth=(username, getpasscb()))
        # Retrieving every issue that references bugzilla probably won't
        # scale as the project accumulates more issues, but it'll do for now
        self._issues = jira.search_issues('project=%s and type != Sub-task '
                                          'and (%s)' %
                                          (project, BZ_ISSUE_CRITERIA),
                                          maxResults=10000)
        self._make_bz_caches()

    def _make_bz_caches(self):
        self._bz_link_cache = link_cache = {}
        self._bz_summary_cache = summary_cache = {}
        for issue in self._issues:
            issue_info = issue.fields
            summary = issue_info.summary.strip()
            bz_summary_ref, __, __ = summary.partition(" ")
            if bz_summary_ref.startswith("BZ#"):
                bz_summary_ref = int(bz_summary_ref[3:])
            else:
                bz_summary_ref = None
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
                v = IssueSummary(issue.key, issue_info.status.name,
                                 summary, external_url,
                                 bz_summary_ref, bz_link_ref)
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

if __name__ == "__main__":
    from getpass import getpass
    info = JiraInfo("checkbugs", getpass)
    for issue in info.iter_bz_issues():
        print tuple(issue)
