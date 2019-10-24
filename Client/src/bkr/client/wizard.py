# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# FYI, many issues encounter using Python 2 version can be fixed by setting
# several environmental variables:
#
# LANG='en_US.UTF-8'
# LC_ALL='en_US.UTF-8'
# PYTHONIOENCODING='UTF8'
#
# Most modern Linux systems do this by default though
# but some users still can have different LANG

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math

DESCRIPTION = """Beaker Wizard is a tool which can transform that
"create all the necessary files with correct names, values, and paths"
boring phase of every test creation into one-line joy. For power
users there is a lot of inspiration in the man page. For quick start
just ``cd`` to your test package directory and simply run
``beaker-wizard``.
"""

__doc__ = """
beaker-wizard: Tool to ease the creation of a new Beaker task
=============================================================

.. program:: beaker-wizard

Synopsis
--------

| :program:`beaker-wizard` [*options*] <testname> <bug>

The *testname* argument should be specified as::

    [[[NAMESPACE/]PACKAGE/]TYPE/][PATH/]NAME

which can be shortened as you need::

    TESTNAME
    TYPE/TESTNAME
    TYPE/PATH/TESTNAME
    PACKAGE/TYPE/NAME
    PACKAGE/TYPE/PATH/NAME
    NAMESPACE/PACKAGE/TYPE/NAME
    NAMESPACE/PACKAGE/TYPE/PATH/NAME

| :program:`beaker-wizard` Makefile

This form will run the Wizard in the Makefile edit mode which allows you to
quickly and simply update metadata of an already existing test while trying to
keep the rest of the Makefile untouched.

Description
-----------

%(DESCRIPTION)s

The beaker-wizard was designed to be flexible: it is intended not only for
beginning Beaker users who will welcome questions with hints but also for
experienced test writers who can make use of the extensive command-line
options to push their new-test-creating productivity to the limits.

For basic usage help, see Options_ below or run ``beaker-wizard -h``.
For advanced features and expert usage examples, read on.

Highlights
~~~~~~~~~~

* provide reasonable defaults wherever possible
* flexible confirmation (``--every``, ``--common``, ``--yes``)
* predefined skeletons (beaker, beakerlib, simple, multihost, library, parametrized, empty)
* saved user preferences (defaults, user skeletons, licenses)
* Bugzilla integration (fetch bug info, reproducers, suggest name, description)
* Makefile edit mode (quick adding of bugs, limiting archs or releases...)
* automated adding created files to the git repository

Skeletons
~~~~~~~~~

Another interesting feature is that you can save your own skeletons into
the preferences file, so that you can automatically populate the new
test scripts with your favourite structure.

All of the test related metadata gathered by the Wizard can be expanded
inside the skeletons using XML tags. For example: use ``<package/>`` for
expanding into the test package name or ``<test/>`` for the full test name.

The following metadata variables are available:

* test namespace package type path testname description
* bugs reproducers requires architectures releases version time
* priority license confidential destructive
* skeleton author email

Options
-------

-h, --help        show this help message and exit
-V, --version     display version info and quit

Basic metadata:
  -d DESCRIPTION  short description
  -a ARCHS        architectures [All]
  -r RELEASES     releases [All]
  -o PACKAGES     run for packages [wizard]
  -q PACKAGES     required packages [wizard]
  -t TIME         test time [5m]

Extra metadata:
  -z VERSION      test version [1.0]
  -p PRIORITY     priority [Normal]
  -l LICENSE      license [GPLv2+]
  -i INTERNAL     confidential [No]
  -u UGLY         destructive [No]

Author info:
  -n NAME         your name [Petr Splichal]
  -m MAIL         your email address [psplicha@redhat.com]

Test creation specifics:
  -s SKELETON     skeleton to use [beakerlib]
  -j PREFIX       join the bug prefix to the testname [Yes]
  -f, --force     force without review and overwrite existing files
  -w, --write     write preferences to ~/.beaker_client/wizard
  -b, --bugzilla  contact bugzilla to get bug details
  -g, --git       add created files to the git repository

Confirmation and verbosity:
  -v, --verbose   display detailed info about every action
  -e, --every     prompt for each and every available option
  -c, --common    confirm only commonly used options [Default]
  -y, --yes       yes, I'm sure, no questions, just do it!

Examples
--------

Some brief examples::

    beaker-wizard overload-performance 379791
        regression test with specified bug and name
        -> /CoreOS/perl/Regression/bz379791-overload-performance

    beaker-wizard buffer-overflow 2008-1071 -a i386
        security test with specified CVE and name, i386 arch only
        -> /CoreOS/perl/Security/CVE-2008-1071-buffer-overflow

    beaker-wizard Sanity/options -y -a?
        sanity test with given name, ask just for architecture
        -> /CoreOS/perl/Sanity/options

    beaker-wizard Sanity/server/smoke
        add an optional path under test type directory
        -> /CoreOS/perl/Sanity/server/smoke

    beaker-wizard -by 1234
        contact bugzilla for details, no questions, just review
        -> /CoreOS/installer/Regression/bz1234-Swap-partition-Installer

    beaker-wizard -byf 2007-0455
        security test, no questions, no review, overwrite existing files
        -> /CoreOS/gd/Security/CVE-2007-0455-gd-buffer-overrun

All of the previous examples assume you're in the package tests
directory (e.g. ``cd git/tests/perl``). All the necessary directories and
files are created under this location.

Bugzilla integration
~~~~~~~~~~~~~~~~~~~~

The following example creates a regression test for bug #227655.
Option ``-b`` is used to contact Bugzilla to automatically fetch bug
details and ``-y`` to skip unnecessary questions.

::

    # beaker-wizard -by 227655
    Contacting bugzilla...
    Fetching details for bz227655
    Examining attachments for possible reproducers
    Adding test.pl (simple test using Net::Config)
    Adding libnet.cfg (libnet.cfg test config file)

    Ready to create the test, please review
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    /CoreOS/perl/Regression/bz227655-libnet-cfg-in-wrong-directory

                 Namespace : CoreOS
                   Package : perl
                 Test type : Regression
             Relative path : None
                 Test name : bz227655-libnet-cfg-in-wrong-directory
               Description : Test for bz227655 (libnet.cfg in wrong directory)

        Bug or CVE numbers : bz227655
      Reproducers to fetch : test.pl, libnet.cfg
         Required packages : None
             Architectures : All
                  Releases : All
                   Version : 1.0
                      Time : 5m

                  Priority : Normal
                   License : GPLv2+
              Confidential : No
               Destructive : No

                  Skeleton : beakerlib
                    Author : Petr Splichal
                     Email : psplicha@redhat.com

    [Everything OK?]
    Directory Regression/bz227655-libnet-cfg-in-wrong-directory created
    File Regression/bz227655-libnet-cfg-in-wrong-directory/PURPOSE written
    File Regression/bz227655-libnet-cfg-in-wrong-directory/runtest.sh written
    File Regression/bz227655-libnet-cfg-in-wrong-directory/Makefile written
    Attachment test.pl downloaded
    Attachment libnet.cfg downloaded

Command line
~~~~~~~~~~~~

The extensive command line syntax can come in handy for example
when creating a bunch of sanity tests for a component. Let's
create a test skeleton for each of wget's feature areas::

    # cd git/tests/wget
    # for test in download recursion rules authentication; do
    >   beaker-wizard -yf $test -t 10m -q httpd,vsftpd \\
    >       -d "Sanity test for $test options"
    > done

    ...

    /CoreOS/wget/Sanity/authentication

                 Namespace : CoreOS
                   Package : wget
                 Test type : Sanity
             Relative path : None
                 Test name : authentication
               Description : Sanity test for authentication options

        Bug or CVE numbers : None
      Reproducers to fetch : None
         Required packages : httpd, vsftpd
             Architectures : All
                  Releases : All
                   Version : 1.0
                      Time : 10m

                  Priority : Normal
                   License : GPLv2+
              Confidential : No
               Destructive : No

                  Skeleton : beakerlib
                    Author : Petr Splichal
                     Email : psplicha@redhat.com

    Directory Sanity/authentication created
    File Sanity/authentication/PURPOSE written
    File Sanity/authentication/runtest.sh written
    File Sanity/authentication/Makefile written

    # tree
    .
    `-- Sanity
        |-- authentication
        |   |-- Makefile
        |   |-- PURPOSE
        |   `-- runtest.sh
        |-- download
        |   |-- Makefile
        |   |-- PURPOSE
        |   `-- runtest.sh
        |-- recursion
        |   |-- Makefile
        |   |-- PURPOSE
        |   `-- runtest.sh
        `-- rules
            |-- Makefile
            |-- PURPOSE
            `-- runtest.sh

Notes
-----

If you provide an option with a "?" you will be given a list of
available options and a prompt to type your choice in.

For working Bugzilla integration you need ``python-bugzilla`` package installed on your system.
If you are trying to access a bug with restricted access, log
in to Bugzilla first with the following command::

    bugzilla login

You will be asked for email and password and after successfully logging in a
``~/.bugzillacookies`` file will be created which then will be used
in all subsequent Bugzilla queries. Logout can be performed with
``rm ~/.bugzillacookies`` ;-)

Files
-----

All commonly used preferences can be saved into ``~/.beaker_client/wizard``.
Use "write" command to save current settings when reviewing gathered
test data or edit the file with you favourite editor.

All options in the config file are self-explanatory. For confirm level choose
one of: nothing, common or everything.

Library tasks
-------------

The "library" skeleton can be used to create a "library task". It allows you to bundle
together common functionality which may be required across multiple
tasks. To learn more, see `the BeakerLib documentation for library
tasks <https://github.com/beakerlib/beakerlib/wiki/man#rlimport>`__.

Bugs
----

If you encounter an issue or have an idea for enhancement, please `file a new bug`_.
See also `open bugs`_.

.. _file a new bug: https://bugzilla.redhat.com/enter_bug.cgi?product=Beaker&component=command+line&short_desc=beaker-wizard:+&status_whiteboard=BeakerWizard&assigned_to=psplicha@redhat.com
.. _open bugs: https://bugzilla.redhat.com/buglist.cgi?product=Beaker&bug_status=__open__&short_desc=beaker-wizard&short_desc_type=allwordssubstr

See also
--------

* `Beaker documentation <http://beaker-project.org/help.html>`_
* `BeakerLib <https://github.com/beakerlib/beakerlib>`_
""" % globals()

from optparse import OptionParser, OptionGroup, IndentedHelpFormatter, SUPPRESS_HELP
from xml.dom.minidom import parse, parseString
from datetime import date
from time import sleep
import subprocess
import textwrap
import pwd
import sys
import re
import os

# Python 2 Unicode compatibility
# wrap stdout in utf-8 writer so we don't have to encode
# everything that goes to print or stdout
if sys.version_info.major == 2:
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

# Version
WizardVersion = "2.3.2"

# Regular expressions
RegExpPackage    = re.compile("^(?![._+-])[.a-zA-Z0-9_+-]+(?<![._-])$")
RegExpRhtsRequires = re.compile("^(?![._+-])[.a-zA-Z0-9_+-/()]+(?<![._-])$")
RegExpPath       = re.compile("^(?![/-])[a-zA-Z0-9/_-]+(?<![/-])$")
RegExpTestName   = re.compile("^(?!-)[a-zA-Z0-9-_]+(?<!-)$")
RegExpReleases   = re.compile("^(?!-)[a-zA-Z0-9-_]+(?<!-)$")
RegExpBug        = re.compile("^\d+$")
RegExpBugLong    = re.compile("^bz\d+$")
RegExpBugPrefix  = re.compile("^bz")
RegExpCVE        = re.compile("^\d{4}-\d{4,}$")
RegExpCVELong    = re.compile("^CVE-\d{4}-\d{4}$")
RegExpCVEPrefix  = re.compile("^CVE-")
RegExpEmail      = re.compile("^[a-z._-]+@[a-z.-]+$")
RegExpYes        = re.compile("Everything OK|y|ye|jo|ju|ja|ano|da", re.I)
RegExpReproducer = re.compile("repr|test|expl|poc|demo", re.I)
RegExpScript     = re.compile("\.(sh|py|pl)$")
RegExpMetadata   = re.compile("(\$\(METADATA\):\s+Makefile.*)$", re.S)
RegExpTest       = re.compile("TEST=(\S+)", re.S)
RegExpVersion    = re.compile("TESTVERSION=([\d.]+)", re.S)

