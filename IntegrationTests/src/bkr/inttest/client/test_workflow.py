# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import re
from bkr.client import BeakerWorkflow, BeakerRecipe


class WorkflowTest(unittest.TestCase):

    def setUp(self):
        self.command = BeakerWorkflow(None)

    def test_processPartitions(self):
        recipe = BeakerRecipe()
        recipe.addPartition(name='/mnt/block1', type='part', fs='ext3', size=1024)
        xml = recipe.toxml()
        self.assertEquals(xml, '<recipe whiteboard="">'
                               '<distroRequires>'
                               '<and/>'
                               '</distroRequires>'
                               '<hostRequires/>'
                               '<repos/>'
                               '<partitions>'
                               '<partition fs="ext3" name="/mnt/block1" size="1024" type="part"/>'
                               '</partitions>'
                               '</recipe>')

    def test_processTemplate_minimal_recipe(self):
        recipeTemplate = BeakerRecipe()
        recipe = self.command.processTemplate(recipeTemplate,
                                              requestedTasks=[{'name': '/example', 'arches': []}],
                                              family='RedHatEnterpriseLinux6')
        xml = recipe.toxml()
        self.assertEquals(xml, '<recipe whiteboard="">'
                               '<distroRequires>'
                               '<and/>'
                               '</distroRequires>'
                               '<hostRequires/>'
                               '<repos/>'
                               '<partitions/>'
                               '<task name="/distribution/check-install" role="STANDALONE">'
                               '<params/>'
                               '</task>'
                               '<task name="/example" role="STANDALONE">'
                               '<params/>'
                               '</task>'
                               '</recipe>')

    # https://bugzilla.redhat.com/show_bug.cgi?id=723789
    def test_processTemplate_does_not_produce_duplicates(self):
        recipeTemplate = BeakerRecipe()

        # with passed-in distroRequires XML
        recipe = self.command.processTemplate(recipeTemplate,
                                              requestedTasks=[{'name': '/example', 'arches': []}],
                                              distroRequires='<distroRequires><distro_name op="=" value="RHEL99-U1" /></distroRequires>',
                                              family='RedHatEnterpriseLinux99')
        xml = recipe.toxml(prettyxml=True)
        self.assertEquals(len(re.findall('<distro_name', xml)), 1, xml)

        # with passed-in hostRequires XML
        recipe = self.command.processTemplate(recipeTemplate,
                                              requestedTasks=[{'name': '/example', 'arches': []}],
                                              hostRequires='<hostRequires><hostname op="=" value="lolcat.example.invalid" /></hostRequires>',
                                              family='RedHatEnterpriseLinux99')
        xml = recipe.toxml(prettyxml=True)
        self.assertEquals(len(re.findall('<hostname', xml)), 1, xml)

        # with distroRequires and hostRequires in the template
        recipeTemplate.addBaseRequires(distro='RHEL99-U1', machine='lolcat.example.invalid')
        recipe = self.command.processTemplate(recipeTemplate,
                                              requestedTasks=[{'name': '/example', 'arches': []}],
                                              family='RedHatEnterpriseLinux99')
        xml = recipe.toxml(prettyxml=True)
        self.assertEquals(len(re.findall('<distro_name', xml)), 1, xml)
        self.assertEquals(len(re.findall('<hostname', xml)), 1, xml)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1200427
    def test_distro_wildcard(self):
        recipeTemplate = BeakerRecipe()
        recipeTemplate.addBaseRequires(distro='RHEL-7.1%', family='RedHatEnterpriseLinux7')
        recipe = self.command.processTemplate(recipeTemplate,
                                              requestedTasks=[{'name': '/example', 'arches': []}],
                                              family='RedHatEnterpriseLinux7')
        xml = recipe.toxml(prettyxml=True)
        self.assertIn('<distro_name op="like" value="RHEL-7.1%"/>', xml)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1010355
    def test_hostrequire_accepts_like_operator(self):
        recipeTemplate = BeakerRecipe()
        recipeTemplate.addBaseRequires(hostrequire=['hostname like %.khw.%'])
        recipe = self.command.processTemplate(recipeTemplate,
                                              requestedTasks=[{'name': '/example', 'arches': []}],
                                              family='RedHatEnterpriseLinux7')
        xml = recipe.toxml()
        self.assertIn('<hostname op="like" value="%.khw.%"/>', xml)
