#!/usr/bin/env python

# Authors:  Petr Muller     <pmuller@redhat.com>
#
# Description: Provides journalling capabilities for RHTS tests
#
# Copyright (c) 2008 Red Hat, Inc. All rights reserved. This copyrighted
# material is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

from xml.dom.minidom import getDOMImplementation
import xml.dom.minidom
from optparse import OptionParser
import sys
import os
import datetime
import rpm
import socket

def wrap(text, width):    
    return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line)-line.rfind('\n')-1
                         + len(word.split('\n',1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )

def printPurpose(message):
  printHeadLog("Test description")
  print wrap(message, 80)

def printLog(message, prefix="LOG"):
  print ":: [%s] :: %s" % (prefix.center(10), message)

def printHeadLog(message):
  print "\n::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
  printLog(message)
  print "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n"

def getAllowedSeverities(treshhold):
  severities ={"DEBUG":0, "INFO":1, "WARNING":2, "ERROR":3, "FATAL":4, "LOG":5}
  allowed_severities = []
  for i in severities:
	  if (severities[i] >= severities[treshhold]): allowed_severities.append(i)
  return allowed_severities

def printPhaseLog(phase,severity):
  phaseName = phase.getAttribute("name")
  phaseResult = phase.getAttribute("result")
  printHeadLog(phaseName)
  passed = 0
  failed = 0
  for node in phase.childNodes:
    if node.nodeName == "message":
      if node.getAttribute("severity") in getAllowedSeverities(severity):
        if (len(node.childNodes) > 0):
          text = node.childNodes[0].nodeValue
        else:
          text = ""
        printLog(text, node.getAttribute("severity"))
    elif node.nodeName == "test":
      result = node.childNodes[0].nodeValue
      if result == "FAIL":
        printLog("%s" % node.getAttribute("message"), "FAIL")
        failed += 1
      else:
        printLog("%s" % node.getAttribute("message"), "PASS")
        passed += 1

  printLog("Assertions: %s good, %s bad" % (passed, failed))
  printLog("RESULT: %s" % phaseName, phaseResult)

def createLog(id,severity):
  jrnl = openJournal(id)
  printHeadLog("TEST PROTOCOL")

  for node in jrnl.childNodes[0].childNodes:
    if node.nodeName == "test_id":
      printLog("Test run ID   : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "package":
      printLog("Package       : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "testname":
      printLog("Test name     : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "pkgdetails":
      printLog("Installed:    : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "release":
      printLog("Distro:       : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "starttime":
      printLog("Test started  : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "endtime":
      printLog("Test finished : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "arch":
      printLog("Architecture  : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "hostname":
      printLog("Hostname      : %s" % node.childNodes[0].nodeValue)
    elif node.nodeName == "purpose":
      printPurpose(node.childNodes[0].nodeValue)
    elif node.nodeName == "log":
      for nod in node.childNodes:
        if nod.nodeName == "message":
          if nod.getAttribute("severity") in getAllowedSeverities(severity):
            if (len(nod.childNodes) > 0):
              text = nod.childNodes[0].nodeValue
            else:
              text = ""
            printLog(text, nod.getAttribute("severity"))
        elif nod.nodeName == "test":
          printLog("TEST BUG: Assertion not in phase", "WARNING")
          result = nod.childNodes[0].nodeValue
          if result == "FAIL":
            printLog("%s" % nod.getAttribute("message"), "FAIL")
          else:
            printLog("%s" % nod.getAttribute("message"), "PASS")
        elif nod.nodeName == "metric":
          printLog("%s: %s" % (nod.getAttribute("name"), nod.childNodes[0].nodeValue), "METRIC")
        elif nod.nodeName == "phase":
          printPhaseLog(nod,severity)

def initializeJournal(id, test, package):
  impl = getDOMImplementation()  
  newdoc = impl.createDocument(None, "RHTS_TEST", None)
  top_element = newdoc.documentElement
  testidEl    = newdoc.createElement("test_id")
  testidCon   = newdoc.createTextNode(str(id))  
  packageEl   = newdoc.createElement("package")
  packageCon  = newdoc.createTextNode(str(package))

  pkgdetails = []

  ts = rpm.ts()
  mi = ts.dbMatch("name", package)
  for pkg in mi:
    pkgDetailsEl = newdoc.createElement("pkgdetails")
    pkgDetailsCon = newdoc.createTextNode("%(name)s-%(version)s-%(release)s.%(arch)s" % pkg)
    pkgdetails.append((pkgDetailsEl, pkgDetailsCon))

  startedEl   = newdoc.createElement("starttime")
  startedCon  = newdoc.createTextNode(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

  endedEl     = newdoc.createElement("endtime")
  endedCon    = newdoc.createTextNode(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

  hostnameEl     = newdoc.createElement("hostname")
  hostnameCon   = newdoc.createTextNode(socket.gethostbyaddr(socket.gethostname())[0])

  archEl     = newdoc.createElement("arch")
  archCon   = newdoc.createTextNode(os.uname()[-1])

  testEl      = newdoc.createElement("testname")
  testCon     = newdoc.createTextNode(str(test))

  releaseEl   = newdoc.createElement("release")
  releaseCon  = newdoc.createTextNode(open("/etc/redhat-release",'r').read().strip())
  logEl       = newdoc.createElement("log")
  purposeEl   = newdoc.createElement("purpose")
  try:  
    purpose_file = open("PURPOSE", 'r')
    purpose = purpose_file.read()
    purpose_file.close()
  except IOError:
    purpose = "Cannot find the PURPOSE file of this test. Could be a missing, or rlInitializeJournal wasn't called from appropriate location"

  purposeCon  = newdoc.createTextNode(purpose)

  testidEl.appendChild(testidCon)
  packageEl.appendChild(packageCon)
  for installed_pkg in pkgdetails:
    installed_pkg[0].appendChild(installed_pkg[1])
  startedEl.appendChild(startedCon)
  endedEl.appendChild(endedCon)
  testEl.appendChild(testCon)
  releaseEl.appendChild(releaseCon)
  purposeEl.appendChild(purposeCon)
  hostnameEl.appendChild(hostnameCon)
  archEl.appendChild(archCon)

  top_element.appendChild(testidEl)
  top_element.appendChild(packageEl)
  for installed_pkg in pkgdetails:
    top_element.appendChild(installed_pkg[0])
  top_element.appendChild(startedEl)
  top_element.appendChild(endedEl)
  top_element.appendChild(testEl)
  top_element.appendChild(releaseEl)
  top_element.appendChild(hostnameEl)
  top_element.appendChild(archEl)
  top_element.appendChild(purposeEl)
  top_element.appendChild(logEl)
  
  saveJournal(newdoc, id)

def saveJournal(newdoc, id):
  output = open('/tmp/rhts_journal.%s' % id, 'wb')
  output.write(newdoc.toxml())
  output.close()

def _openJournal(id):
  jrnl = xml.dom.minidom.parse("/tmp/rhts_journal.%s" % id )
  return jrnl

def openJournal(id):
  try:
    jrnl = _openJournal(id)
  except (IOError, EOFError):
    printLog('Journal not initialised? Trying it now.', 'RHTSlib_WARNING')
    initializeJournal(id,
                      os.environ.get("TEST", "some test"),
                      os.environ.get("PACKAGE", "some package"))
    jrnl = _openJournal(id)
  return jrnl

def getLogEl(jrnl):
  for node in jrnl.getElementsByTagName('log'):
    return node
  
def getLastUnfinishedPhase(tree):
  for node in tree.getElementsByTagName('phase'):
    if node.getAttribute('result') == 'unfinished':
      return node
  return tree 

def addPhase(id, name, type):
  jrnl = openJournal(id)  
  log = getLogEl(jrnl)  
  phase = jrnl.createElement("phase")
  phase.setAttribute("name", name)
  phase.setAttribute("result", 'unfinished')
  phase.setAttribute("type", type)
  log.appendChild(phase)
  saveJournal(jrnl, id)

def finPhase(id):
  jrnl  = openJournal(id)
  phase = getLastUnfinishedPhase(getLogEl(jrnl))
  type  = phase.getAttribute('type')
  name  = phase.getAttribute('name')
  end   = jrnl.getElementsByTagName('endtime')[0]
  end.childNodes[0].nodeValue = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  passed = failed = 0
  for node in phase.childNodes:
    if node.nodeName == "test":
      result = node.childNodes[0].nodeValue
      if result == "FAIL":
        failed += 1
      else:
        passed += 1

  if failed == 0:
    phase.setAttribute("result", 'PASS')
  else:
    phase.setAttribute("result", type)

  phase.setAttribute('score', str(failed))
  saveJournal(jrnl, id)
  return (phase.getAttribute('result'), phase.getAttribute('score'), type, name)

def getPhase(tree):
  for node in tree.getElementsByTagName("phase"):
    if node.getAttribute("name") == name:
      return node
  return tree

def addMessage(id, message, severity):
  jrnl = openJournal(id)  
  log = getLogEl(jrnl)  
  add_to = getLastUnfinishedPhase(log)    
  
  msg = jrnl.createElement("message")
  msg.setAttribute("severity", severity)  
  
  msgText = jrnl.createTextNode(message)
  msg.appendChild(msgText)
  add_to.appendChild(msg)
  saveJournal(jrnl, id)

def addTest(id, message, result="FAIL"):
  jrnl = openJournal(id)
  log = getLogEl(jrnl)
  add_to = getLastUnfinishedPhase(log)
  
  msg = jrnl.createElement("test")
  msg.setAttribute("message", message)
  
  msgText = jrnl.createTextNode(result)
  msg.appendChild(msgText)
  add_to.appendChild(msg)
  saveJournal(jrnl, id)

def addMetric(id, type, name, value, tolerance):
  jrnl = openJournal(id)
  log = getLogEl(jrnl)
  add_to = getLastUnfinishedPhase(log)

  metric = jrnl.createElement("metric")
  metric.setAttribute("type", type)
  metric.setAttribute("name", name)
  metric.setAttribute("tolerance", str(tolerance))

  metricText = jrnl.createTextNode(str(value))
  metric.appendChild(metricText)
  add_to.appendChild(metric)
  saveJournal(jrnl, id)

def dumpJournal(id):  
  print openJournal(id).toprettyxml()
  
def need(args):
  if None in args:
    print "need Blargh!"
    sys.exit(1)  

DESCRIPTION = "Wrapper for operations above rhtslib journal"
optparser = OptionParser(description=DESCRIPTION)

optparser.add_option("-i", "--id", default=None, dest="testid", metavar="TEST-ID")
optparser.add_option("-p", "--package", default=None, dest="package", metavar="PACKAGE")
optparser.add_option("-t", "--test", default=None, dest="test", metavar="TEST")
optparser.add_option("-n", "--name", default=None, dest="name", metavar="NAME")
optparser.add_option("-s", "--severity", default=None, dest="severity", metavar="SEVERITY")
optparser.add_option("-m", "--message", default=None, dest="message", metavar="MESSAGE")
optparser.add_option("-r", "--result", default=None, dest="result")
optparser.add_option("-v", "--value", default=None, dest="value")
optparser.add_option("--tolerance", default=None, dest="tolerance")
optparser.add_option("--type", default=None, dest="type")


(options, args) = optparser.parse_args()

if len(args) != 1:
  print "Argh Blargh!: %s" % len(args)
  sys.exit(1)

command = args[0]

if command == "init":
  need((options.testid, options.test, options.package))  
  initializeJournal(options.testid, options.test, options.package) 
elif command == "dump":
  need((options.testid,))
  dumpJournal(options.testid)
elif command == "printlog":
  need((options.testid,options.severity))
  createLog(options.testid, options.severity)
elif command == "addphase":
  need((options.testid, options.name, options.type))
  addPhase(options.testid, options.name, options.type)
  printHeadLog(options.name)
elif command == "log":
  need((options.message, options.testid))  
  severity = options.severity
  if severity is None:
    severity = "LOG"
  addMessage(options.testid, options.message, severity)
elif command == "test":
  need((options.testid, options.message))  
  result = options.result
  if result is None:
    result = "FAIL"
  addTest(options.testid, options.message, result)
  printLog(options.message, result)
elif command == "metric":
  need((options.testid, options.name, options.type, options.value, options.tolerance))
  try:
    addMetric(options.testid, options.type, options.name, float(options.value), float(options.tolerance))
  except ValueError:
    sys.exit(1)
elif command == "finphase":
  need((options.testid,))
  result, score, type, name = finPhase(options.testid)
  print "%s:%s:%s" % (type,result,name)
  print >> sys.stderr, score
  sys.exit(int(score))

sys.exit(0)
