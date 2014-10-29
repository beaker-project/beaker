
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from decimal import Decimal
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.server.model import Cpu, Arch
from rdflib.term import URIRef, Literal
from rdflib.graph import Graph

from bkr.server.rdf import INV, describe_system

class SystemRDFTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

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
        system = data_setup.create_system(fqdn=u'cpu-speed-decimal.test-rdf.invalid')
        system.cpu = Cpu(speed=2666.67)
        session.flush()
        graph = self.describe(system)
        speed_literal = graph.value(
                subject=URIRef(get_server_base() + 'view/cpu-speed-decimal.test-rdf.invalid#system'),
                predicate=INV.cpuSpeed, any=False)
        self.assertEqual(speed_literal.datatype,
                URIRef('http://www.w3.org/2001/XMLSchema#decimal'))
