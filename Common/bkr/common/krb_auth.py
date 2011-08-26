import krbV

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

    def reinit(self):
        if not self.keytab or not self.primary_principal:
            raise ValueError('Need a keytab and a primary pricipal to reinit krb cache')
        # Apparently, wiping the ccache is required
        self.ccache.init(self.primary_principal)
        self.ccache.init_creds_keytab(keytab=self.keytab, principal=self.primary_principal)