# Suggested test types (these used to be enforced)
SuggestedTestTypes = """Regression Performance Stress Certification
            Security Durations Interoperability Standardscompliance
            Customeracceptance Releasecriterium Crasher Tier1 Tier2
            Alpha KernelTier1 KernelTier2 Multihost MultihostDriver
            Install FedoraTier1 FedoraTier2 KernelRTTier1
            KernelReporting Sanity Library""".split()

# Guesses
pwd_uinfo = pwd.getpwuid(os.getuid())

# pw_name and pw_gecos are in ASCII encoding
GuessAuthorLogin = pwd_uinfo.pw_name
try:
    GuessAuthorName = u'{}'.format(pwd_uinfo.pw_gecos.decode("utf-8"))
except AttributeError:
    GuessAuthorName = pwd_uinfo.pw_gecos

GuessAuthorDomain = re.sub("^.*\.([^.]+\.[^.]+)$", "\\1", os.uname()[1])
GuessAuthorEmail = "%s@%s" % (GuessAuthorLogin, GuessAuthorDomain)

# Make sure guesses are valid values
if not RegExpEmail.match(GuessAuthorEmail):
    GuessAuthorEmail = "your@email.com"

# Commands
GitCommand="git add".split()

# Constants
MaxLengthSuggestedDesc = 50
MaxLengthTestName = 50
ReviewWidth = 22
MakefileLineWidth = 17
VimDictionary = "# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k"
BugzillaUrl = 'https://bugzilla.redhat.com/show_bug.cgi?id='
BugzillaXmlrpc = 'https://bugzilla.redhat.com/xmlrpc.cgi'
PreferencesDir = os.getenv('HOME') + "/.beaker_client"
PreferencesFile = PreferencesDir + "/wizard"
PreferencesTemplate = """<?xml version="1.0" ?>

<wizard>
    <author>
        <name>%s</name>
        <email>%s</email>
        <confirm>common</confirm>
        <skeleton>beakerlib</skeleton>
    </author>
    <test>
        <time>5m</time>
        <type>Sanity</type>
        <prefix>Yes</prefix>
        <namespace>CoreOS</namespace>
        <priority>Normal</priority>
        <license>GPLv2+</license>
        <confidential>No</confidential>
        <destructive>No</destructive>
    </test>
    <licenses>
        <license name="GPLvX">
            This is GPLvX license text.
        </license>
        <license name="GPLvY">
            This is GPLvY license text.
        </license>
        <license name="GPLvZ">
            This is GPLvZ license text.
        </license>
    </licenses>
    <skeletons>
        <skeleton name="skel1" requires="gdb" rhtsrequires="library(perl/lib1) library(scl/lib2)">
            This is skeleton 1 example.
        </skeleton>
        <skeleton name="skel2">
            This is skeleton 2 example.
        </skeleton>
        <skeleton name="skel3">
            This is skeleton 3 example.
        </skeleton>
    </skeletons>
</wizard>
""" % (GuessAuthorName, GuessAuthorEmail)


def wrapText(text):
    """ Wrapt text to fit default width """
    text = re.compile("\s+").sub(" ", text)
    return "\n".join(textwrap.wrap(text))

def dedentText(text, count = 12):
    """ Remove leading spaces from the beginning of lines """
    return re.compile("\n" + " " * count).sub("\n", text)

def indentText(text, count = 12):
    """ Insert leading spaces to the beginning of lines """
    return re.compile("\n").sub("\n" + " " * count, text)

def shortenText(text, max = 50):
    """ Shorten long texts into something more usable """
    # if shorter, nothing to do
    if not text or len(text) <= max:
        return text
    # cut the text
    text = text[0:max+1]
    # remove last non complete word
    text = re.sub(" [^ ]*$", "", text)
    return text

def shellEscaped(text):
    """
    Returns the text escaped for inclusion inside a shell double-quoted string.
    """
    return text.replace('\\', '\\\\')\
               .replace('"', r'\"')\
               .replace('$', r'\$')\
               .replace('`', r'\`')\
               .replace('!', r'\!')

def unique(seq):
    """ Remove duplicates from the supplied sequence """
    dictionary = {}
    for i in seq:
        dictionary[i] = 1
    return list(dictionary.keys())

def hr(width = 70):
    """ Return simple ascii horizontal rule """
    if width < 2: return ""
    return "# " + (width - 2) * "~"


def comment(text, width=70, comment="#", top=True, bottom=True, padding=3):
    """
    Create nicely formatted comment
    """
    result = ""

    # top hrule & padding
    if width and top:
        result += hr(width) + "\n"
    result += int(math.floor(padding/3)) * (comment + "\n")

    # prepend lines with the comment char and padding
    result += re.compile("^(?!#)", re.M).sub(comment + padding * " ", text)

    # bottom padding & hrule
    result += int(math.floor(padding/3)) * ("\n" + comment)
    if width and bottom:
        result += "\n" + hr(width)

    # remove any trailing spaces
    result = re.compile("\s+$", re.M).sub("", result)
    return result

def dashifyText(text, allowExtraChars = ""):
    """ Replace all special chars with dashes, and perhaps shorten """
    if not text: return text
    # remove the rubbish from the start & end
    text = re.sub("^[^a-zA-Z0-9]*", "", text)
    text = re.sub("[^a-zA-Z0-9]*$", "", text)
    # replace all special chars with dashes
    text = re.sub("[^a-zA-Z0-9%s]+" % allowExtraChars, "-", text)
    return text

def createNode(node, text):
    """ Create a child text node """
    # find document root
    root = node
    while root.nodeType != root.DOCUMENT_NODE:
        root = root.parentNode
    # append child text node
    node.appendChild(root.createTextNode(text))
    return node

def getNode(node):
    """ Return node value """
    try: value = node.firstChild.nodeValue
    except: return None
    else: return value

def setNode(node, value):
    """ Set node value (create a child if necessary) """
    try: node.firstChild.nodeValue = value
    except: createNode(node, value)
    return value

def findNode(parent, tag, name = None):
    """ Find a child node with specified tag (and name) """
    try:
        for child in parent.getElementsByTagName(tag):
            if name is None or child.getAttribute("name") == name:
                return child
    except:
        return None

def findNodeNames(node, tag):
    """ Return list of all name values of specified tags """
    list = []
    for child in node.getElementsByTagName(tag):
        if child.hasAttribute("name"):
            list.append(child.getAttribute("name"))
    return list

def parentDir():
    """ Get parent directory name for package name suggestion """
    dir = re.split("/", os.getcwd())[-1]
    if dir == "": return "kernel"
    # remove the -tests suffix if present
    # (useful if writing tests in the package/package-tests directory)
    dir = re.sub("-tests$", "", dir)
    return dir

