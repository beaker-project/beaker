
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

import sys
import os
import logging
import turbogears.config
from turbogears.database import session
import unittest
from nose.plugins.skip import SkipTest
try:
    import krbV
except ImportError:
    krbV = None
from bkr.server.test import data_setup
from bkr.server.test.selenium import XmlRpcTestCase

log = logging.getLogger(__name__)

class XmlRpcLoginTest(XmlRpcTestCase):

    def test_krb_login(self):
        if not krbV:
            raise SkipTest('krbV module not found')
        server_princ_name = turbogears.config.get(
                'identity.krb_auth_principal', None)
        if not server_princ_name: # XXX FIXME dead test
            raise SkipTest('server not configured for krbV')

        # build krb request
        ctx = krbV.default_context()
        try:
            ccache = ctx.default_ccache()
            client_princ = ccache.principal()
        except krbV.Krb5Error:
            raise SkipTest('client ticket not found, run kinit first')
        server_princ = krbV.Principal(name=server_princ_name, context=ctx)
        ac = krbV.AuthContext(context=ctx)
        ac.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        ac.rcache = ctx.default_rcache()
        ac, req = ctx.mk_req(server=sprinc, client=cprinc, auth_context=ac,
                ccache=ccache, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
        encoded_req = base64.encodestring(req)

        # attempt to log in
        server = self.get_server()
        server.auth.login_krbv(encoded_req)

    def test_password_login(self):
        user = data_setup.create_user(password=u'lulz')
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, u'lulz')
        self.assertEquals(server.auth.who_am_i(), user.user_name)

    def test_password_proxy_login(self):
        group = data_setup.create_group(permissions=[u'proxy_auth'])
        user = data_setup.create_user(password=u'lulz')
        proxied_user = data_setup.create_user(password=u'not_used')
        data_setup.add_user_to_group(user, group)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, u'lulz', proxied_user.user_name)
        self.assertEquals(server.auth.who_am_i(), proxied_user.user_name)
