from mod_python import apache
from DocXMLRPCServer import ServerHTMLDoc
import xmlrpclib
from labcontroller import Labcontroller
 
def handler(req):
    exposed_instance = Labcontroller()
    all_methods = list_public_methods(exposed_instance)
    all_methods.append("system.listMethods")
    if req.method == "GET":
        req.content_type = "text/html; charset=UTF-8"
        req.send_http_header()
        srv = ServerHTMLDoc()
        req.write(srv.docserver("XMLRPC server in Apache", "", dict([(m,getattr(exposed_instance,m,None)) for m in all_methods]) ))
        return_val = apache.OK
    elif req.method == "POST":
        data = req.read()
        if data == "":
            req.content_type = "text/html"
            req.send_http_header()
            return_val = apache.HTTP_EXPECTATION_FAILED
        else:
            req.content_type = "text/xml"
            req.send_http_header()
            params, method = xmlrpclib.loads(data)
            if method == "system.listMethods":
                req.write(xmlrpclib.dumps((all_methods,), methodresponse = True))
            else:
                if method in all_methods:
                    req.write(xmlrpclib.dumps((getattr(exposed_instance,method)(*params),), methodresponse = True, allow_none = True))
                else:
                    req.write(xmlrpclib.dumps(((-2, "Unknown function : %s" % str(method), "",{}),), methodresponse = True, allow_none = True))
        return_val = apache.OK
    return return_val

#======================================================

def authenhandler(req):
    """
    Verify user has permision.
    """

    pw   = req.get_basic_auth_pw()
    user = req.user
    if user == "testing" and pw == "testing":
       return apache.OK
    else:
       return apache.HTTP_UNAUTHORIZED


def list_public_methods(obj):
    """Returns a list of attribute strings, found in the specified
    object, which represent callable attributes"""

    return [member for member in dir(obj)
                if not member.startswith('_') and
                    callable(getattr(obj, member))]


