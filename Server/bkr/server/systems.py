
from turbogears import expose, identity, controllers
from bkr.server.model import System
from bkr.server.xmlrpccontroller import RPCRoot

__all__ = ['SystemsController']

class SystemsController(controllers.Controller):
    # For XMLRPC methods in this class.
    exposed = True

    @expose()
    @identity.require(identity.not_anonymous())
    def reserve(self, fqdn):
        """
        "Reserves" (a.k.a. "takes") the system with the given fully-qualified domain 
        name. The caller then becomes the user of the system, and can 
        provision it at will.

        A system may only be reserved when: its condition is 'Manual', it is not 
        currently in use, and the caller has permission to use the system.
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.reserve(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def release(self, fqdn):
        """
        Releases a reservation on the system with the given fully-qualified 
        domain name.

        The caller must be the current user of a system (i.e. must have 
        successfully reserved it previously).
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.unreserve(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

# for sphinx
systems = SystemsController
