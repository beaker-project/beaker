
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import pkg_resources
import lxml.etree

class SchemaTestBase(unittest.TestCase):

    schema_doc = None # filled by setUpClass

    def assert_valid(self, xml):
        schema = lxml.etree.RelaxNG(self.schema_doc)
        schema.assertValid(lxml.etree.fromstring(xml))

    def assert_not_valid(self, xml, error_message):
        schema = lxml.etree.RelaxNG(self.schema_doc)
        self.assert_(not schema.validate(lxml.etree.fromstring(xml)))
        messages = [str(e.message) for e in schema.error_log]
        self.assert_(error_message in messages, messages)

class TaskSchemaTest(SchemaTestBase):

    @classmethod
    def setUpClass(cls):
        cls.schema_doc = lxml.etree.parse(pkg_resources.resource_stream(
        'bkr.common', 'schema/beaker-task.rng'))

    def test_minimal_task(self):
        self.assert_valid('''
            <task name='/distribution/example' 
                  creation_date='2010-05-0517:39:14'
                  destructive='0'
                  nda='0'
                  version='1.0'>
              <description>Testing description</description>
              <owner>Me!</owner>
              <rpms>
                <rpm url='http://example.com/task.rpm' name='task.rpm' />
              </rpms>
              <path>/mnt/test/distribution/example</path>
             </task>
            ''')

    def test_maximal_task(self):
        self.assert_valid('''
            <task name='/distribution/example' 
                  creation_date='2010-05-05 17:39:14'
                  destructive='0'
                  nda='0'
                  version='1.0'>
              <description>Testing description</description>
              <owner>Me!</owner>
              <rpms>
                <rpm url='http://example.com/task.rpm' name='task.rpm' />
              </rpms>
              <path>/mnt/test/distribution/example</path>
              <excludedDistroFamilies>
                <distroFamily>Major1</distroFamily>
                <distroFamily>Major2</distroFamily>
              </excludedDistroFamilies>
              <excludedArches>
                <arch>i386</arch>
                <arch>s390x</arch>
              </excludedArches>
              <requires>
                <package>selenium-python</package>
                <package>some-valid-pacakge</package>
              </requires>
              <runFor>
                <package>beaker-server</package>
                <package>beah</package>
              </runFor>
              <bugzillas>
                <bugzilla>893445</bugzilla>
                <bugzilla>3424623</bugzilla>
              </bugzillas>
            </task>
           ''')


class JobSchemaTest(SchemaTestBase):

    @classmethod
    def setUpClass(cls):
        cls.schema_doc = lxml.etree.parse(pkg_resources.resource_stream(
            'bkr.common', 'schema/beaker-job.rng'))

    def test_minimal_job(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_minimal_job_with_system_inventory_status(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires>
                            <system>
                              <last_inventoried op="=" value=""/>
                            </system>
                        </hostRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_minimal_job_with_system_inventory_date(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires>
                            <system>
                              <last_inventoried op="=" value="2013-10-10" />
                            </system>
                        </hostRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_minimal_job_with_invalid_system_inventory_date(self):
        self.assert_not_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires>
                            <system>
                              <last_inventoried op="=" value="2013-10-10 10:10:10" />
                            </system>
                        </hostRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
        ''', 'Element hostRequires has extra content: system')

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
                            <hostRequires/>
                            <task name="/distribution/install" role="STANDALONE"/>
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_optional_guestname(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <guestrecipe guestargs="--lol">
                            <distroRequires>
                                <distro_name op="=" value="BlueShoeLinux5-5"/>
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/install" role="STANDALONE"/>
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_hostRequires_not_optional(self):
        self.assert_not_valid('''
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
            ''',
            'Invalid sequence in interleave')

    #https://bugzilla.redhat.com/show_bug.cgi?id=851354
    def test_force_system(self):

        # force and hostRequires are mutually exclusive
        self.assert_not_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                        <hostRequires force="test1.system.fqdn">
                        <system> <name op="=" value="test1.system.fqdn"/> </system>
                        </hostRequires>

                    </recipe>
                </recipeSet>
            </job>
            ''', 'Invalid attribute force for element hostRequires')

        # <hostRequires><system>..</system></hostRequires>
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                        <hostRequires>
                        <system> <name op="=" value="test1.system.fqdn"/> </system>
                        </hostRequires>

                    </recipe>
                </recipeSet>
            </job>''')

        # test <hostRequires force='..' </hostRequires>
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <task name="/distribution/install" role="STANDALONE"/>
                        <hostRequires force='test1.system.fqdn'/>
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_device(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires/>
                        <hostRequires>
                            <device op="="
                                    type="network" bus="pci" driver="e1000e"
                                    vendor_id="8086" device_id="10d3"
                                    subsys_vendor_id="8086" subsys_device_id="a01f"
                                    />
                        </hostRequires>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_device_driver(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires/>
                        <hostRequires>
                            <device op="=" driver="e1000e" />
                        </hostRequires>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_optional_op(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <and>
                                <family op="=" value="RedHatEnterpriseLinux6"/>
                                <variant value="Server"/>
                                <name op="=" value="RedHatEnterpriseLinux-6.3"/>
                                <arch value="x86_64"/>
                            </and>
                        </distroRequires>
                        <hostRequires>
                            <device op="=" driver="e1000e" />
                            <memory value="2048"/>
                            <cpu>
                                <and>
                                    <cores op=">" value="1"/>
                                    <flag value="sse2"/>
                                </and>
                            </cpu>
                        </hostRequires>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_disk_units(self):
        # These are all valid units for disk sizes:
        units = ['bytes', 'B', 'kB', 'KB', 'KiB', 'MB', 'MiB',
                 'GB', 'GiB', 'TB', 'TiB']
        for unit in units:
            self.assert_valid('''
                <job>
                    <recipeSet>
                        <recipe>
                            <distroRequires/>
                            <hostRequires>
                                <disk>
                                    <size op="&gt;=" value="10" units="%s" />
                                </disk>
                            </hostRequires>
                            <task name="/distribution/install" />
                        </recipe>
                    </recipeSet>
                </job>
                ''' % unit)
        # gigaquads are definitely not a valid unit for disk sizes
        self.assert_not_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires/>
                        <hostRequires>
                            <disk>
                                <size op="&gt;=" value="10" units="gigaquads" />
                            </disk>
                        </hostRequires>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''',
            'Element hostRequires has extra content: disk')

    def test_job_with_reservesys(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <reservesys/>
                        <distroRequires/>
                        <hostRequires>
                            <device op="=" driver="e1000e" />
                        </hostRequires>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')

    def test_job_with_reservesys_duration(self):
        self.assert_valid('''
            <job>
                <recipeSet>
                    <recipe>
                        <reservesys duration="9999"/>
                        <distroRequires/>
                        <hostRequires>
                            <device op="=" driver="e1000e" />
                        </hostRequires>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')

