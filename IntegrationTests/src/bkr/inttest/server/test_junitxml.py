# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import unittest
from bkr.server.junitxml import job_to_junit_xml
from bkr.server.model import session, TaskResult, TaskStatus
from bkr.server.tests import data_setup
from bkr.inttest import get_server_base


class JUnitXMLUnitTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        session.begin()
        self.addCleanup(session.rollback)

    def test_passing_result(self):
        job = data_setup.create_completed_job(recipe_whiteboard=u'happy',
                                              fqdn=u'happysystem.testdata', server_log=True,
                                              result=TaskResult.pass_,
                                              task_status=TaskStatus.completed)
        recipe = job.recipesets[0].recipes[0]
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 10)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="happy" id="R:{recipe_id}" hostname="happysystem.testdata" tests="2" skipped="0" failures="0" errors="0">
    <testcase classname="/distribution/reservesys" name="(main)">
      <system-out>{server}recipes/{recipe_id}/tasks/{task_id}/logs/tasks/dummy.txt</system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="(none)" time="10">
      <system-out>{server}recipes/{recipe_id}/tasks/{task_id}/results/{result_id}/logs/result.txt</system-out>
    </testcase>
  </testsuite>
</testsuites>
""".format(server=get_server_base(), recipe_id=recipe.id, task_id=recipe.tasks[0].id,
           result_id=recipe.tasks[0].results[0].id)
        self.assertMultiLineEqual(expected, out)

    def test_failing_result(self):
        job = data_setup.create_completed_job(recipe_whiteboard=u'failing result',
                                              fqdn=u'happysystem.testdata', server_log=True,
                                              result=TaskResult.fail,
                                              task_status=TaskStatus.completed)
        recipe = job.recipesets[0].recipes[0]
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 10)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="failing result" id="R:{recipe_id}" hostname="happysystem.testdata" tests="2" skipped="0" failures="2" errors="0">
    <testcase classname="/distribution/reservesys" name="(main)">
      <failure type="failure"/>
      <system-out>{server}recipes/{recipe_id}/tasks/{task_id}/logs/tasks/dummy.txt</system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="(none)" time="10">
      <failure message="(Fail)" type="failure"/>
      <system-out>{server}recipes/{recipe_id}/tasks/{task_id}/results/{result_id}/logs/result.txt</system-out>
    </testcase>
  </testsuite>
</testsuites>
""".format(server=get_server_base(), recipe_id=recipe.id, task_id=recipe.tasks[0].id,
           result_id=recipe.tasks[0].results[0].id)
        self.assertMultiLineEqual(expected, out)

    def test_aborted(self):
        job = data_setup.create_running_job(recipe_whiteboard=u'ewd',
                                            fqdn=u'sadsystem.testdata')
        job.abort(msg=u'External Watchdog Expired')
        job.update_status()
        recipe = job.recipesets[0].recipes[0]
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 10)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="ewd" id="R:%s" hostname="sadsystem.testdata" tests="2" skipped="0" failures="0" errors="2">
    <testcase classname="/distribution/reservesys" name="(main)">
      <error type="error"/>
      <system-out></system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="(none)" time="10">
      <error message="External Watchdog Expired" type="error"/>
      <system-out></system-out>
    </testcase>
  </testsuite>
</testsuites>
""" % recipe.id
        self.assertMultiLineEqual(expected, out)

    def test_cancelled(self):
        job = data_setup.create_running_job(recipe_whiteboard=u'cancelled',
                                            fqdn=u'sadsystem.testdata')
        job.cancel(msg=u'I cancelled it')
        job.update_status()
        recipe = job.recipesets[0].recipes[0]
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 10)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="cancelled" id="R:%s" hostname="sadsystem.testdata" tests="2" skipped="2" failures="0" errors="0">
    <testcase classname="/distribution/reservesys" name="(main)">
      <skipped type="skipped"/>
      <system-out></system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="(none)" time="10">
      <skipped message="I cancelled it" type="skipped"/>
      <system-out></system-out>
    </testcase>
  </testsuite>
</testsuites>
""" % recipe.id
        self.assertMultiLineEqual(expected, out)

    def test_new_job(self):
        # We can't give anything much sensible if the job is not finished yet,
        # but we *don't* want to just totally explode and return a 500 error.
        job = data_setup.create_job(recipe_whiteboard=u'new job')
        self.assertEqual(job.status, TaskStatus.new)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="new job" id="R:%s" tests="0" skipped="0" failures="0" errors="0"/>
