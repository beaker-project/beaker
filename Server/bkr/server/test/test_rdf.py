
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
from decimal import Decimal
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.model import Cpu, Arch
from rdflib.term import URIRef, Literal
from rdflib.graph import Graph

from bkr.server.rdf import INV, describe_system

class SystemRDFTest(unittest.TestCase):

    def describe(self, system):
        g = Graph()
        describe_system(system, g)
        return g

    def test_system_without_lab_controller(self):
        system = data_setup.create_system()
        system.lab_controller = None
        session.flush()
        graph = self.describe(system)
        self.assert_((None, INV.controlledBy, None) not in graph)

    def test_cpu_speed_is_decimal(self):
        system = data_setup.create_system(fqdn=u'cpu_speed_decimal.test_rdf')
        system.cpu = Cpu(speed=2666.67)
        session.flush()
        graph = self.describe(system)
        speed_literal = graph.value(
                subject=URIRef('http://localhost:9090/view/cpu_speed_decimal.test_rdf#system'),
                predicate=INV.cpuSpeed, any=False)
        self.assertEqual(speed_literal.datatype,
                URIRef('http://www.w3.org/2001/XMLSchema#decimal'))
