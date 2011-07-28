#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session

class TaskByName(SeleniumTestCase):

    def setUp(self):
        self.my_task = data_setup.create_task()
        self.selenium = self.get_selenium()
        self.selenium.start()
        session.flush()

    def test_task_redirect(self):
        sel = self.selenium
        task_id = self.my_task.id
        task_name = self.my_task.name
        sel.open('tasks%s' % task_name)
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Tasks - %s" % task_name))
        data_from_name = sel.get_text("//body")

        sel.open('tasks/%s' % task_id)
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Tasks - %s" % task_name))
        data_from_id = sel.get_text("//body")

        self.assertEqual(data_from_id, data_from_name)

    def tearDown(self):
        self.selenium.stop()