</testsuites>
""" % job.recipesets[0].recipes[0].id
        self.assertMultiLineEqual(expected, out)

    def test_incomplete_job(self):
        # First task is completed so it shows up in the JUnit XML, second task
        # is still running and has no results so it doesn't appear.
        job = data_setup.create_running_job(recipe_whiteboard=u'running job',
                                            fqdn=u'busysystem.testdata',
                                            task_list=[
                                                data_setup.create_task(u'/test_junitxml/completed'),
                                                data_setup.create_task(u'/test_junitxml/running')])
        recipe = job.recipesets[0].recipes[0]
        data_setup.mark_recipe_tasks_finished(recipe,
                                              only=True, num_tasks=1, result=TaskResult.pass_,
                                              server_log=True)
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 10)
        self.assertEqual(job.status, TaskStatus.running)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="running job" id="R:{recipe_id}" hostname="busysystem.testdata" tests="2" skipped="0" failures="0" errors="0">
    <testcase classname="/test_junitxml/completed" name="(main)">
      <system-out>{server}recipes/{recipe_id}/tasks/{task_id}/logs/tasks/dummy.txt</system-out>
    </testcase>
    <testcase classname="/test_junitxml/completed" name="(none)" time="10">
      <system-out>{server}recipes/{recipe_id}/tasks/{task_id}/results/{result_id}/logs/result.txt</system-out>
    </testcase>
  </testsuite>
</testsuites>
""".format(server=get_server_base(), recipe_id=recipe.id, task_id=recipe.tasks[0].id,
           result_id=recipe.tasks[0].results[0].id)
        self.assertMultiLineEqual(expected, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1291107
    def test_duration(self):
        job = data_setup.create_running_job(recipe_whiteboard=u'duration',
                                            fqdn=u'happysystem.testdata')
        recipe = job.recipesets[0].recipes[0]
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].pass_(path=u'first', score=0, summary=u'(Pass)')
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 10)
        recipe.tasks[0].pass_(path=u'second', score=0, summary=u'(Pass)')
        recipe.tasks[0].results[1].start_time = datetime.datetime(2015, 12, 14, 0, 0, 13)
        recipe.tasks[0]._change_status(TaskStatus.completed)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="duration" id="R:%s" hostname="happysystem.testdata" tests="3" skipped="0" failures="0" errors="0">
    <testcase classname="/distribution/reservesys" name="(main)">
      <system-out></system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="first" time="10">
      <system-out></system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="second" time="3">
      <system-out></system-out>
    </testcase>
  </testsuite>
</testsuites>
""" % recipe.id
        self.assertMultiLineEqual(expected, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1291112
    def test_result_names(self):
        job = data_setup.create_running_job(recipe_whiteboard=u'duration',
                                            fqdn=u'happysystem.testdata',
                                            task_name=u'/junitxml/names')
        recipe = job.recipesets[0].recipes[0]
        recipe.tasks[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 0)
        recipe.tasks[0].pass_(path=u'/start', score=0, summary=u'(Pass)')
        recipe.tasks[0].results[0].start_time = datetime.datetime(2015, 12, 14, 0, 0, 1)
        recipe.tasks[0].pass_(path=u'/junitxml/names/with-suffix', score=0, summary=u'(Pass)')
        recipe.tasks[0].results[1].start_time = datetime.datetime(2015, 12, 14, 0, 0, 2)
        recipe.tasks[0].pass_(path=u'/junitxml/names', score=0, summary=u'(Pass)')
        recipe.tasks[0].results[2].start_time = datetime.datetime(2015, 12, 14, 0, 0, 3)
        recipe.tasks[0].pass_(path=u'beakerlib-style', score=0, summary=u'(Pass)')
        recipe.tasks[0].results[3].start_time = datetime.datetime(2015, 12, 14, 0, 0, 4)
        recipe.tasks[0].finish_time = datetime.datetime(2015, 12, 14, 0, 0, 5)
        recipe.tasks[0]._change_status(TaskStatus.completed)
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="duration" id="R:%s" hostname="happysystem.testdata" tests="5" skipped="0" failures="0" errors="0">
    <testcase classname="/junitxml/names" name="(main)">
      <system-out></system-out>
    </testcase>
    <testcase classname="/junitxml/names" name="start" time="1">
      <system-out></system-out>
    </testcase>
    <testcase classname="/junitxml/names" name="with-suffix" time="1">
      <system-out></system-out>
    </testcase>
    <testcase classname="/junitxml/names" name="(none)" time="1">
      <system-out></system-out>
    </testcase>
    <testcase classname="/junitxml/names" name="beakerlib-style" time="1">
      <system-out></system-out>
    </testcase>
  </testsuite>
</testsuites>
""" % recipe.id
        self.assertMultiLineEqual(expected, out)

    # htps://bugzilla.redhat.com/show_bug.cgi?id=1316045
    def test_cancelled_recipe_has_tasks_never_started(self):
        job = data_setup.create_job(recipe_whiteboard=u'cancelled',
                                    task_name=u'/test_junixml/cancelled')
        job.cancel(msg=u'I cancelled it')
        recipe = job.recipesets[0].recipes[0]
        job.update_status()
        out = job_to_junit_xml(job)
        expected = """\
<?xml version=\'1.0\' encoding=\'utf8\'?>
<testsuites>
  <testsuite name="cancelled" id="R:%s" tests="2" skipped="2" failures="0" errors="0">
    <testcase classname="/test_junixml/cancelled" name="(main)">
      <skipped type="skipped"/>
      <system-out></system-out>
    </testcase>
    <testcase classname="/test_junixml/cancelled" name="(none)">
      <skipped message="I cancelled it" type="skipped"/>
      <system-out></system-out>
    </testcase>
  </testsuite>
</testsuites>
""" % recipe.id
        self.assertMultiLineEqual(expected, out)

    # htps://bugzilla.redhat.com/show_bug.cgi?id=1316045
    def test_aborted_recipe_has_tasks_never_started(self):
        job = data_setup.create_job(recipe_whiteboard=u'aborted')
        job.abort(msg=u'External Watchdog Expired')
        job.update_status()
        recipe = job.recipesets[0].recipes[0]
        out = job_to_junit_xml(job)
        expected = """\
<?xml version='1.0' encoding='utf8'?>
<testsuites>
  <testsuite name="aborted" id="R:%s" tests="2" skipped="0" failures="0" errors="2">
    <testcase classname="/distribution/reservesys" name="(main)">
      <error type="error"/>
      <system-out></system-out>
    </testcase>
    <testcase classname="/distribution/reservesys" name="(none)">
      <error message="External Watchdog Expired" type="error"/>
      <system-out></system-out>
    </testcase>
  </testsuite>
</testsuites>
""" % recipe.id
        self.assertMultiLineEqual(expected, out)
