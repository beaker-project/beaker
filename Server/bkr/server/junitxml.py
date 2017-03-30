
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Converts Beaker job results to an XML format compatible with the Ant JUnit 
test runner, which Jenkins can understand.

Many people (including nose) refer to this as the "XUnit" XML format, probably 
because "xUnit" is a short-hand for referring to the group of language-specific 
unit testing tools modelled after SUnit (JUnit, NUnit, etc). But that's 
confusing because there is also at least three other projects named XUnit which 
have their own *different* XML formats.
"""

import urlparse
import lxml.etree
from lxml.builder import E
from bkr.common.helpers import total_seconds
from bkr.server.util import absolute_url
from bkr.server.model import TaskStatus, TaskResult

def _systemout_for_task(task):
    return '\n'.join(absolute_url(log.href) for log in task.logs)

def _systemout_for_result(result):
    return '\n'.join(absolute_url(log.href) for log in result.logs)

def _testcases_for_task(task):
    if not task.is_finished():
        return
    testcase = E.testcase(
            classname=task.name,
            name='(main)')
    if task.status == TaskStatus.cancelled:
        testcase.append(E.skipped(type=u'skipped'))
    elif task.status == TaskStatus.aborted:
        testcase.append(E.error(type=u'error'))
    elif task.result in (TaskResult.warn, TaskResult.fail):
        testcase.append(E.failure(type=u'failure'))
    testcase.append(E(u'system-out', _systemout_for_task(task)))
    yield testcase
    for result in task.results:
        testcase = E.testcase(
                classname=task.name,
                name=result.short_path.lstrip('/') or '(none)')
        if result.duration:
            testcase.set('time', '%.0f' % total_seconds(result.duration))
        # For Cancelled and Aborted, the final Warn is the reason message
        if (task.status == TaskStatus.cancelled and
                result == task.results[-1] and
                result.result == TaskResult.warn):
            testcase.append(E.skipped(message=result.log or u'', type=u'skipped'))
        elif (task.status == TaskStatus.aborted and
                result == task.results[-1] and
                result.result == TaskResult.warn):
            testcase.append(E.error(message=result.log or u'', type=u'error'))
        elif result.result in (TaskResult.warn, TaskResult.fail):
            testcase.append(E.failure(message=result.log or u'', type=u'failure'))
        testcase.append(E(u'system-out', _systemout_for_result(result)))
        yield testcase

def _testsuite_for_recipe(recipe):
    testsuite = E.testsuite(id=recipe.t_id, name=recipe.whiteboard or u'')
    if recipe.resource and recipe.resource.fqdn:
        testsuite.set('hostname', recipe.resource.fqdn)
    for task in recipe.tasks:
        testsuite.extend(_testcases_for_task(task))
    testsuite.set('tests', str(len(testsuite.findall('testcase'))))
    testsuite.set('skipped', str(len(testsuite.findall('testcase/skipped'))))
    testsuite.set('failures', str(len(testsuite.findall('testcase/failure'))))
    testsuite.set('errors', str(len(testsuite.findall('testcase/error'))))
    return testsuite

def job_to_junit_xml(job):
    testsuites = E.testsuites()
    for recipe in job.all_recipes:
        testsuites.append(_testsuite_for_recipe(recipe))
    return lxml.etree.tostring(testsuites, encoding='utf8',
            xml_declaration=True, pretty_print=True)

def recipe_to_junit_xml(recipe):
    testsuites = E.testsuites()
    testsuites.append(_testsuite_for_recipe(recipe))
    return lxml.etree.tostring(testsuites, encoding='utf8',
            xml_declaration=True, pretty_print=True)
