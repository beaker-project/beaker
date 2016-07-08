
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import xmlrpclib
from bkr.inttest.server.selenium import XmlRpcTestCase

class NonexistentXmlRpcMethodTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1029287
    def test_error_message_for_nonexistent_methods(self):
        try:
            self.server.flimflam()
            self.fail('should raise')
        except xmlrpclib.Fault as e:
            self.assertEquals(e.faultString,
                    'XML-RPC method flimflam not implemented by this server')
