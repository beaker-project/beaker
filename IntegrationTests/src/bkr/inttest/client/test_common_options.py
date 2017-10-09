
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import pkg_resources
import re
from bkr.common import __version__
from bkr.inttest import get_server_base, Process
from bkr.inttest.client import run_client, create_client_config, ClientTestCase, \
        ClientError

class CommonOptionsTest(ClientTestCase):

    def test_hub(self):
        # wrong hub in config, correct one passed on the command line
        config = create_client_config(hub_url='http://notexist.invalid')
        run_client(['bkr', '--hub', get_server_base().rstrip('/'),
                'labcontroller-list'], config=config)

    # https://bugzilla.redhat.com/show_bug.cgi?id=862146
    def test_version(self):
        out = run_client(['bkr', '--version'])
        self.assert_(re.match(r'\d+\.[.a-zA-Z0-9]+$', out), out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1345735
    def test_insecure(self):
        # The hub will be http:// so --insecure will have no effect, but at 
        # least this tests that the option exists...
        run_client(['bkr', 'whoami', '--insecure'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1029287
    def test_on_error_warns_if_server_version_does_not_match(self):
        fake_server = Process('http_server.py', args=[sys.executable,
                    pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                    '--base', '/notexist',
                    '--add-response-header', 'X-Beaker-Version:999.3'],
                listen_port=19998)
        fake_server.start()
        self.addCleanup(fake_server.stop)

        # use AUTH_METHOD=none because we can't authenticate to the fake server
        config = create_client_config(hub_url='http://localhost:19998',
                auth_method=u'none')
        try:
            run_client(['bkr', 'system-status', 'asdf.example.com'], config=config)
            self.fail('should raise')
        except ClientError as e:
            error_lines = e.stderr_output.splitlines()
            self.assertEquals(error_lines[0],
                    'WARNING: client version is %s but server version is 999.3'
                    % __version__)
            self.assertIn('HTTP error: 404 Client Error: Not Found',
                    error_lines[1])
