
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import krbV
import socket
import base64

class AuthManager:
    def __init__(self, cache_file=None, primary_principal=None, keytab=None):
        self.context = krbV.default_context()
        self.primary_principal = primary_principal
        self.keytab = keytab
        if self.keytab and not isinstance(self.keytab, krbV.Keytab):
            self.keytab = krbV.Keytab(name=self.keytab, context=self.context)
        if not self.primary_principal and not cache_file:
            raise ValueError('No cache file nor primary principal')
        if self.primary_principal and not isinstance(self.primary_principal, krbV.Principal):
            self.primary_principal = krbV.Principal(name=self.primary_principal, context=self.context)
        if self.primary_principal:
            if cache_file:
                self.ccache = krbV.CCache(name="FILE:"+cache_file, context=self.context,
                                          primary_principal=self.primary_principal)
            else:
                self.ccache = self.context.default_ccache(primary_principal=self.primary_principal)
        else:
            if cache_file:
                self.ccache = krbV.CCache(name="FILE:"+cache_file, context=self.context)
            else:
                self.ccache = self.context.default_ccache()
            self.primary_principal = self.ccache.principal()
        if self.keytab: self.reinit()

    def _create_request(self, sprinc, ac):
        _, req = self.context.mk_req(server=sprinc, client=self.primary_principal,
            auth_context=ac, ccache=self.ccache, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
        return req

    def get_encoded_request(self, full_principal):
        sprinc = krbV.Principal(name=full_principal, context=self.context)
        ac = krbV.AuthContext(context=self.context)
        ac.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        ac.rcache = self.context.default_rcache()

        # create and encode the authentication request
        try:
            req = self._create_request(sprinc, ac)
        except krbV.Krb5Error, e:
            if 'Ticket expired' in str(e):
                self.reinit()
                req = self._create_request(sprinc, ac)
            else:
                raise
        return base64.encodestring(req)

    def reinit(self):
        if not self.keytab or not self.primary_principal:
            raise ValueError('Need a keytab and a primary pricipal to reinit krb cache')
        # Apparently, wiping the ccache is required
        self.ccache.init(self.primary_principal)
        self.ccache.init_creds_keytab(keytab=self.keytab, principal=self.primary_principal)
