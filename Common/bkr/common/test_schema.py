# Beaker
#
# Copyright (C) 2010 Red Hat, Inc.
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

import unittest
import pkg_resources
import lxml.etree

class JobSchemaTest(unittest.TestCase):
    
    job_schema_doc = lxml.etree.parse(pkg_resources.resource_stream(
            'bkr.common', 'schema/beaker-job.rng'))

    def assert_valid(self, xml):
        schema = lxml.etree.RelaxNG(self.job_schema_doc)
        schema.assertValid(lxml.etree.fromstring(xml))

    def assert_not_valid(self, xml, error_message):
        schema = lxml.etree.RelaxNG(self.job_schema_doc)
        self.assert_(not schema.validate(lxml.etree.fromstring(xml)))
        self.assert_(error_message in [str(e.message) for e in schema.error_log])

    def test_minimal_job(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_recipe_elements_in_different_order(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="">
                        <partitions/>
                        <task name="/distribution/install" role="STANDALONE"/>
                        <repos/>
                        <ks_appends/>
                        <hostRequires>
                            <system_type value="Machine"/>
                        </hostRequires>
                        <task name="/distribution/reservesys" role="STANDALONE"/>
                        <packages/>
                        <autopick random="false"/>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <watchdog panic="None"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_duplicate_elements(self):
        self.assert_not_valid('''
            <job>
                <recipeSet>
                    <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="">
                        <autopick random="true"/>
                        <autopick random="false"/>
                        <watchdog panic="None"/>
                        <watchdog panic="always"/>
                        <packages/>
                        <packages/>
                        <ks_appends/>
                        <ks_appends/>
                        <repos/>
                        <repos/>
                        <distroRequires/>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''',
            'Extra element autopick in interleave')

    def test_guestrecipe(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <guestrecipe guestname="asdf" guestargs="--lol">
                            <distroRequires>
                                <distro_name op="=" value="BlueShoeLinux5-5"/>
                            </distroRequires>
                            <task name="/distribution/install" role="STANDALONE"/>
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
