LDAP TLS certificate checking is no longer disabled
===================================================

In previous versions Beaker disabled TLS certificate checking for LDAP 
connections. The certificate checking behaviour is now inherited from the 
system-wide OpenLDAP configuration. By default OpenLDAP requires a trusted 
certificate on all connections.

If your Beaker site is using LDAP integration you should ensure that your LDAP 
directory's CA is trusted by adding it to the system-wide OpenSSL trust store, 
or by setting the ``TLS_CACERT`` option in :file:`/etc/openldap/ldap.conf` 
appropriately.

If necessary, TLS certificate checking can be disabled system-wide in OpenLDAP 
by setting the ``TLS_REQCERT`` option in :file:`/etc/openldap/ldap.conf`. See 
:manpage:`ldap.conf(5)` for details.
