import urllib2 as u2

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
        return super(BeakerRequest, self).get_method()
