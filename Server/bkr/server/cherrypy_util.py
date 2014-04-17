
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Utilities to help with CherryPy based web interfaces
"""
import cherrypy
from cherrypy import response

# Error handling helpers that report HTTP errors as plain text responses
# containing just the error message details, which will be displayed as
# the error message.
class PlainTextHTTPException(cherrypy.HTTPError):
    """
    A base class for returning error details as plain text
    """
    def __init__(self, status=500, message=None):
        self._status = status
        self._message = message
        super(PlainTextHTTPException, self).__init__()

    def set_response(self):
        response.status = self._status
        response.body = self._message
        response.headers['content-type'] = 'text/plain'
