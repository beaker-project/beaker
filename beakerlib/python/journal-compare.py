#!/usr/bin/env python

# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Petr Muller <pmuller@redhat.com>

import xml.dom.minidom
import sys

class Result:
	def __init__(self):
		self.name = ""
		self.result = ""
		self.messages = []

	def addMessage(self, message):
		self.messages.append(message)

	def canBePass(self):
		if self.result == "":
			self.result = "PASS"
	def canBeWarn(self):
		if self.result != "FAIL":
			self.result = "WARN"
	def isFail(self):
		self.result = "FAIL"

class Metric:
	def __init__(self, name, value, type, tolerance):
		self.value = value
		self.type  = type
		self.tolerance = tolerance
		self.name = name

	def compare(self, other):
		if self.type == "low":
			first = self.value
			second = other.value
			message = "First %s, second %s, toleranced first %s" % (first, second, first+first*tolerance)
		else:
			first = other.value
			second = self.value
			message = "First %s, second %s, toleranced first %s" % (second, first, second+second*tolerance)

		result = Result()
		result.name = self.name
		result.addMessage(message)

		if first >= second:
			result.result = "PASS"
		elif first+first*tolerance >= second:
			result.result = "WARN"
		else:
			result.result = "FAIL"
		return result

class Test:
	def __init__(self, name):
		self.name = name
		self.passes   = 0
		self.failures = 0
		self.aborts   = 0
		self.warnings = 0

	def addResult(self, result):
		if result == "PASS":
			self.passes += 1
		elif result == "FAIL":
			self.failures += 1
		elif result == "ABORT":
			self.aborts += 1
		elif result == "WARN":
			self.warnings += 1

	def compare(self, other):
		result = Result()
		result.name = self.name
		if self.passes <= other.passes:
			result.canBePass()
			if 0 not in (self.passes, other.passes):
				result.addMessage("PASSES OK (old %s, new %s)" % (self.passes, other.passes))
		else:
			result.canBeWarn()
			result.addMessage("PASSES NOT OK (old %s, new %s)" % (self.passes, other.passes))

		if self.failures >= other.failures and other.failures == 0:
			result.canBePass()
			if 0 not in (self.failures, other.failures):
				result.addMessage("FAILS OK (old %s, new %s)" % (self.failures, other.failures))
		elif self.failures >= other.failures:
			result.canBeWarn()
			if 0 not in (self.failures, other.failures):
				result.addMessage("FAILS REMAINING (old %s, new %s)" % (self.failures, other.failures))
		elif self.failures < other.failures and self.passes > other.passes:
			result.isFail()
			result.addMessage("FAILS REGRESSION (old %s, new %s)" % (self.failures, other.failures))
		else:
			result.isFail()
			result.addMessage("FAILS NOT OK (old %s, new %s)" % (self.failures, other.failures))

		if self.aborts >= other.aborts and other.aborts == 0:
			result.canBePass()
			if 0 not in (self.aborts, other.aborts):
				result.addMessage("ABORTS OK (old %s, new %s)" % (self.aborts, other.aborts))
		elif self.aborts >= other.aborts:
			result.canBeWarn()
			if 0 not in (self.aborts, other.aborts):
				result.addMessage("ABORTS REMAINING (old %s, new %s)" % (self.aborts, other.aborts))
		else:
			result.isFail()
			result.addMessage("ABORTS NOT OK (old %s, new %s)" % (self.passes, other.passes))

		if self.warnings >= other.warnings and other.warnings == 0:
			result.canBePass()
			if 0 not in (self.warnings, other.warnings):
				result.addMessage("WARNINGS OK (old %s, new %s)" % (self.warnings, other.warnings))
		elif self.warnings >= other.warnings:
			result.canBeWarn()
			if 0 not in (self.warnings, other.warnings):
				result.addMessage("WARNINGS REMAINING (old %s, new %s)" % (self.warnings, other.warnings))
		else:
			result.isFail()
			result.addMessage("WARNINGS NOT OK (old %s, new %s)" % (self.warnings, other.warnings))

		return result

class TestSet:
	def __init__(self):
		self.results = {}

	def addTestResult(self, name, result):
		if not self.results.has_key(name):
			self.results[name] = Test(name)
		self.results[name].addResult(result)

	def compare(self, other):
		result_list = []
		for key in self.results.keys():
			try:
				result_list.append(self.results[key].compare(other.results[key]))
			except KeyError:
				print "[WARN] Could not find corresponding test for: %s" % key
		return result_list

try:
  old = sys.argv[1]
  new = sys.argv[2]
except IndexError:
  old = "old/rcw-journal"
  new = "new/rcw-journal"

journal_old = xml.dom.minidom.parse(old)
journal_new = xml.dom.minidom.parse(new)

old_log = journal_old.getElementsByTagName("log")[0]
new_log = journal_new.getElementsByTagName("log")[0]

old_phases = old_log.getElementsByTagName("phase")
new_phases = new_log.getElementsByTagName("phase")

walk_through = range(len(new_phases))

for i in walk_through:
	old_type, old_name = old_phases[i].getAttribute("type"), old_phases[i].getAttribute("name")
	new_type, new_name = new_phases[i].getAttribute("type"), new_phases[i].getAttribute("name")

	if old_type == new_type and old_name == new_name:
		print "Types match, so we are comparing phase %s of type %s" % (old_type, new_type)
		old_tests = TestSet()
		new_tests = TestSet()
		old_metrics = {}
		new_metrics = {}

		for phases, results, metrics in ((old_phases, old_tests, old_metrics), (new_phases, new_tests, new_metrics)):
			for test in phases[i].getElementsByTagName("test"):
				key = test.getAttribute("message")
				result = test.childNodes[0].data.strip()
				results.addTestResult(key, result)

			for metric in phases[i].getElementsByTagName("metric"):
				key = metric.getAttribute("name")
				value = float(metric.childNodes[0].data.strip())
				tolerance = float(metric.getAttribute("tolerance"))
				metrics[key] = Metric(key, value, metric.getAttribute("type"), tolerance)

		print "==== Actual compare ===="
		print " * Metrics * "
		metric_results = []
		for key in old_metrics.keys():
			metric_results.append(old_metrics[key].compare(new_metrics[key]))
		for metric in metric_results:
			for message in metric.messages:
				print "[%s] %s (%s)" % (metric.result, metric.name, message)
		print " * Tests * "
		test_results = old_tests.compare(new_tests)
		for test in test_results:
			print "[%s] %s" % (test.result, test.name)
			for message in test.messages:
				print "\t - %s" % message

	else:
		print "We are not doing any compare, types dont match"
