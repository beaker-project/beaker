# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import re
from beah.core import event
from beah.core.constants import RC
from beah.misc import dict_update

class TestHarnessTAP2EventList(object):
    """\
TaskFilter for analysing Perl's Test::Harness:TAP as defined by
http://search.cpan.org/~petdance/Test-Harness-2.64/lib/Test/Harness/TAP.pod
"""
    comment_re = re.compile('^(.*?)\s*#\s*(.*)')
    plan_re = re.compile('^(\d+)\.\.(\d+)\s*$')
    testcase_re = re.compile('^(not\s+)?ok\s+(\d+\s+)?(.*)$')
    directive_re = re.compile('^(?i)((skip|todo)\S*)?(.*)$')
    bail_out_re = re.compile('^(?i)Bail out!\s*(.*)')
    error_re = re.compile('\S+')

    def __init__(self):
        self.reset()

    def reset(self):
        self.test_case = 0
        self.test_cases = {}
        self.plan = None

    origin = {'origin':'harness'}

    def __call__(self, iline):
        answ = []
        result_dict = {}

        m_comment = self.comment_re.match(iline)
        if m_comment:
            (line, comment) = m_comment.groups()
            m_directive = self.directive_re.match(comment)
            if m_directive:
                (_, directive, _) = m_directive.groups()
            else:
                directive = ''
        else:
            line = iline
            comment = ''
            directive = ''
        if comment: result_dict['diagnostics'] = comment
        if directive: result_dict['directive'] = directive

        if not self.plan:
            m_plan = self.plan_re.match(line)
            if m_plan:
                plan = m_plan.groups()
                self.plan = (int(plan[0]), int(plan[1]))
                self.test_case = self.plan[0]-1
                return answ

        m_testcase = self.testcase_re.match(line)
        if m_testcase:
            if not self.plan:
                self.plan = (-1, -1)
            if not m_testcase.group(1):
                result = RC.PASS
            else:
                result = RC.FAIL
            self.test_case = int(m_testcase.group(2) or '0') or self.test_case+1
            description = m_testcase.group(3)
            if self.plan[0] >= 0:
                if self.test_case < self.plan[0] or \
                        self.test_case > self.plan[1]:
                    answ.append(event.lwarning(
                            message="${test_case} is out of plan range ${test_plan}!",
                            origin=self.origin,
                            test_case=self.test_case,
                            test_plan=self.plan))
            if self.test_cases.has_key(self.test_case):
                if self.test_cases[self.test_case] != result:
                    answ.append(event.lwarning(
                            message="${test_case} was processed already and returned different result ${prev_result}!",
                            origin=self.origin,
                            test_case=self.test_case,
                            prev_result=result))
                else:
                    answ.append(event.lwarning(
                            message="${test_case} was processed already",
                            origin=self.origin,
                            test_case=self.test_case))
            self.test_cases[self.test_case] = result
            result_dict['test_case'] = self.test_case
            if description:
                result_dict['message'] = description
            answ.append(event.result(result,**result_dict))
            return answ

        m_bailout = self.bail_out_re.match(line)
        if m_bailout:
            result_dict['message'] = line
            answ.append(event.result(RC.FATAL, **result_dict))
            return answ

        if self.error_re.match(line):
            # FIXME: using ${var} in strings. This is both well understood and
            # easy to process on server
            dict_update(result_dict,
                    origin=self.origin,
                    message="${line} does not match Test::Harness::TAP format",
                    line=line)
            # we update result_dict in this case, not to lose information
            answ.append(event.lwarning(**result_dict))
            return answ

        if comment or directive:
            answ.append(event.linfo(**result_dict))
            return answ

        return answ

################################################################################
# Some useful constructs:
################################################################################

# FIXME: Is this useful outside of this?
# FIXME: Use default serializer from configuration
from beah.filters import JSONSerializer

def Str2Task(data, filter=None, serializer=None):
    str_list = data.split('\n')
    if not str_list:
        return
    serializer = serializer or JSONSerializer().proc_obj
    filter = filter or TestHarnessTAP2EventList()
    for str in str_list:
        if str:
            for event in filter(str):
                event and serializer(event)

def Stdin2Task(filter=None, serializer=None):
    from sys import stdin
    serializer = serializer or JSONSerializer().proc_obj
    filter = filter or TestHarnessTAP2EventList()
    for line in stdin:
        Str2Task(line, filter, serializer)

################################################################################
# TESTING:
################################################################################

if __name__ == '__main__':
    from pprint import pprint
    def ltest(a_list):
        print '================================================================================'
        pprint(a_list)
        print '--------------------------------------------------------------------------------'
        filter = TestHarnessTAP2EventList()
        for str in a_list:
            pprint(filter(str))

    def stest(a_string):
        list = a_string.split('\n')
        ltest(list)
        print '--------------------------------------------------------------------------------'
        Str2Task(a_string)

    from beah.tests.tap import tests
    for test_string in tests:
        stest(test_string)
