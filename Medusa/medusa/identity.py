from turbogears.identity.saprovider import SqlAlchemyIdentityProvider, SqlAlchemyIdentity
from turbogears.identity import set_login_attempted
from turbogears.config import get
from turbogears.database import session
from turbogears.util import load_class
import ldap
import logging
import krbV
import cherrypy
import os
log = logging.getLogger("medusa.controllers")

class LdapSqlAlchemyIdentityProvider(SqlAlchemyIdentityProvider):
    """
    IdentityProvider that uses LDAP for authentication.
    """

    def __init__(self):
        super(LdapSqlAlchemyIdentityProvider, self).__init__()

        self.uri = get("identity.soldapprovider.uri", "ldaps://localhost")
        self.host = get("identity.soldapprovider.host", "localhost")
        self.port = get("identity.soldapprovider.port", 389)
        self.basedn  = get("identity.soldapprovider.basedn", "dc=localhost")
        self.autocreate = get("identity.soldapprovider.autocreate", False)

        user_class_path = get("identity.saprovider.model.user",
                              None)
        self.user_class = load_class(user_class_path)
        group_class_path = get("identity.saprovider.model.group",
                                None)
        self.group_class = load_class(group_class_path)
        permission_class_path = get("identity.saprovider.model.permission",
                                    None)
        self.permission_class = load_class(permission_class_path)
        visit_class_path = get("identity.saprovider.model.visit",
                               None)
        log.info("Loading: %s", visit_class_path)
        self.visit_class = load_class(visit_class_path)

        log.info("uri :: %s" % self.uri)
        log.info("host :: %s" % self.host)
        log.info("port :: %d" % self.port)
        log.info("basedn :: %s" % self.basedn)
        log.info("autocreate :: %s" % self.autocreate)

    def validate_identity(self, user_name, password, visit_key, krb=None):
        objects = self.validate_password(None, user_name, password, krb)
        if objects:
            user = session.query(self.user_class).get_by(user_name=user_name)
            if not user:
                if self.autocreate:
                    user = self.user_class()
                    user.user_name = user_name
                    user.display_name = objects[0][1]['cn'][0]
                    user.email_address = objects[0][1]['mail'][0]
                    session.save(user)
                    session.flush()
                else:
                    return None
            link = session.query(self.visit_class).get_by(visit_key=visit_key)
            if not link:
                link = self.visit_class(visit_key=visit_key, user_id=user.user_id)
                session.save(link)
            else:
                link.user_id = user.user_id
            session.flush()
            return SqlAlchemyIdentity(visit_key, user)
        return None

    def validate_password( self, user, user_name, password, krb=None ):
        '''
        Validates user_name and password against an AD domain.
        
        '''
        # Only needed for devel.  comment out for Prod.
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        #ldapcon = ldap.open(self.host, self.port)
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

        if not krb:
            try:
                rc = ldapcon.simple_bind(dn, password)
                ldapcon.result(rc)
            except ldap.INVALID_CREDENTIALS:
                log.error("Invalid password supplied for %s" % user_name)
                return False

	return objects

    def load_identity(self, visit_key):
        user = super(LdapSqlAlchemyIdentityProvider, self).load_identity(visit_key)
        if not user.anonymous:
            return user

        try:
            os.environ["KRB5CCNAME"] = cherrypy.request.headers['X-FORWARDED-KEYTAB']
            ccache = krbV.CCache(cherrypy.request.headers['X-FORWARDED-KEYTAB'])
            (user_name, realm) = ccache.principal().name.split('@')
        except KeyError:
            return None
        except AttributeError:
            return None
        except krbV.Krb5Error:
            return None
        set_login_attempted( True )
        return self.validate_identity( user_name, None, visit_key, True )

    def by_name(self, user_name):
        """
        Looks up user_name against an AD domain.
        """

        # Only needed for devel.  comment out for Prod.
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        ldapcon = ldap.initialize(self.uri)

        filter = "(uid=%s*)" % user_name
        rc = ldapcon.search(self.basedn, ldap.SCOPE_SUBTREE, filter)
                            
        objects = ldapcon.result(rc)[1]
        return [object[0].split(',')[0].split('=')[1] for object in objects]
