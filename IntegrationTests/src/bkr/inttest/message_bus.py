
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from bkr.server.message_bus import ServerBeakerBus


class TestServerBeakerBus(ServerBeakerBus):

    @classmethod
    def do_krb_auth(cls):
        from bkr.common.krb_auth import AuthManager
        cache_file_name = os.environ.get('BEAKER_TEST_KRB_CACHE')
        cls._auth_mgr = AuthManager(cache_file = cache_file_name)
