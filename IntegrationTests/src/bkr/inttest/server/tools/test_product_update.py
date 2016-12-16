
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import tempfile
import pkg_resources
import shutil
from bkr.common import __version__
from bkr.server.model import session, Product
from bkr.inttest import DatabaseTestCase, Process
from bkr.inttest.server.tools import run_command, CommandError

class ProductUpdateTest(DatabaseTestCase):

    def setUp(self):
        self.product_docroot = tempfile.mkdtemp(prefix='beaker-fake-product-server')
        self.addCleanup(shutil.rmtree, self.product_docroot, ignore_errors=True)
        self.product_server = Process('http_server.py', args=[sys.executable,
                pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                '--base', self.product_docroot], listen_port=19998)
        self.product_server.start()
        self.addCleanup(self.product_server.stop)

    def test_version(self):
        out = run_command('product_update.py', 'product-update', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_errors_out_if_file_not_specified(self):
        try:
            run_command('product_update.py', 'product-update', [])
            self.fail('should raise')
        except CommandError as e:
            self.assertIn(
                    'Specify product data to load using --product-file or --product-url',
                    e.stderr_output)

    def test_loads_cpe_identifiers_from_xml_file(self):
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write("""\
            <products>
                <product>
                    <cpe>cpe:/a:redhat:ceph_storage:2</cpe>
                </product>
                <product>
                    <cpe>cpe:/o:redhat:enterprise_linux:4:update8</cpe>
                </product>
            </products>
            """)
        xml_file.flush()
        run_command('product_update.py', 'product-update', ['-f', xml_file.name])
        with session.begin():
            # check that the products have been inserted into the db
            Product.by_name(u'cpe:/a:redhat:ceph_storage:2')
            Product.by_name(u'cpe:/o:redhat:enterprise_linux:4:update8')

    def test_ignores_duplicate_cpe_identifiers(self):
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write("""\
            <products>
                <product>
                    <cpe>cpe:/a:redhat:ceph_storage:69</cpe>
                </product>
                <product>
                    <cpe>cpe:/a:redhat:ceph_storage:69</cpe>
                </product>
            </products>
            """)
        xml_file.flush()
        run_command('product_update.py', 'product-update', ['-f', xml_file.name])
        with session.begin():
            Product.by_name(u'cpe:/a:redhat:ceph_storage:69')

    def test_ignores_empty_cpe_identifiers(self):
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write("""\
            <products>
                <product>
                    <cpe></cpe>
                </product>
            </products>
            """)
        xml_file.flush()
        run_command('product_update.py', 'product-update', ['-f', xml_file.name])
        with session.begin():
            self.assertEquals(Product.query.filter(Product.name == u'').count(), 0)
            self.assertEquals(Product.query.filter(Product.name == u'None').count(), 0)

    def test_loads_cpe_identifiers_from_xml_url(self):
        with open(os.path.join(self.product_docroot, 'product.xml'), 'wb') as xml_file:
            xml_file.write("""\
                <products>
                    <product>
                        <cpe>cpe:/o:redhat:enterprise_linux:7.0</cpe>
                    </product>
                    <product>
                        <cpe>cpe:/o:redhat:enterprise_linux:7:2</cpe>
                    </product>
                </products>
                """)
        run_command('product_update.py', 'product-update',
                ['--product-url', 'http://localhost:19998/product.xml'])
        with session.begin():
            Product.by_name(u'cpe:/o:redhat:enterprise_linux:7.0')
            Product.by_name(u'cpe:/o:redhat:enterprise_linux:7:2')

    def test_loads_cpe_identifiers_from_json_url(self):
        with open(os.path.join(self.product_docroot, 'product.json'), 'wb') as json_file:
            json_file.write("""\
                [
                    {"id": 1, "cpe": "cpe:/a:redhat:jboss_data_virtualization:6.2.0"},
                    {"id": 2, "cpe": "cpe:/a:redhat:jboss_operations_network:3.2.0"},
                    {"id": 3, "cpe": ""},
                    {"id": 4}
                ]
                """)
        run_command('product_update.py', 'product-update',
                ['--product-url', 'http://localhost:19998/product.json'])
        with session.begin():
            Product.by_name(u'cpe:/a:redhat:jboss_data_virtualization:6.2.0')
            Product.by_name(u'cpe:/a:redhat:jboss_operations_network:3.2.0')