def addToGit(path):
    """ Add a file or a directory to Git """

    try:
        process = subprocess.Popen(GitCommand + [path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
        out, err = process.communicate()
        if process.wait():
            print("Sorry, failed to add %s to git :-(" % path)
            print(out, err)
            sys.exit(1)
    except OSError:
        print("Unable to run %s, is %s installed?"
                % (" ".join(GitCommand), GitCommand[0]))
        sys.exit(1)

def removeEmbargo(summary):
    return summary.replace('EMBARGOED ', '')


class Preferences:
    """ Test's author preferences """

    # There is too much eval() magic for pylint to handle this properly.
    #pylint: disable=no-member

    def __init__(self, load_user_prefs=True):
        """ Set (in future get) user preferences / defaults """
        self.template = parseString(PreferencesTemplate.encode("utf-8"))
        self.firstRun = False
        if load_user_prefs:
            self.load()
        else:
            self.xml = self.template
            self.parse()


    # XXX (ncoghlan): all of these exec invocations should be replaced with
    # appropriate usage of setattr and getattr. However, beaker-wizard needs
    # decent test coverage before embarking on that kind of refactoring...
    def parse(self):
        """ Parse values from the xml file """
        # parse list nodes
        for node in "author test licenses skeletons".split():
            exec("self.%s = findNode(self.xml, '%s')" % (node, node))

        # parse single value nodes for author
        for node in "name email confirm skeleton".split():
            exec("self.%s = findNode(self.author, '%s')" % (node, node))
            # if the node cannot be found get the default from template
            if not eval("self." + node):
                print("Could not find <%s> in preferences, using default" % node)
                exec("self.%s = findNode(self.template, '%s').cloneNode(True)"
                        % (node, node))
                exec("self.author.appendChild(self.%s)" % node)

        # parse single value nodes for test
        for node in "type namespace time priority confidential destructive " \
                "prefix license".split():
            exec("self.%s = findNode(self.test, '%s')" % (node, node))
            # if the node cannot be found get the default from template
            if not eval("self." + node):
                print("Could not find <%s> in preferences, using default" % node)
                exec("self.%s = findNode(self.template, '%s').cloneNode(True)" % (node, node))
                exec("self.test.appendChild(self.%s)" % node)

    def load(self):
        """
        Load user preferences (or set to defaults)
        """
        preferences_file = os.environ.get("BEAKER_WIZARD_CONF", PreferencesFile)
        try:
            self.xml = parse(preferences_file)
        except:
            if os.path.exists(preferences_file):
                print("I'm sorry, the preferences file seems broken.\n" \
                        "Did you do something ugly to %s?" % preferences_file)
                sleep(3)
            else:
                self.firstRun = True
            self.xml = self.template
            self.parse()
        else:
            try:
                self.parse()
            except:
                print("Failed to parse %s, falling to defaults." % preferences_file)
                sleep(3)
                self.xml = self.template
                self.parse()

    def update(self, author, email, confirm, type, namespace,
               time, priority, confidential, destructive, prefix, license, skeleton):
        """
        Update preferences with current settings
        """
        setNode(self.name, author)
        setNode(self.email, email)
        setNode(self.confirm, confirm)
        setNode(self.type, type)
        setNode(self.namespace, namespace)
        setNode(self.time, time)
        setNode(self.priority, priority)
        setNode(self.confidential, confidential)
        setNode(self.destructive, destructive)
        setNode(self.prefix, prefix)
        setNode(self.license, license)
        setNode(self.skeleton, skeleton)

    def save(self):
        """ Save user preferences """
        # try to create directory
        try:
            os.makedirs(PreferencesDir)
        except OSError as e:
            if e.errno == 17:
                pass
            else:
                print("Cannot create preferences directory %s :-(" % PreferencesDir)
                return

        # try to write the file
        try:
            file = open(PreferencesFile, "wb")
        except:
            print("Cannot write to %s" % PreferencesFile)
        else:
            file.write((self.xml.toxml() + "\n").encode("utf-8"))
            file.close()
            print("Preferences saved to %s" % PreferencesFile)
        sleep(1)

    def getAuthor(self): return getNode(self.name)
    def getEmail(self): return getNode(self.email)
    def getConfirm(self): return getNode(self.confirm)
    def getType(self): return getNode(self.type)
    def getPackage(self): return parentDir()
    def getNamespace(self): return getNode(self.namespace)
    def getTime(self): return getNode(self.time)
    def getPriority(self): return getNode(self.priority)
    def getConfidential(self): return getNode(self.confidential)
    def getDestructive(self): return getNode(self.destructive)
    def getPrefix(self): return getNode(self.prefix)
    def getVersion(self): return "1.0"
    def getLicense(self): return getNode(self.license)
    def getSkeleton(self): return getNode(self.skeleton)

    def getLicenseContent(self, license):
        content = findNode(self.licenses, "license", license)
        if content:
            return re.sub("\n\s+$", "", content.firstChild.nodeValue)
        else:
            return None


class Help:
    """ Help texts """

    def __init__(self, options = None):
        if options:
            # display expert usage page only
            if options.expert():
                print(self.expert())
                sys.exit(0)
            # show version info
            elif options.ver():
                print(self.version())
                sys.exit(0)

    @staticmethod
    def usage():
        return "beaker-wizard [options] [TESTNAME] [BUG/CVE...] or beaker-wizard Makefile"

    @staticmethod
    def version():
        return "beaker-wizard %s" % WizardVersion

    @staticmethod
    def description():
        return DESCRIPTION

    @staticmethod
    def expert():
        os.execv('/usr/bin/man', ['man', 'beaker-wizard'])
        sys.exit(1)


class Makefile:
    """
    Parse values from an existing Makefile to set the initial values
    Used in the Makefile edit mode.
    """

    def __init__(self, options):
        # try to read the original Makefile
        self.path = options.arg[0]
        try:
            # open and read the whole content into self.text
            print("Reading the Makefile...")
            with open(self.path) as fd:
                # readlines behavior in Python 2 returns list with strings not unicode,
                # convert them manually
                text = []
                for line in fd.readlines():
                    try:
                        line = line.decode("utf-8")
                    except AttributeError:
                        pass
                    text.append(line)

                self.text = ''.join(text)

            # substitute the old style $TEST sub-variables if present
            for var in "TOPLEVEL_NAMESPACE PACKAGE_NAME RELATIVE_PATH".split():
                m = re.search("%s=(\S+)" % var, self.text)
                if m: self.text = re.sub("\$\(%s\)" % var, m.group(1), self.text)

            # locate the metadata section
            print("Inspecting the metadata section...")
            m = RegExpMetadata.search(self.text)
            self.metadata = m.group(1)

            # parse the $TEST and $TESTVERSION
            print("Checking for the full test name and version...")
            m = RegExpTest.search(self.text)
            options.arg = [m.group(1)]
            m = RegExpVersion.search(self.text)
            options.opt.version = m.group(1)
        except Exception as e:
            print("Failed to parse the original Makefile")
            print(e)
            sys.exit(6)

        # disable test name prefixing and set confirm to nothing
        options.opt.prefix = "No"
        options.opt.confirm = "nothing"

        # initialize non-existent options.opt.* vars
        options.opt.bug = options.opt.owner = options.opt.runfor = None
        # uknown will be used to store unrecognized metadata fields
        self.unknown = ""
        # map long fields to short versions
        map = {
            "description" : "desc",
            "architectures" : "archs",
            "testtime" : "time"
        }

        # parse info from metadata line by line
        print("Parsing the individual metadata...")
        for line in self.metadata.split("\n"):
            m = re.search("echo\s+[\"'](\w+):\s*(.*)[\"']", line)
            # skip non-@echo lines
            if not m: continue
            # read the key & value pair
            try: key = map[m.group(1).lower()]
            except: key = m.group(1).lower()
            # get the value, unescape escaped double quotes
            value = re.sub("\\\\\"", "\"", m.group(2))
            # skip fields known to contain variables
            if key in ("name", "testversion", "path"): continue
            # save known fields into options
            for data in "owner desc type archs releases time priority license " \
                    "confidential destructive bug requires runfor".split():
                if data == key:
                    # if multiple choice, extend the array
                    if key in "archs bug releases requires runfor".split():
                        try: exec("options.opt.%s.append(value)" % key)
                        except: exec("options.opt.%s = [value]" % key)
                    # otherwise just set the value
                    else:
                        exec("options.opt.%s = value" % key)
                    break
            # save unrecognized fields to be able to restore them back
            else:
                self.unknown += "\n" + line

        # parse name & email
        m = re.search("(.*)\s+<(.*)>", options.opt.owner)
        if m:
            options.opt.author = m.group(1)
            options.opt.email = m.group(2)

        # add bug list to arg
        if options.opt.bug:
            options.arg.extend(options.opt.bug)

        # success
        print("Makefile successfully parsed.")

    def save(self, test, version, content):
        # possibly update the $TEST and $TESTVERSION
        self.text = RegExpTest.sub("TEST=" + test, self.text)
        self.text = RegExpVersion.sub("TESTVERSION=" + version, self.text)

        # substitute the new metadata
        m = RegExpMetadata.search(content)
        self.text = RegExpMetadata.sub(m.group(1), self.text)

        # add unknown metadata fields we were not able to parse at init
        self.text = re.sub("\n\n\trhts-lint",
                self.unknown + "\n\n\trhts-lint", self.text)

        # let's write it
        try:
            file = open(self.path, "wb")
            file.write(self.text.encode("utf-8"))
            file.close()
        except:
            print("Cannot write to %s" % self.path)
            sys.exit(3)
        else:
            print("Makefile successfully written")


class Options:
    """
    Class maintaining user preferences and options provided on command line

    self.opt  ... options parsed from command line
    self.pref ... user preferences / defaults
    """

    def __init__(self, argv=None, load_user_prefs=True):
        if argv is None:
            argv = sys.argv
        self.pref = Preferences(load_user_prefs)
        formatter = IndentedHelpFormatter(max_help_position=40)
        #formatter._long_opt_fmt = "%s"

        # parse options
        parser = OptionParser(Help().usage(), formatter=formatter)
        parser.set_description(Help().description())

        # examples and help
        parser.add_option("-x", "--expert",
            dest="expert",
            action="store_true",
            help=SUPPRESS_HELP)
        parser.add_option("-V", "--version",
            dest="ver",
            action="store_true",
            help="display version info and quit")

        # author
        groupAuthor = OptionGroup(parser, "Author info")
        groupAuthor.add_option("-n",
            dest="author",
            metavar="NAME",
            help="your name [%s]" % self.pref.getAuthor())
        groupAuthor.add_option("-m",
            dest="email",
            metavar="MAIL",
            help="your email address [%s]" %  self.pref.getEmail())

        # create
        groupCreate = OptionGroup(parser, "Test creation specifics")
        groupCreate.add_option("-s",
            dest="skeleton",
            help="skeleton to use [%s]" % self.pref.getSkeleton())
        groupCreate.add_option("-j",
            dest="prefix",
            metavar="PREFIX",
            help="join the bug prefix to the testname [%s]"
                    % self.pref.getPrefix())
        groupCreate.add_option("-f", "--force",
            dest="force",
            action="store_true",
            help="force without review and overwrite existing files")
        groupCreate.add_option("-w", "--write",
            dest="write",
            action="store_true",
            help="write preferences to ~/.beaker_client/wizard")
        groupCreate.add_option("-b", "--bugzilla",
            dest="bugzilla",
            action="store_true",
            help="contact bugzilla to get bug details")
        groupCreate.add_option("-g", "--git",
            dest="git",
            action="store_true",
            help="add created files to the git repository")
        groupCreate.add_option("-C", "--current-directory",
            dest="use_current_dir",
            action="store_true",
            default=False,
            help="create test in current directory")

        # setup default to correctly display in help
        defaultEverything = defaultCommon = defaultNothing = ""
        if self.pref.getConfirm() == "everything":
            defaultEverything = " [Default]"
        elif self.pref.getConfirm() == "common":
            defaultCommon = " [Default]"
        elif self.pref.getConfirm() == "nothing":
            defaultNothing = " [Default]"

        # confirm
        groupConfirm = OptionGroup(parser, "Confirmation and verbosity")
        groupConfirm.add_option("-v", "--verbose",
            dest="verbose",
            action="store_true",
            help="display detailed info about every action")
        groupConfirm.add_option("-e", "--every",
            dest="confirm",
            action="store_const",
            const="everything",
            help="prompt for each and every available option" + defaultEverything)
        groupConfirm.add_option("-c", "--common",
            dest="confirm",
            action="store_const",
            const="common",
            help="confirm only commonly used options" + defaultCommon)
        groupConfirm.add_option("-y", "--yes",
            dest="confirm",
            action="store_const",
            const="nothing",
            help="yes, I'm sure, no questions, just do it!" + defaultNothing)

        # test metadata
        groupMeta = OptionGroup(parser, "Basic metadata")
        groupMeta.add_option("-d",
            dest="desc",
            metavar="DESCRIPTION",
            help="short description")
        groupMeta.add_option("-a",
            dest="archs",
            action="append",
            help="architectures [All]")
        groupMeta.add_option("-r",
            dest="releases",
            action="append",
            help="releases [All]")
        groupMeta.add_option("-o",
            dest="runfor",
            action="append",
            metavar="PACKAGES",
            help="run for packages [%s]" % self.pref.getPackage())
        groupMeta.add_option("-q",
            dest="requires",
            action="append",
            metavar="PACKAGES",
            help="required packages [%s]" % self.pref.getPackage())
        groupMeta.add_option("-Q",
            dest="rhtsrequires",
            action="append",
            metavar="TEST",
            help="required RHTS tests or libraries")
        groupMeta.add_option("-t",
            dest="time",
            help="test time [%s]" % self.pref.getTime())

        # test metadata
        groupExtra = OptionGroup(parser, "Extra metadata")
        groupExtra.add_option("-z",
            dest="version",
            help="test version [%s]" % self.pref.getVersion())
        groupExtra.add_option("-p",
            dest="priority",
            help="priority [%s]" % self.pref.getPriority())
        groupExtra.add_option("-l",
            dest="license",
            help="license [%s]" % self.pref.getLicense())
        groupExtra.add_option("-i",
            dest="confidential",
            metavar="INTERNAL",
            help="confidential [%s]" % self.pref.getConfidential())
        groupExtra.add_option("-u",
            dest="destructive",
            metavar="UGLY",
            help="destructive [%s]" % self.pref.getDestructive())

        # put it together
        parser.add_option_group(groupMeta)
        parser.add_option_group(groupExtra)
        parser.add_option_group(groupAuthor)
        parser.add_option_group(groupCreate)
        parser.add_option_group(groupConfirm)

        # convert all args to unicode
        uniarg = []
        for arg in argv[1:]:
            try:
                uarg = unicode(arg, 'utf-8')
            except NameError:
                uarg = arg
            uniarg.append(uarg)

        # and parse it!
        (self.opt, self.arg) = parser.parse_args(uniarg)

        # parse namespace/package/type/path/test
        self.opt.namespace = None
        self.opt.package = None
        self.opt.type = None
        self.opt.path = None
        self.opt.name = None
        self.opt.bugs = []
        self.makefile = False

        if self.arg:
            # if we're run in the Makefile-edit mode, parse it to get the values
            if re.match(".*Makefile$", self.arg[0]):
                self.makefile = Makefile(self)

            # the first arg looks like bug/CVE -> we take all args as bugs/CVE's
            if RegExpBug.match(self.arg[0]) or RegExpBugLong.match(self.arg[0]) or \
                    RegExpCVE.match(self.arg[0]) or RegExpCVELong.match(self.arg[0]):
                self.opt.bugs = self.arg[:]
            # otherwise we expect bug/CVE as second and following
            else:
                self.opt.bugs = self.arg[1:]
                # parsing namespace/package/type/path/testname
                self.testinfo = self.arg[0]
                path_components = os.path.normpath(self.testinfo.rstrip('/')).split('/')
                if len(path_components) >= 1:
                    self.opt.name = path_components.pop(-1)
                if len(path_components) >= 3 and re.match(Namespace().match() + '$', path_components[0]):
                    self.opt.namespace = path_components.pop(0)
                    self.opt.package = path_components.pop(0)
                    self.opt.type = path_components.pop(0)
                elif len(path_components) >= 2 and path_components[1] in SuggestedTestTypes:
                    self.opt.package = path_components.pop(0)
                    self.opt.type = path_components.pop(0)
                elif len(path_components) >= 1:
                    self.opt.type = path_components.pop(0)
                if path_components:
                    self.opt.path = '/'.join(path_components)

        # try to connect to bugzilla
        self.bugzilla = None
        if self.opt.bugzilla:
            try:
                from bugzilla import Bugzilla
            except:
                print("Sorry, the bugzilla interface is not available right now, try:\n"
                        "    yum install python-bugzilla\n"
                        "Use 'bugzilla login' command if you wish to access restricted bugs.")
                sys.exit(8)
            else:
                try:
                    print("Contacting bugzilla...")
                    self.bugzilla = Bugzilla(url=BugzillaXmlrpc)
                except:
                    print("Cannot connect to bugzilla, check your net connection.")
                    sys.exit(9)

    # command-line-only option interface
    def expert(self):   return self.opt.expert
    def ver(self):      return self.opt.ver
    def force(self):    return self.opt.force
    def write(self):    return self.opt.write
    def verbose(self):  return self.pref.firstRun or self.opt.verbose
    def confirm(self):  return self.opt.confirm or self.pref.getConfirm()

    # return both specified and default values for the rest of options
    def author(self):       return [ self.opt.author,       self.pref.getAuthor() ]
    def email(self):        return [ self.opt.email,        self.pref.getEmail() ]
    def skeleton(self):     return [ self.opt.skeleton,     self.pref.getSkeleton() ]
    def archs(self):        return [ self.opt.archs,        [] ]
    def releases(self):     return [ self.opt.releases,     ['-RHEL4', '-RHELClient5', '-RHELServer5'] ]
    def runfor(self):       return [ self.opt.runfor,       [self.pref.getPackage()] ]
    def requires(self):     return [ self.opt.requires,     [self.pref.getPackage()] ]
    def rhtsrequires(self): return [ self.opt.rhtsrequires, [] ]
    def time(self):         return [ self.opt.time,         self.pref.getTime() ]
    def priority(self):     return [ self.opt.priority,     self.pref.getPriority() ]
    def confidential(self): return [ self.opt.confidential, self.pref.getConfidential() ]
    def destructive(self):  return [ self.opt.destructive,  self.pref.getDestructive() ]
    def prefix(self):       return [ self.opt.prefix,       self.pref.getPrefix() ]
    def license(self):      return [ self.opt.license,      self.pref.getLicense() ]
    def version(self):      return [ self.opt.version,      self.pref.getVersion() ]
    def desc(self):         return [ self.opt.desc,         "What the test does" ]
    def description(self):  return [ self.opt.description,  "" ]
    def namespace(self):    return [ self.opt.namespace,    self.pref.getNamespace() ]
    def package(self):      return [ self.opt.package,      self.pref.getPackage() ]
    def type(self):         return [ self.opt.type,         self.pref.getType() ]
    def path(self):         return [ self.opt.path,         "" ]
    def name(self):         return [ self.opt.name,         "a-few-descriptive-words" ]
    def bugs(self):         return [ self.opt.bugs,         [] ]



class Inquisitor:
    """
    Father of all Inquisitors

    Well he is not quite real Inquisitor, as he is very
    friendly and accepts any answer you give him.
    """
    def __init__(self, options = None, suggest = None):
        # set options & initialize
        self.options = options
        self.suggest = suggest
        self.common = True
        self.error = 0
        self.init()
        if not self.options: return

        # finally ask for confirmation or valid value
        if self.confirm or not self.valid():
            self.ask()

    def init(self):
        """ Initialize basic stuff """
        self.name = "Answer"
        self.question = "What is the answer to life, the universe and everything"
        self.description = None
        self.default()

    def default(self, optpref=None):
        """ Initialize default option data """
        # nothing to do when options not supplied
        if not optpref: return

        # initialize opt (from command line) & pref (from user preferences)
        (self.opt, self.pref) = optpref

        # set confirm flag
        self.confirm = self.common and self.options.confirm() != "nothing" \
                or not self.common and self.options.confirm() == "everything"

        # now set the data!
        # commandline option overrides both preferences & suggestion
        if self.opt:
            self.data = self.opt
            self.confirm = False
        # use suggestion if available (disabled in makefile edit mode)
        elif self.suggest and not self.options.makefile:
            self.data = self.suggest
        # otherwise use the default from user preferences
        else:
            self.data = self.pref
            # reset the user preference if it's not a valid value
            # (to prevent suggestions like: x is not valid what about x?)
            if not self.valid():
                self.pref = "something else"

    def defaultify(self):
        """ Set data to default/preferred value """
        self.data = self.pref

    def normalize(self):
        """ Remove trailing and double spaces """
        if not self.data: return
        self.data = re.sub("^\s*", "", self.data)
        self.data = re.sub("\s*$", "", self.data)
        self.data = re.sub("\s+", " ", self.data)

    def read(self):
        """
        Read an answer from user
        """
        try:
            # Even though unicode_literals are imported, stdin still produces ascii
            answer = sys.stdin.readline().strip()
            answer = answer.decode("utf-8")
        # Python 3 doesn't have decode
        except AttributeError:
            pass
        except KeyboardInterrupt:
            print("\nOk, finishing for now. See you later ;-)")
            sys.exit(4)
        # if just enter pressed, we leave self.data as it is (confirmed)
        if answer != "":
            # append the data if the answer starts with a "+",
            # but ignore if only "+" is present
            m = re.search("^\+\S+(.*)", answer)
            if m and isinstance(self.data, list):
                self.data.append(m.group(1))
            else:
                self.data = answer
        self.normalize()

    def heading(self):
        """ Display nice heading with question """
        print("\n" + self.question + "\n" + 77 * "~")

    def value(self):
        """ Return current value """
        return self.data

    def show(self, data = None):
        """ Return current value nicely formatted (redefined in children)"""
        if not data:
            data = self.data
        if data == "":
            return "None"
        return data

    def singleName(self):
        """ Return the name in lowercase singular (for error reporting) """
        return re.sub("s$", "", self.name.lower())

    def matchName(self, text):
        """ Return true if the text matches inquisitor's name """
        # remove any special characters from the search string
        text = re.sub("[^\w\s]", "", text)
        return re.search(text, self.name, re.I)

    def describe(self):
        if self.description is not None:
            print(wrapText(self.description))

    def format(self, data = None):
        """ Display in a nicely indented style """
        print(self.name.rjust(ReviewWidth), ":", (data or self.show()))

    def formatMakefileLine(self, name = None, value = None):
        """ Format testinfo line for Makefile inclusion """
        if not (self.value() or value): return ""
        return '\n            	@echo "%s%s" >> $(METADATA)' % (
                ((name or self.name) + ":").ljust(MakefileLineWidth),
                shellEscaped(value or self.value()))

    def valid(self):
        """ Return true when provided value is a valid answer """
        return self.data not in ["?", ""]

    def suggestion(self):
        """
        Provide user with a suggestion or detailed description.

        Note that the return value is already encoded as bytes for display.
        """
        # if current data is valid, offer is as a suggestion
        if self.valid():
            if self.options.verbose(): self.describe()
            return "%s?" % self.show()
        # otherwise suggest the default value
        else:
            bad = self.data
            self.defaultify()

            # regular suggestion (no question mark for help)
            if bad is None or "".join(bad) != "?":
                self.error += 1
                if self.error > 1 or self.options.verbose(): self.describe()
                return "%s is not a valid %s, what about %s?" \
                    % (self.show(bad), self.singleName(), self.show(self.pref))
            # we got question mark ---> display description to help
            else:
                self.describe()
                return "%s?" % self.show()

    def ask(self, force = False, suggest = None):
        """ Ask for valid value """
        if force: self.confirm = True
        if suggest: self.data = suggest
        self.heading()
        # keep asking until we get sane answer
        while self.confirm or not self.valid():
            sys.stdout.write("[%s] " % self.suggestion())
            # Python 3 had a complete IO overhaul and doesn't flush automatically
            # like Python 2 did. So to not wait until readline() flushes, we flush before
            # prompting user for data
            sys.stdout.flush()
            self.read()
            self.confirm = False

    def edit(self, suggest = None):
        """ Edit = force to ask again
        returns true if changes were made """
        before = self.data
        self.ask(force = True, suggest = suggest)
        return self.data != before


class SingleChoice(Inquisitor):
    """ This Inquisitor accepts just one value from the given list """

    def init(self):
        self.name = "SingleChoice"
        self.question = "Give a valid answer from the list"
        self.description = "Supply a single value from the list above."
        self.list = ["list", "of", "valid", "values"]
        self.default()

    def propose(self):
        """ Try to find nearest match in the list"""
        if self.data == "?": return
        for item in self.list:
            if re.search(re.escape(self.data), item, re.I):
                self.pref = item
                return

    def valid(self):
        if self.data in self.list:
            return True
        else:
            self.propose()
            return False

    def heading(self):
        Inquisitor.heading(self)
        if self.list:
            print(wrapText("Possible values: " + ", ".join(self.list)))


class YesNo(SingleChoice):
    """ Inquisitor expecting only two obvious answers """

    def init(self):
        self.name = "Yes or No"
        self.question = "Are you sure?"
        self.description = "All you need to say is simply 'Yes,' or 'No'; \
                anything beyond this comes from the evil one."
        self.list = ["Yes", "No"]
        self.default()

    def normalize(self):
        """ Recognize yes/no abbreviations """
        if not self.data: return
        self.data = re.sub("^y.*$", "Yes", self.data, re.I)
        self.data = re.sub("^n.*$", "No", self.data, re.I)

    def formatMakefileLine(self, name = None, value = None):
        """ Format testinfo line for Makefile inclusion """
        # testinfo requires lowercase yes/no
        return Inquisitor.formatMakefileLine(self,
                name = name, value = self.data.lower())

    def valid(self):
        self.normalize()
        return SingleChoice.valid(self)


class MultipleChoice(SingleChoice):
    """ This Inquisitor accepts more values but only from the given list """

    def init(self):
        self.name = "MultipleChoice"
        self.question = "Give one or more values from the list"
        self.description = "You can supply more values separated with space or comma\n"\
            "but they all must be from the list above."
        self.list = ["list", "of", "valid", "values"]
        self.emptyListMeaning = "None"
        self.sort = True
        self.default()

    def default(self, optpref):
        # initialize opt & pref
        (self.opt, self.pref) = optpref

        # set confirm flag
        self.confirm = self.common and self.options.confirm() != "nothing" \
                or not self.common and self.options.confirm() == "everything"

        # first initialize data as an empty list
        self.data = []

        # append possible suggestion to the data (disabled in makefile edit mode)
        if self.suggest and not self.options.makefile:
            self.data.append(self.suggest)

        # add items obtained from the command line
        if self.opt:
            self.data.extend(self.opt)
            self.confirm = False

        # default preferences used only if still no data obtained
        if not self.data:
            self.data.extend(self.pref)

        self.listify()

    def defaultify(self):
        self.data = self.pref[:]
        self.listify()

    def listify(self):
        # make sure data is list
        if type(self.data) is not list:
            # special value "none" means an empty list
            if self.data.lower() == "none":
                self.data = []
                return
            # depending on emptyListMeaning "all" can mean
            elif self.data.lower() == "all":
                # no restrictions (releases, archs)
                if self.emptyListMeaning == "All":
                    self.data = []
                # all items (reproducers)
                else:
                    self.data = self.list[:]
                return
            # otherwise just listify
            else:
                self.data = [ self.data ]

        # expand comma/space separated items
        result = []
        for item in self.data:
            # strip trailing separators
            item = re.sub('[ ,]*$', '', item)
            # split on spaces and commas
            result.extend(re.split('[ ,]+', item))
        self.data = result

        # let's make data unique and sorted
        if self.sort:
            self.data = unique(self.data)
            self.data.sort()

    def normalize(self):
        """ Parse input into a list """
        self.listify()

    def showItem(self, item):
        return item

    def formatMakefileLine(self, name = None, value = None):
        """ Format testinfo line for Makefile inclusion """
        # for multiple choice we produce values joined by spaces
        return Inquisitor.formatMakefileLine(self,
                name = name, value = " ".join(self.data))

    def show(self, data = None):
        if data is None: data = self.data
        if not data: return self.emptyListMeaning
        return ", ".join(map(self.showItem, data))

    def propose(self):
        """ Try to find nearest matches in the list"""
        if self.data[0] == "?": return
        result = []
        try:
            for item in self.list:
                if re.search(re.escape(self.data[0]), item, re.I):
                    result.append(item)
        except:
            pass
        if result:
            self.pref = result[:]

    def validItem(self, item):
        return item in self.list

    def valid(self):
        for item in self.data:
            if not self.validItem(item):
                self.data = [item]
                self.propose()
                return False
        return True

# TODO: Make the licensing organisation configurable
LICENSE_ORGANISATION = "Red Hat, Inc"

GPLv2_ONLY_LICENSE = ("""Copyright (c) %s %s.

This copyrighted material is made available to anyone wishing
to use, modify, copy, or redistribute it subject to the terms
and conditions of the GNU General Public License version 2.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the Free
Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
Boston, MA 02110-1301, USA."""
% (date.today().year, LICENSE_ORGANISATION))

GPLv2_OR_LATER_LICENSE = ("""Copyright (c) %s %s.

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 2 of
the License, or (at your option) any later version.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see http://www.gnu.org/licenses/."""
% (date.today().year, LICENSE_ORGANISATION))

GPLv3_OR_LATER_LICENSE = ("""Copyright (c) %s %s.

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see http://www.gnu.org/licenses/."""
% (date.today().year, LICENSE_ORGANISATION))

PROPRIETARY_LICENSE_TEMPLATE = ("""Copyright (c) %s %s. All rights reserved.

%%s"""
% (date.today().year, LICENSE_ORGANISATION))

DEFINED_LICENSES = {
# Annoyingly, the bare "GPLv2" and "GPLv3" options differ in whether or not
# they include the "or later" clause. Unfortunately, changing it now could
# result in GPLv3 tests intended to be GPLv3+ getting mislabeled.
"GPLv2" : GPLv2_ONLY_LICENSE,
"GPLv3" : GPLv3_OR_LATER_LICENSE,
# The GPLvX+ variants consistently use the "or later" phrasing
"GPLv2+" : GPLv2_OR_LATER_LICENSE,
"GPLv3+" : GPLv3_OR_LATER_LICENSE,
"other" : PROPRIETARY_LICENSE_TEMPLATE,
}


class License(Inquisitor):
    """
    License to be included in test files
    """

    def init(self):
        self.name = "License"
        self.question = "What license should be used?"
        self.description = "Just supply a license GPLv2+, GPLv3+, ..."
        self.common = False
        self.default(self.options.license())
        self.licenses = DEFINED_LICENSES

    def get(self):
        """
        Return license corresponding to user choice
        """

        if self.data != "other" and self.data in self.licenses:
            return dedentText(self.licenses[self.data])
        else:
            license = self.options.pref.getLicenseContent(self.data)
            if license:  # user defined license from preferences
                return dedentText(self.licenses["other"]
                                  % (license,), count=12)
            else:  # anything else
                return dedentText(self.licenses["other"]
                                  % ("PROVIDE YOUR LICENSE TEXT HERE.",))


class Time(Inquisitor):
    """ Time for test to run """

    def init(self):
        self.name = "Time"
        self.question = "Time for test to run"
        self.description = """The time must be in format [1-99][m|h|d] for 1-99
                minutes/hours/days (e.g. 3m, 2h, 1d)"""
        self.default(self.options.time())

    def valid(self):
        m = re.match("^(\d{1,2})[mhd]$", self.data)
        return m is not None and int(m.group(1)) > 0


class Version(Inquisitor):
    """ Time for test to run """

    def init(self):
        self.name = "Version"
        self.question = "Version of the test"
        self.description = "Must be in the format x.y"
        self.common = False
        self.default(self.options.version())

    def valid(self):
        return re.match("^\d+\.\d+$", self.data)


class Priority(SingleChoice):
    """ Test priority """

    def init(self):
        self.name = "Priority"
        self.question = "Priority"
        self.description = "Test priority for scheduling purposes"
        self.common = False
        self.list = "Low Medium Normal High Manual".split()
        self.default(self.options.priority())


class Confidential(YesNo):
    """ Confidentiality flag """

    def init(self):
        self.name = "Confidential"
        self.question = "Confidential"
        self.description = "Should the test be kept internal?"
        self.common = False
        self.list = ["Yes", "No"]
        self.default(self.options.confidential())

    def singleName(self):
        return "confidentiality flag"


class Destructive(YesNo):
    """ Destructivity flag """

    def init(self):
        self.name = "Destructive"
        self.question = "Destructive"
        self.description = "Is it such an ugly test that it can break the system?"
        self.common = False
        self.list = ["Yes", "No"]
        self.default(self.options.destructive())

    def singleName(self):
        return "destructivity flag"


class Prefix(YesNo):
    """ Bug number prefix """

    def init(self):
        self.name = "Prefix the test name"
        self.question = "Add the bug number to the test name?"
        self.description = "Should we prefix the test name with the bug/CVE number?"
        self.common = False
        self.list = ["Yes", "No"]
        self.default(self.options.prefix())

    def singleName(self):
        return "prefix choice"


class Releases(MultipleChoice):
    """ List of releases the test should run on """

    def init(self):
        self.name = "Releases"
        self.question = "Releases (choose one or more or \"all\")"
        self.description = """One or more values separated with space or comma
            or "all" for no limitaion. You can also use minus sign for excluding
            a specific release (-RHEL4). Refer to Web UI Distro Family
            selection for OSMajor alias name or if none provided use the
            OSMajor Name"""
        self.list = "RHEL2.1 RHEL3 RHEL4 RHELServer5 RHELClient5".split()
        self.list += ["RHEL{0}".format(id) for id in range(6, 9)]
        self.list += ["F{0}".format(release) for release in range(7, 32)]
        self.sort = True
        self.common = False
        self.emptyListMeaning = "All"
        self.default(self.options.releases())

    def validItem(self, item):
        item = re.sub("^-","", item)
        valid = item in self.list
        if not valid:
            return RegExpReleases.match(item)
        else:
            return valid


class Architectures(MultipleChoice):
    """ List of architectures the test should run on """

    def init(self):
        self.name = "Architectures"
        self.question = "Architectures (choose one or more or \"all\")"
        self.description = "You can supply more values separated with space or comma\n"\
            "but they all must be from the list of possible values above."
        self.list = "i386 x86_64 ia64 ppc ppc64 ppc64le s390 s390x aarch64".split()
        self.sort = True
        self.common = False
        self.emptyListMeaning = "All"
        self.default(self.options.archs())


class Namespace(SingleChoice):
    """ Namespace"""

    def init(self):
        self.name = "Namespace"
        self.question = "Namespace"
        self.description = "Provide a root namespace for the test."
        self.list = """distribution installation kernel desktop tools CoreOS
                cluster rhn examples performance ISV virt""".split()
        if self.options: self.default(self.options.namespace())

    def match(self):
        """ Return regular expression matching valid data """
        return "(" + "|".join(self.list) + ")"


class Package(Inquisitor):
    """ Package for which the test is written """

    def init(self):
        self.name = "Package"
        self.question = "What package is this test for?"
        self.description = "Supply a package name (without version or release number)"
        self.common = False
        self.default(self.options.package())

    def valid(self):
        return RegExpPackage.match(self.data)


class Type(Inquisitor):
    """ Test type """

    def init(self):
        self.name = "Test type"
        self.question = "What is the type of test?"
        self.description = "Specify the type of the test. Hints above."
        self.proposed = 0
        self.proposedname = ""
        self.list = SuggestedTestTypes
        self.dirs = [os.path.join(o) for o in os.listdir('.')
                     if os.path.isdir(os.path.join('.', o)) and not o.startswith('.')]
        if self.options: self.default(self.options.type())

    def heading(self):
        Inquisitor.heading(self)
        print(wrapText("Recommended values: " + ", ".join(sorted(self.dirs))))
        print(wrapText("Possible values: " + ", ".join(self.list)))

    def propose(self):
        """ Try to find nearest match in the list"""
        if self.data == "?":
            return
        self.proposed = 1
        self.proposedname = self.data
        self.description = "Type '%s' does not exist. Confirm creating a new type." % self.proposedname
        self.describe()
        for item in self.list:
            if re.search(re.escape(self.data), item, re.I):
                self.pref = item
                return

    def suggestSkeleton(self):
        """ For multihost tests and library suggest proper skeleton """
        if self.data == "Multihost":
            return "multihost"
        elif self.data == "Library":
            return "library"

    def valid(self):
        if self.data in self.list or self.data in self.dirs or (self.proposed == 1 and self.proposedname == self.data):
            return True
        else:
            self.propose()
            return False


class Path(Inquisitor):
    """ Relative path to test """

    def init(self):
        self.name = "Relative path"
        self.question = "Relative path under test type"
        self.description = """Path can be used to organize tests
            for complex packages, e.g. 'server' part in
            /CoreOS/mysql/Regression/server/bz123456-some-test.
            (You can also use dir/subdir for deeper nesting.
            Use "none" for no path.)"""
        self.common = False
        self.default(self.options.path())

    def valid(self):
        return (self.data is None or self.data == ""
                or RegExpPath.match(self.data))

    def normalize(self):
        """ Replace none keyword with real empty path """
        Inquisitor.normalize(self)
        if self.data and re.match('none', self.data, re.I):
            self.data = None

    def value(self):
        if self.data:
            return "/" + self.data
        else:
            return ""


class Bugs(MultipleChoice):
    """ List of bugs/CVE's related to the test """

    def init(self):
        self.name = "Bug or CVE numbers"
        self.question = "Bugs or CVE's related to the test"
        self.description = """Supply one or more bug or CVE numbers
                (e.g. 123456 or 2009-7890). Use the '+' sign to add
                the bugs instead of replacing the current list."""
        self.list = []
        self.sort = False
        self.emptyListMeaning = "None"
        self.bug = None
        self.default(self.options.bugs())
        self.reproducers = Reproducers(self.options)

    def validItem(self, item):
        return RegExpBug.match(item) \
            or RegExpCVE.match(item)

    def valid(self):
        # let's remove possible (otherwise harmless) bug/CVE prefixes
        for i in range(len(self.data)):
            self.data[i] = re.sub(RegExpBugPrefix, "", self.data[i])
            self.data[i] = re.sub(RegExpCVEPrefix, "", self.data[i])
        # and do the real validation
        return MultipleChoice.valid(self)

    def showItem(self, item):
        if RegExpBug.match(item):
            return "BZ#" + item
        elif RegExpCVE.match(item):
            return "CVE-" + item
        else:
            return item

    def formatMakefileLine(self, name = None, value = None):
        """ Format testinfo line for Makefile inclusion """
        list = []
        # filter bugs only (CVE's are not valid for testinfo.desc)
        for item in self.data:
            if RegExpBug.match(item):
                list.append(item)
        if not list: return ""
        return Inquisitor.formatMakefileLine(self, name = "Bug", value = " ".join(list))

    def getFirstBug(self):
        """ Return first bug/CVE if there is some """
        if self.data: return self.showItem(self.data[0])

    def fetchBugDetails(self):
        """ Fetch details of the first bug from Bugzilla """
        if self.options.bugzilla and self.data:
            # use CVE prefix when searching for CVE's in bugzilla
            if RegExpCVE.match(self.data[0]):
                bugid = "CVE-" + self.data[0]
            else:
                bugid = self.data[0]
            # contact bugzilla and try to fetch the details
            try:
                print("Fetching details for", self.showItem(self.data[0]))
                self.bug = self.options.bugzilla.getbug(bugid,
                        include_fields=['id', 'alias', 'component', 'summary',
                                        'attachments'])
            except Exception as e:
                if re.search('not authorized to access', str(e)):
                    print("Sorry, %s has a restricted access.\n"
                        "Use 'bugzilla login' command to set up cookies "
                        "then try again." % self.showItem(self.data[0]))
                else:
                    print("Sorry, could not get details for %s\n%s" % (bugid, e))
                sleep(3)
                return
            # successfully fetched
            else:
                # for CVE's add the bug id to the list of bugs
                if RegExpCVE.match(self.data[0]):
                    self.data.append(str(self.bug.id))
                # else investigate for possible CVE alias
                elif self.bug.alias and RegExpCVELong.match(self.bug.alias[0]):
                    cve = re.sub("CVE-", "", self.bug.alias[0])
                    self.data[:0] = [cve]
                # and search attachments for possible reproducers
                if self.bug:
                    self.reproducers.find(self.bug)
                    return True

    def getSummary(self):
        """ Return short summary fetched from bugzilla """
        if self.bug:
            return re.sub("CVE-\d{4}-\d{4}\s*", "", removeEmbargo(self.bug.summary))

    def getComponent(self):
        """ Return bug component fetched from bugzilla """
        if self.bug:
            component = self.bug.component
            # Use the first component if component list given
            if isinstance(component, list):
                component = component[0]
            # Ignore generic CVE component "vulnerability"
            if component != 'vulnerability':
                return component

    def getLink(self):
        """ Return URL of the first bug """
        if self.data:
            if RegExpCVE.match(self.data[0]):
                return "%sCVE-%s" % (BugzillaUrl, self.data[0])
            else:
                return BugzillaUrl + self.data[0]

    def suggestType(self):
        """ Guess test type according to first bug/CVE """
        if self.data:
            if RegExpBug.match(self.data[0]):
                return "Regression"
            elif RegExpCVE.match(self.data[0]):
                return "Security"

    def suggestConfidential(self):
        """ If the first bug is a CVE, suggest as confidential """
        if self.data and RegExpCVE.match(self.data[0]):
            return "Yes"
        else:
            return None

    def suggestTestName(self):
        """ Suggest testname from bugzilla summary """
        return dashifyText(shortenText(self.getSummary(), MaxLengthTestName))

    def suggestDescription(self):
        """ Suggest short description from bugzilla summary """
        if self.getSummary():
            return "Test for %s (%s)" % (
                self.getFirstBug(),
                shortenText(re.sub(":", "", self.getSummary()),
                        max=MaxLengthSuggestedDesc))

    def formatBugDetails(self):
        """ Put details fetched from Bugzilla into nice format for PURPOSE file """
        if not self.bug:
            return ""
        else:
            return "Bug summary: %s\nBugzilla link: %s\n" % (
                    self.getSummary(), self.getLink())


class Name(Inquisitor):
    """ Test name """

    def init(self):
        self.name = "Test name"
        self.question = "Test name"
        self.description = """Use few, well chosen words describing
            what the test does. Special chars will be automatically
            converted to dashes."""
        self.default(self.options.name())
        self.data = dashifyText(self.data, allowExtraChars="_")
        self.bugs = Bugs(self.options)
        self.bugs.fetchBugDetails()
        # suggest test name (except when supplied on command line)
        if self.bugs.suggestTestName() and not self.opt:
            self.data = self.bugs.suggestTestName()
        self.prefix = Prefix(self.options)

    def normalize(self):
        """ Add auto-dashify function for name editing """
        if not self.data == "?":
            # when editing the test name --- dashify, but allow
            # using underscore if the user really wants it
            self.data = dashifyText(self.data, allowExtraChars="_")

    def valid(self):
        return self.data is not None and RegExpTestName.match(self.data)

    def value(self):
        """ Return test name (including bug/CVE number) """
        bug = self.bugs.getFirstBug()
        if bug and self.prefix.value() == "Yes":
            return bug.replace('BZ#','bz') + "-" + self.data
        else:
            return self.data

    def format(self, data = None):
        """ When formatting let's display with bug/CVE numbers """
        Inquisitor.format(self, self.value())

    def show(self, data=None):
        """ Return current value """
        if data == "":
            return "None"
        if not data:
            data = self.data
        return data

class Reproducers(MultipleChoice):
    """ Possible reproducers from Bugzilla """

    def init(self):
        self.name = "Reproducers to fetch"
        self.question = "Which Bugzilla attachments do you wish to download?"
        self.description = """Wizard can download Bugzilla attachments for you.
                It suggests those which look like reproducers, but you can pick
                the right attachments manually as well."""
        self.bug = None
        self.list = []
        self.sort = True
        self.emptyListMeaning = "None"
        self.common = False
        self.default([[], []])
        self.confirm = False

    def singleName(self):
        return "reproducer"

    def find(self, bug):
        """ Get the list of all attachments (except patches and obsolotes)"""

        if not bug or not bug.attachments:
            return False
        # remember the bug & empty the lists
        self.bug = bug
        self.list = []
        self.pref = []
        self.data = []

        # Provide "None" as a possible choice for attachment download
        self.list.append("None")

        print("Examining attachments for possible reproducers")
        for attachment in self.bug.attachments:
            # skip obsolete and patch attachments
            is_patch = attachment.get("is_patch", attachment.get("ispatch"))
            filename = attachment.get("file_name", attachment.get("filename"))
            is_obsolete = attachment.get(
                    "is_obsolete", attachment.get("isobsolete"))
            if is_patch == 0 and is_obsolete == 0:
                self.list.append(filename)
                # add to suggested attachments if it looks like a reproducer
                if RegExpReproducer.search(attachment['description']) or \
                        RegExpReproducer.search(filename):
                    self.data.append(filename)
                    self.pref.append(filename)
                    print("Adding"),
                else:
                    print("Skipping",)
                print("%s (%s)" % (filename, attachment['description']))
                sleep(1)

    def download(self, path):
        """ Download selected reproducers """
        if not self.bug:
            return False
        for attachment in self.bug.attachments:
            attachment_filename = attachment.get(
                    "file_name", attachment.get("filename"))
            is_obsolete = attachment.get(
                    "is_obsolete", attachment.get("isobsolete"))
            if attachment_filename in self.data and is_obsolete == 0:
                print("Attachment", attachment_filename,)
                try:
                    dirfiles = os.listdir(path)
                    filename = path + "/" + attachment_filename
                    remote = self.options.bugzilla.openattachment(
                            attachment['id'])
                    # rename the attachment if it has the same name as one
                    # of the files in the current directory
                    if attachment_filename in dirfiles:
                        print("- file already exists in {0}/".format(path))
                        new_name = ""
                        while new_name == "":
                            print("Choose a new filename for the attachment: ",)
                            try:
                                # Even though unicode_literals are imported, stdin still produces ascii
                                new_name = sys.stdin.readline().strip()
                                new_name = new_name.decode("utf-8")
                            # Python 3 doesn't have decode
                            except AttributeError:
                                pass
                        filename = path + "/" + new_name

                    local = open(filename, 'wb')
                    # XXX needs more testing
                    local.write(remote.read().encode("utf-8"))
                    remote.close()
                    local.close()

                    # optionally add to the git repository
                    if self.options.opt.git:
                        addToGit(filename)
                        addedToGit = ", added to git"
                    else:
                        addedToGit = ""
                except:
                    print("download failed")
                    print("python-bugzilla-0.5 or higher required")
                    sys.exit(5)
                else:
                    print("downloaded" + addedToGit)


class RunFor(MultipleChoice):
    """ List of packages which this test should be run for """

    def init(self):
        self.name = "Run for packages"
        self.question = "Run for packages"
        self.description = """Provide a list of packages which this test should
                be run for. It's a good idea to add dependent packages here."""
        self.list = []
        self.sort = True
        self.emptyListMeaning = "None"
        self.common = False
        self.default(self.options.runfor())

    def validItem(self, item):
        return RegExpPackage.match(item)


class Requires(MultipleChoice):
    """ List of packages which should be installed on test system """

    def init(self):
        self.name = "Required packages"
        self.question = "Requires: packages which test depends on"
        self.description = """Just write a list of package names
                which should be automatically installed on the test system."""
        self.list = []
        self.sort = True
        self.emptyListMeaning = "None"
        self.common = False
        self.default(self.options.requires())

    def validItem(self, item):
        return RegExpPackage.match(item)


class RhtsRequires(MultipleChoice):
    """ List of other RHTS tests or libraries which this test requires """

    def init(self):
        self.name = "Required RHTS tests/libraries"
        self.question = "RhtsRequires: other tests or libraries required by " \
                "this one, e.g. test(/mytests/common) or library(mytestlib)"
        self.description = """Write a list of RPM dependencies which should be
                installed by the package manager. Other tasks provide test(/task/name)
                and libraries provide library(name)."""
        self.list = []
        self.sort = True
        self.emptyListMeaning = "None"
        self.common = False
        self.default(self.options.rhtsrequires())

    def validItem(self, item):
        return RegExpRhtsRequires.match(item)


class Skeleton(SingleChoice):
    """ Skeleton to be used for creating the runtest.sh """

    def init(self):
        self.name = "Skeleton"
        self.question = "Skeleton to be used for creating the runtest.sh"
        self.description = """There are several runtest.sh skeletons available:
                beaker (general Beaker template),
                beakerlib (BeakerLib structure),
                simple (creates separate script with test logic),
                empty (populates runtest.sh just with header and license) and
                "skelX" (custom skeletons saved in user preferences)."""
        self.skeletons = parseString("""
    <skeletons>
        <skeleton name="beakerlib">
            # Include Beaker environment
            . /usr/bin/rhts-environment.sh || exit 1
            . /usr/share/beakerlib/beakerlib.sh || exit 1

            PACKAGE="<package/>"

            rlJournalStart
                rlPhaseStartSetup
                    rlAssertRpm $PACKAGE
                    rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
                    rlRun "pushd $TmpDir"
                rlPhaseEnd

                rlPhaseStartTest
                    rlRun "touch foo" 0 "Creating the foo test file"
                    rlAssertExists "foo"
                    rlRun "ls -l foo" 0 "Listing the foo test file"
                rlPhaseEnd

                rlPhaseStartCleanup
                    rlRun "popd"
                    rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
                rlPhaseEnd
            rlJournalPrintText
            rlJournalEnd
        </skeleton>
        <skeleton name="conditional">
            # Include Beaker environment
            . /usr/bin/rhts-environment.sh || exit 1
            . /usr/share/beakerlib/beakerlib.sh || exit 1

            PACKAGE="<package/>"

            rlJournalStart
                rlPhaseStartSetup
                    rlAssertRpm $PACKAGE || rlDie "$PACKAGE not installed"
                    rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
                    rlRun "pushd $TmpDir"
                rlPhaseEnd

                rlGetTestState &amp;&amp; { rlPhaseStartTest
                    rlRun "touch foo" 0 "Creating the foo test file"
                    rlAssertExists "foo"
                    rlRun "ls -l foo" 0 "Listing the foo test file"
                rlPhaseEnd; }

                rlPhaseStartCleanup
                    rlRun "popd"
                    rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
                rlPhaseEnd
            rlJournalPrintText
            rlJournalEnd
        </skeleton>
        <skeleton name="beaker">
            # Include Beaker environment
            . /usr/bin/rhts-environment.sh || exit 1

            PACKAGE="<package/>"
            set -x

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Setup
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            score=0
            rpm -q $PACKAGE || ((score++))
            TmpDir=$(mktemp -d) || ((score++))
            pushd $TmpDir || ((score++))
            ((score == 0)) &amp;&amp; result=PASS || result=FAIL
            echo "Setup finished, result: $result, score: $score"
            report_result $TEST/setup $result $score


            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Test
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            score=0
            touch foo || ((score++))
            [ -e foo ] || ((score++))
            ls -l foo || ((score++))
            ((score == 0)) &amp;&amp; result=PASS || result=FAIL
            echo "Testing finished, result: $result, score: $score"
            report_result $TEST/testing $result $score


            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Cleanup
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            score=0
            popd || ((score++))
            rm -r "$TmpDir" || ((score++))
            ((score == 0)) &amp;&amp; result=PASS || result=FAIL
            echo "Cleanup finished, result: $result, score: $score"
            report_result $TEST/cleanup $result $score
        </skeleton>
        <skeleton name="multihost">
            # Include Beaker environment
            . /usr/bin/rhts-environment.sh || exit 1
            . /usr/share/beakerlib/beakerlib.sh || exit 1

            PACKAGE="<package/>"

            # set client &amp; server manually if debugging
            # SERVERS="server.example.com"
            # CLIENTS="client.example.com"

            Server() {
                rlPhaseStartTest Server
                    # server setup goes here
                    rlRun "rhts-sync-set -s READY" 0 "Server ready"
                    rlRun "rhts-sync-block -s DONE $CLIENTS" 0 "Waiting for the client"
                rlPhaseEnd
            }

            Client() {
                rlPhaseStartTest Client
                    rlRun "rhts-sync-block -s READY $SERVERS" 0 "Waiting for the server"
                    # client action goes here
                    rlRun "rhts-sync-set -s DONE" 0 "Client done"
                rlPhaseEnd
            }

            rlJournalStart
                rlPhaseStartSetup
                    rlAssertRpm $PACKAGE
                    rlLog "Server: $SERVERS"
                    rlLog "Client: $CLIENTS"
                    rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
                    rlRun "pushd $TmpDir"
                rlPhaseEnd

                if echo $SERVERS | grep -q $HOSTNAME ; then
                    Server
                elif echo $CLIENTS | grep -q $HOSTNAME ; then
                    Client
                else
                    rlReport "Stray" "FAIL"
                fi

                rlPhaseStartCleanup
                    rlRun "popd"
                    rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
                rlPhaseEnd
            rlJournalPrintText
            rlJournalEnd
        </skeleton>
        <skeleton name="simple">
            rhts-run-simple-test $TEST ./test
        </skeleton>
        <skeleton name="empty">
        </skeleton>

        <skeleton name="library">
            # Include Beaker environment
            . /usr/bin/rhts-environment.sh || exit 1
            . /usr/share/beakerlib/beakerlib.sh || exit 1

            PACKAGE="<package/>"
            PHASE=${PHASE:-Test}

            rlJournalStart
                rlPhaseStartSetup
                    rlRun "rlImport <package/>/<testname/>"
                    rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
                    rlRun "pushd $TmpDir"
                rlPhaseEnd

                # Create file
                if [[ "$PHASE" =~ "Create" ]]; then
                    rlPhaseStartTest "Create"
                        fileCreate
                    rlPhaseEnd
                fi

                # Self test
                if [[ "$PHASE" =~ "Test" ]]; then
                    rlPhaseStartTest "Test default name"
                        fileCreate
                        rlAssertExists "$fileFILENAME"
                    rlPhaseEnd
                    rlPhaseStartTest "Test filename in parameter"
                        fileCreate "parameter-file"
                        rlAssertExists "parameter-file"
                    rlPhaseEnd
                    rlPhaseStartTest "Test filename in variable"
                        FILENAME="variable-file" fileCreate
                        rlAssertExists "variable-file"
                    rlPhaseEnd
                fi

                rlPhaseStartCleanup
                    rlRun "popd"
                    rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
                rlPhaseEnd
            rlJournalPrintText
            rlJournalEnd
        </skeleton>
        <skeleton name="parametrized">
            # Include Beaker environment
            . /usr/bin/rhts-environment.sh || exit 1
            . /usr/share/beakerlib/beakerlib.sh || exit 1

            # Packages to be tested
            PACKAGES=${PACKAGES:-<runfor />}
            # Other required packages
            REQUIRES=${REQUIRES:-<requires />}

            rlJournalStart
                rlPhaseStartSetup
                    rlAssertRpm --all
                    rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
                    rlRun "pushd $TmpDir"
                rlPhaseEnd

                rlPhaseStartTest
                    rlRun "touch foo" 0 "Creating the foo test file"
                    rlAssertExists "foo"
                    rlRun "ls -l foo" 0 "Listing the foo test file"
                rlPhaseEnd

                rlPhaseStartCleanup
                    rlRun "popd"
                    rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
                rlPhaseEnd
            rlJournalPrintText
            rlJournalEnd
        </skeleton>
    </skeletons>
            """)

        self.makefile = """
            export TEST=%s
            export TESTVERSION=%s

            BUILT_FILES=

            FILES=$(METADATA) %s

            .PHONY: all install download clean

            run: $(FILES) build
            	./runtest.sh

            build: $(BUILT_FILES)%s

            clean:
            	rm -f *~ $(BUILT_FILES)


            include /usr/share/rhts/lib/rhts-make.include

            $(METADATA): Makefile
            	@echo "Owner:           %s" > $(METADATA)
            	@echo "Name:            $(TEST)" >> $(METADATA)
            	@echo "TestVersion:     $(TESTVERSION)" >> $(METADATA)
            	@echo "Path:            $(TEST_DIR)" >> $(METADATA)%s

            	rhts-lint $(METADATA)
            """

        # skeleton for lib.sh file when creating library
        self.library = """
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   library-prefix = %s
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

            true <<'=cut'
            =pod

            =head1 NAME

            %s/%s - %s

            =head1 DESCRIPTION

            This is a trivial example of a BeakerLib library. Its main goal
            is to provide a minimal template which can be used as a skeleton
            when creating a new library. It implements function fileCreate().
            Please note that all library functions must begin with the same
            prefix which is defined at the beginning of the library.

            =cut

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Variables
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

            true <<'=cut'
            =pod

            =head1 VARIABLES

            Below is the list of global variables. When writing a new library,
            please make sure that all global variables start with the library
            prefix to prevent collisions with other libraries.

            =over

            =item fileFILENAME

            Default file name to be used when no provided ('foo').

            =back

            =cut

            fileFILENAME="foo"

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Functions
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

            true <<'=cut'
            =pod

            =head1 FUNCTIONS

            =head2 fileCreate

            Create a new file, name it accordingly and make sure (assert) that
            the file is successfully created.

                fileCreate [filename]

            =over

            =item filename

            Name for the newly created file. Optionally the filename can be
            provided in the FILENAME environment variable. When no file name
            is given 'foo' is used by default.

            =back

            Returns 0 when the file is successfully created, non-zero otherwise.

            =cut

            fileCreate() {
                local filename
                filename=${1:-$FILENAME}
                filename=${filename:-$fileFILENAME}
                rlRun "touch '$filename'" 0 "Creating file '$filename'"
                rlAssertExists "$filename"
                return $?
            }

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Execution
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

            true <<'=cut'
            =pod

            =head1 EXECUTION

            This library supports direct execution. When run as a task, phases
            provided in the PHASE environment variable will be executed.
            Supported phases are:

            =over

            =item Create

            Create a new empty file. Use FILENAME to provide the desired file
            name. By default 'foo' is created in the current directory.

            =item Test

            Run the self test suite.

            =back

            =cut

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Verification
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #
            #   This is a verification callback which will be called by
            #   rlImport after sourcing the library to make sure everything is
            #   all right. It makes sense to perform a basic sanity test and
            #   check that all required packages are installed. The function
            #   should return 0 only when the library is ready to serve.

            fileLibraryLoaded() {
                if rpm=$(rpm -q coreutils); then
                    rlLogDebug "Library coreutils/file running with $rpm"
                    return 0
                else
                    rlLogError "Package coreutils not installed"
                    return 1
                fi
            }

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            #   Authors
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

            true <<'=cut'
            =pod

            =head1 AUTHORS

            =over

            =item *

            %s

            =back

            =cut
            """

        self.list = []
        self.list.extend(findNodeNames(self.skeletons, "skeleton"))
        self.list.extend(findNodeNames(self.options.pref.skeletons, "skeleton"))
        self.common = False
        self.default(self.options.skeleton())
        self.requires = None
        self.rhtsrequires = None

    def replaceVariables(self, xml, test = None):
        """ Replace all <variable> tags with their respective values """
        skeleton = ""
        for child in xml.childNodes:
            # regular text node -> just copy
            if child.nodeType == child.TEXT_NODE:
                skeleton += child.nodeValue
            # xml tag -> try to expand value of test.tag.show()
            elif child.nodeType == child.ELEMENT_NODE:
                try:
                    name = child.tagName
                    # some variables need a special treatment
                    if name == "test":
                        value = test.fullPath()
                    elif name == "bugs":
                        value = test.testname.bugs.show()
                    elif name == "reproducers":
                        value = test.testname.bugs.reproducers.show()
                    elif name == "runfor":
                        value = ' '.join(test.runfor.data)
                    elif name == "requires":
                        value = ' '.join(test.requires.data)
                    else:
                        # map long names to the real vars
                        map = {
                            "description" : "desc",
                            "architectures" : "archs",
                        }
                        try: name = map[name]
                        except: pass
                        # get the value
                        value = eval("test." + name + ".show()")
                except:
                    # leave unknown xml tags as they are
                    skeleton += child.toxml()
                else:
                    skeleton += value
        return skeleton

    def getRuntest(self, test = None):
        """ Return runtest.sh skeleton corresponding to user choice """
        # get the template from predefined or user skeletons
        skeleton = findNode(self.skeletons, "skeleton", self.data) \
                or findNode(self.options.pref.skeletons, "skeleton", self.data)
        # substitute variables, convert to plain text
        skeleton = self.replaceVariables(skeleton, test)
        # return dedented skeleton without trailing whitespace
        skeleton = re.sub("\n\s+$", "\n", skeleton)
        return dedentText(skeleton)

    def getRhtsRequires(self):
        """ Return packages/libraries listed in the arguments of a skeleton, if any """
        # get the template from predefined or user skeletons
        skeleton = findNode(self.skeletons, "skeleton", self.data) \
                or findNode(self.options.pref.skeletons, "skeleton", self.data)
        if not skeleton:
            return None
        try:
            rhtsrequires = skeleton.getAttribute("rhtsrequires")
            return rhtsrequires
        except:
            print("getRhtsRequires exception")

    def getMakefile(self, type, testname, version, author, reproducers, meta):
        """ Return Makefile skeleton """

        # if test type is Library, include lib.sh to the Makefile instead of PURPOSE
        files = ["runtest.sh", "Makefile"]
        files.append("lib.sh" if type == "Library" else "PURPOSE")
        build = ["runtest.sh"]
        # add "test" file when creating simple test
        if self.data == "simple":
            files.append("test")
            build.append("test")
        # include the reproducers in the lists as well
        if reproducers:
            for reproducer in reproducers:
                files.append(reproducer)
                # add script-like reproducers to build tag
                if RegExpScript.search(reproducer):
                    build.append(reproducer)
        chmod = "\n            	test -x %s || chmod a+x %s"
        return dedentText(self.makefile % (testname, version, " ".join(files),
                "".join([chmod % (file, file) for file in build]), author, meta))

    def getVimHeader(self):
        """ Insert the vim completion header if it's an beakerlib skeleton """
        if re.search("rl[A-Z]", self.getRuntest()):
            return comment(VimDictionary,
                    top = False, bottom = False, padding = 0) + "\n"
        else:
            return ""

    def getLibrary(self, testname, description, package, author):
        """ Return lib.sh skeleton """
        return dedentText(self.library.lstrip() %
                (testname, package, testname, description, author))

class Author(Inquisitor):
    """ Author's name """

    def init(self):
        self.name = "Author"
        self.question = "Author's name"
        self.description = """Put your name [middle name] and surname here,
                abbreviations allowed."""
        # ask for author when run for the first time
        self.common = self.options.pref.firstRun
        self.default(self.options.author())

    def valid(self):
        return self.data is not None and self.data not in ["", "?"]


class Email(Inquisitor):
    """ Author's email """

    def init(self):
        self.name = "Email"
        self.question = "Author's email"
        self.description = """Email address in lower case letters,
                dots and dashes. Underscore allowed before the "@" only."""
        # ask for author when run for the first time
        self.common = self.options.pref.firstRun
        self.default(self.options.email())

    def valid(self):
        return self.data is not None \
            and RegExpEmail.match(self.data)


class Desc(Inquisitor):
    """ Description """

    def init(self):
        self.name = "Description"
        self.question = "Short description"
        self.description = "Provide a short sentence describing the test."
        self.default(self.options.desc())

    def valid(self):
        return self.data is not None and self.data not in ["", "?"]


class Test(SingleChoice):
    """ Test class containing all the information necessary for building a test """

    def init(self):
        self.name = "Test fields"
        if self.options.makefile:
            self.question = "Ready to write the new Makefile, "\
                    "please review or make the changes"
        else:
            self.question = "Ready to create the test, please review"
        self.description = "Type a few letters from field name to "\
                "edit or press ENTER to confirm. Use the \"write\" keyword "\
                "to save current settings as preferences."
        self.list = []
        self.default(["", "Everything OK"])

        # possibly print first time welcome message
        if self.options.pref.firstRun:
            print(dedentText("""
                Welcome to The Beaker Wizard!
                ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                It seems, you're running the beaker-wizard for the first time.
                I'll try to be a little bit more verbose. Should you need
                any help in the future, just try using the "?" character.
                """, count = 16))

        # gather all test data
        self.testname = Name(self.options)
        self.path = Path(self.options)
        self.type = Type(self.options, suggest = self.testname.bugs.suggestType() or
                ('Library' if 'library' in self.options.skeleton() else None))
        self.package = Package(self.options,
                suggest = self.testname.bugs.getComponent())
        self.namespace = Namespace(self.options)
        self.desc = Desc(self.options,
                suggest = self.testname.bugs.suggestDescription())

        self.runfor = RunFor(self.options, suggest = self.package.value())
        self.requires = Requires(self.options, suggest = self.package.value())
        self.archs = Architectures(self.options)
        self.releases = Releases(self.options)
        self.time = Time(self.options)

        self.version = Version(self.options)
        self.priority = Priority(self.options)
        self.confidential = Confidential(self.options,
                suggest = self.testname.bugs.suggestConfidential())
        self.destructive = Destructive(self.options)
        self.license = License(self.options)

        self.skeleton = Skeleton(self.options,
                suggest = self.type.suggestSkeleton())
        self.author = Author(self.options)
        self.email = Email(self.options)

        self.rhtsrequires = RhtsRequires(self.options, suggest = self.skeleton.getRhtsRequires())

        # we escape review only in force mode
        if not self.options.force(): self.confirm = True
        if not self.confirm: self.format()

    def valid(self):
        return self.data is not None \
            and self.data not in ["?"] \
            and self.edit(checkOnly = True)

    def format(self):
        """ Format all test fields into nice table """
        print()
        print(self.fullPath())
        print()
        self.namespace.format()
        self.package.format()
        self.type.format()
        self.path.format()
        self.testname.format()
        self.desc.format()
        print()
        self.testname.bugs.format()
        if not self.options.makefile: # skip in makefile edit mode
            self.testname.prefix.format()
            self.testname.bugs.reproducers.format()
        print()
        self.runfor.format()
        self.requires.format()
        self.rhtsrequires.format()
        self.archs.format()
        self.releases.format()
        self.version.format()
        self.time.format()
        print()
        self.priority.format()
        self.license.format()
        self.confidential.format()
        self.destructive.format()
        print()
        if not self.options.makefile:
            self.skeleton.format() # irrelevant in makefile edit mode
        self.author.format()
        self.email.format()
        print()

    def heading(self):
        SingleChoice.heading(self)
        self.format()

    def edit(self, checkOnly = False):
        """ Edit test fields (based on just few letters from field name)
        If checkOnly is on then checks only for valid field name """

        # quit
        if re.match("q|exit", self.data, re.I):
            print("Ok, quitting for now. See you later ;-)")
            sys.exit(0)
        # no (seems the user is beginner -> turn on verbosity)
        elif re.match("no?$", self.data, re.I):
            self.options.opt.verbose = True
            return True
        # yes
        elif RegExpYes.match(self.data):
            return True

        # check all fields for matching string (and edit if not checking only)
        for field in self.testname, self.package, self.namespace, self.runfor, \
                self.requires, self.rhtsrequires, self.package, self.releases, self.version, \
                self.time, self.desc, self.destructive, self.archs, \
                self.path, self.priority, self.confidential, self.license, \
                self.skeleton, self.author, self.email, self.testname.prefix, \
                self.testname.bugs.reproducers:
            if field.matchName(self.data):
                if not checkOnly: field.edit()
                return True

        # bugs & type have special treatment
        if self.type.matchName(self.data):
            if not checkOnly and self.type.edit():
                # if type has changed suggest a new skeleton
                self.skeleton = Skeleton(self.options,
                        suggest = self.type.suggestSkeleton())
            return True
        elif self.testname.bugs.matchName(self.data):
            if not checkOnly and self.testname.bugs.edit():
                # if bugs changed, suggest new name & desc & reproducers
                if self.testname.bugs.fetchBugDetails():
                    self.testname.edit(self.testname.bugs.suggestTestName())
                    self.desc.edit(self.testname.bugs.suggestDescription())
                    self.testname.bugs.reproducers.edit()
            return True
        # write preferences
        elif re.match("w", self.data, re.I):
            if not checkOnly:
                self.savePreferences(force = True)
            return True
        # bad option
        else:
            return False

    def relativePath(self):
        """ Return relative path from package directory"""
        path = "%s%s/%s" % (
            self.type.value(),
            self.path.value(),
            self.testname.value())
        if self.options.opt.use_current_dir:
            path = "."
        return path

    def fullPath(self):
        """ Return complete test path """
        return "/%s/%s/%s" % (
            self.namespace.value(),
            self.package.value(),
            self.relativePath())

    def formatAuthor(self):
        """ Format author with email """
        return "%s <%s>" % (self.author.value(), self.email.value())

    def formatHeader(self, filename):
        """ Format standard header """
        return "%s of %s\nDescription: %s\nAuthor: %s" % (
            filename, self.fullPath(),
            self.desc.value(),
            self.formatAuthor())

    def formatMakefile(self):
        # add 'Provides' to the Makefile when test type is 'Library'
        if self.type.value() == "Library":
            provides = self.formatMakefileLine(
                    name="Provides",
                    value="library({0}/{1})".format(
                            self.package.value(), self.testname.value()))
        else:
            provides = ""
        return (
            comment(self.formatHeader("Makefile")) + "\n" +
            comment(self.license.get(), top = False) + "\n" +
            self.skeleton.getMakefile(
                self.type.value(),
                self.fullPath(),
                self.version.value(),
                self.formatAuthor(),
                self.testname.bugs.reproducers.value(),
                self.desc.formatMakefileLine() +
                self.type.formatMakefileLine(name = "Type") +
                self.time.formatMakefileLine(name = "TestTime") +
                self.runfor.formatMakefileLine(name = "RunFor") +
                self.requires.formatMakefileLine(name = "Requires") +
                self.rhtsrequires.formatMakefileLine(name = "RhtsRequires") +
                provides +
                self.priority.formatMakefileLine() +
                self.license.formatMakefileLine() +
                self.confidential.formatMakefileLine() +
                self.destructive.formatMakefileLine() +
                self.testname.bugs.formatMakefileLine(name = "Bug") +
                self.releases.formatMakefileLine() +
                self.archs.formatMakefileLine()))

    def savePreferences(self, force = False):
        """ Save user preferences (well, maybe :-) """
        # update user preferences with current settings
        self.options.pref.update(
            self.author.value(),
            self.email.value(),
            self.options.confirm(),
            self.type.value(),
            self.namespace.value(),
            self.time.value(),
            self.priority.value(),
            self.confidential.value(),
            self.destructive.value(),
            self.testname.prefix.value(),
            self.license.value(),
            self.skeleton.value())
        # and possibly save them to disk
        if force or self.options.pref.firstRun or self.options.write():
            self.options.pref.save()

    def createFile(self, filename, content, mode=None):
        """ Create single test file with specified content """
        fullpath = self.relativePath() + "/" + filename
        addedToGit = ""

        # overwrite existing?
        if os.path.exists(fullpath):
            sys.stdout.write(fullpath + " already exists, ")
            if self.options.force():
                print("force on -> overwriting")
            else:
                sys.stdout.write("overwrite? [y/n] ")
                sys.stdout.flush()
                try:
                    # Even though unicode_literals are imported, stdin still produces ascii
                    answer = sys.stdin.readline().strip()
                    answer = answer.decode("utf-8")
                # Python 3 doesn't have decode
                except AttributeError:
                    pass
                if not re.match("y", answer, re.I):
                    print("Ok skipping. Next time use -f if you want to overwrite files.")
                    return

        # let's write it
        try:
            file = open(fullpath, "wb")
            file.write(content.encode("utf-8"))
            file.close()

            # change mode if provided
            if mode: os.chmod(fullpath, mode)

            # and, optionally, add to Git
            if self.options.opt.git:
                addToGit(fullpath)
                addedToGit = ", added to git"
        except IOError:
            print("Cannot write to %s" % fullpath)
            sys.exit(3)
        else:
            print("File", fullpath, "written" + addedToGit)

    def create(self):
        """ Create all necessary test files """
        # if in the Makefile edit mode, just save the Makefile
        if self.options.makefile:
            self.options.makefile.save(self.fullPath(), self.version.value(),
                    self.formatMakefile())
            return

        # set file vars
        test = self.testname.value()
        package = self.package.value()
        author = self.formatAuthor()
        description = self.desc.value()
        path = self.relativePath()
        fullpath = self.fullPath()
        addedToGit = ""

        # create test directory
        class AlreadyExists(Exception): pass
        try:
            # nothing to do if already exists
            if os.path.isdir(path):
                raise AlreadyExists
            # otherwise attempt to create the whole hiearchy
            else:
                os.makedirs(path)
        except OSError:
            print("Bad, cannot create test directory %s :-(" % path)
            sys.exit(1)
        except AlreadyExists:
            print("Well, directory %s already exists, let's see..." % path)
        else:
            print("Directory %s created %s" % (path, addedToGit))

        # if test type is Library, create lib.sh and don't include PURPOSE
        if self.type.value() == "Library":
            self.createFile("lib.sh", content =
                    "#!/bin/bash\n" +
                    self.skeleton.getVimHeader() +
                    comment(self.formatHeader("lib.sh")) + "\n" +
                    comment(self.license.get(), top=False, bottom=False) +
                    "\n" +
                    self.skeleton.getLibrary(
                            test, description, package, author))
        # for regular tests create PURPOSE
        else:
            self.createFile("PURPOSE", content =
                self.formatHeader("PURPOSE") + "\n" +
                self.testname.bugs.formatBugDetails())

        # runtest.sh
        self.createFile("runtest.sh", content =
            "#!/bin/bash\n" +
            self.skeleton.getVimHeader() +
            comment(self.formatHeader("runtest.sh")) + "\n" +
            comment(self.license.get(), top = False) + "\n" +
            self.skeleton.getRuntest(self),
            mode=0o755
            )

        # Makefile
        self.createFile("Makefile", content = self.formatMakefile())

        # test
        if self.skeleton.value() == "simple":
            self.createFile("test", content = "")

        # download reproducers
        self.testname.bugs.reproducers.download(self.relativePath())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    # parse options and user preferences
    options = Options()

    # possibly display help or version message
    Help(options)

    # ask for all necessary details
    test = Test(options)

    # keep asking until everything is OK
    while not RegExpYes.match(test.value()):
        test.edit()
        test.default(["", "Everything OK"])
        test.ask(force = True)

    # and finally create the test file structure
    test.create()
    test.savePreferences()
    return 0

if __name__ == '__main__':
    sys.exit(main())
