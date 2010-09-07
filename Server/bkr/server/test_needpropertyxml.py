# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
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

import sys
import unittest
import xmltramp
from bkr.server.needpropertyxml import ElementWrapper

def evaluate_filter(xml):
    clauses = []
    for child in ElementWrapper(xmltramp.parse(xml)):
        if callable(getattr(child, 'filter', None)):
            (join, query) = child.filter()
            clauses.extend(join)
            if query: clauses.append(query)
    return clauses

class TestElementWrapperFilters(unittest.TestCase):

    def test_cpu_count(self):
        clauses = evaluate_filter("""
            <hostRequires>
                <and>
                    <cpu_count op="=" value="4" />
                </and>
            </hostRequires>
            """)
        self.assertEquals(2, len(clauses))
        self.assertEquals('system.id = cpu.system_id', str(clauses[0]))
        self.assertEquals('cpu.processors = %s', str(clauses[1]))
        self.assertEquals(4, clauses[1].compile().params['processors_1'])

    def test_numa_node_count(self):
        clauses = evaluate_filter("""
            <hostRequires>
                <and>
                    <numa_node_count op=">=" value="32" />
                </and>
            </hostRequires>
            """)
        self.assertEquals(2, len(clauses))
        self.assertEquals('system.id = numa.system_id', str(clauses[0]))
        self.assertEquals('numa.nodes >= %s', str(clauses[1]))
        self.assertEquals(32, clauses[1].compile().params['nodes_1'])
