import urllib2 as u2
import urlparse

class DavDeleteErrorHandler(u2.BaseHandler):

    def http_error_204(self, request, response, *args, **kw):
        return response


    def http_error_404(self, request, response, *args, **kw):
        # If we're trying to delete something that doesn't exist,
        # no real drama
        return response

class BeakerRequest(u2.Request):

    def __init__(self, method=None, *args, **kw):
        u2.Request.__init__(self, *args, **kw)
        self._method = method

    def get_method(self):
        if self._method is not None:
            return self._method
        return u2.Request.get_method(self)

class RedirectHandler(u2.HTTPRedirectHandler):

    def http_error_302(req, fp, code, msg, hdrs, newurl):
        req = u2.HTTPRedirectHandler.http_error_302(req, fp, code, msg, hdrs, newurl)
        return req

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return BeakerRequest(url=newurl,
            headers=req.headers,
            method=req.get_method(),
            origin_req_host=req.get_origin_req_host(),
            unverifiable=True)
