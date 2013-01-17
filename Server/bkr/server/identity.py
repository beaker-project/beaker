from turbogears.identity.saprovider import SqlAlchemyIdentityProvider, SqlAlchemyIdentity
from turbogears.identity import set_login_attempted
from turbogears.config import get
from turbogears.database import session
from turbogears.util import load_class
import ldap
import logging
import cherrypy
import os
log = logging.getLogger("bkr.server.controllers")

class LdapSqlAlchemyIdentityProvider(SqlAlchemyIdentityProvider):
    """
    IdentityProvider that uses LDAP for authentication.
    """

    def __init__(self):
        super(LdapSqlAlchemyIdentityProvider, self).__init__()

        global user_class, group_class, permission_class, visit_class

        self.ldap = get("identity.ldap.enabled", False)
        if self.ldap:
            self.uri = get("identity.soldapprovider.uri", "ldaps://localhost")
            self.basedn  = get("identity.soldapprovider.basedn", "dc=localhost")
            self.autocreate = get("identity.soldapprovider.autocreate", False)
            # Only needed for devel. comment out for Prod.
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            log.info("uri :: %s" % self.uri)
            log.info("basedn :: %s" % self.basedn)
            log.info("autocreate :: %s" % self.autocreate)

        user_class_path = get("identity.saprovider.model.user",
                              None)
        user_class = load_class(user_class_path)
        group_class_path = get("identity.saprovider.model.group",
                                None)
        group_class = load_class(group_class_path)
        permission_class_path = get("identity.saprovider.model.permission",
                                    None)
        permission_class = load_class(permission_class_path)
        visit_class_path = get("identity.saprovider.model.visit",
                               None)
        log.info("Loading: %s", visit_class_path)
        visit_class = load_class(visit_class_path)


    def validate_identity(self, user_name, password, visit_key, krb=None):
        user = user_class.by_user_name(user_name)
        if not user:
            log.warning("No such user: %s", user_name)
            return None
        if user.disabled:
            log.warning("User %s has been disabled", user_name)
            return None
        if user.removed:
            log.warning("User %s has been removed", user_name)
            return None
        if not krb and not self.validate_password(user, user_name, password):
            log.warning("Passwords don't match for user: %s", user_name)
            return None
        log.info("Associating user (%s) with visit (%s)",
            user_name, visit_key)
        return SqlAlchemyIdentity(visit_key, user)

    def can_change_password(self, user_name):
        if self.ldap:
            ldapcon = ldap.initialize(self.uri)
            filter = "(uid=%s)" % user_name
            rc = ldapcon.search(self.basedn, ldap.SCOPE_SUBTREE, filter)
            objects = ldapcon.result(rc)[1]
            if len(objects) != 0:
                # LDAP user. No chance of changing password.
                return False
            else:
                # Assume non LDAP user
                return True
        else:
            return True

    def validate_password(self, user, user_name, password):
        '''
        Validates user_name and password against an AD domain.
        
        '''
        # Always try and authenticate against local DB first.
        if user.password == self.encrypt_password(password):
            return True
        # If ldap is enabled then try against that
        if self.ldap:
            ldapcon = ldap.initialize(self.uri)
            filter = "(uid=%s)" % user_name
            rc = ldapcon.search(self.basedn, ldap.SCOPE_SUBTREE, filter)
                            
            objects = ldapcon.result(rc)[1]

            if(len(objects) == 0):
                log.warning("No such LDAP user: %s" % user_name)
                return False
            elif(len(objects) > 1):
                log.error("Too many users: %s" % user_name)
                return False

            dn = objects[0][0]

            try:
                rc = ldapcon.simple_bind(dn, password)
                ldapcon.result(rc)
                return True
            except ldap.INVALID_CREDENTIALS:
                log.error("Invalid password supplied for %s" % user_name)
                return False
        # Nothing autheticated. 
	return False

    def load_identity(self, visit_key):
        user = super(LdapSqlAlchemyIdentityProvider, self).load_identity(visit_key)
        if not user.anonymous:
            return user

        if cherrypy.request.login:
            if cherrypy.request.login.find("@") != -1:
                (user_name, realm) = cherrypy.request.login.split('@')
            else:
                user_name = cherrypy.request.login
        else:
            return None
        set_login_attempted( True )
        return self.validate_identity( user_name, None, visit_key, True )
