
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Utilities to help with Flask based web interfaces
"""
import contextlib
import functools
from werkzeug.exceptions import HTTPException
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.bexceptions import InsufficientSystemPermissions


# Error handling helpers that play nice with the Beaker CLI.
# These report HTTP errors as plain text responses containing just the
# error message details, which the client then intercepts and displays as
# the error message for a failed command.

class PlainTextHTTPException(HTTPException):
    """A base class for returning error details as plain text"""
    def get_body(self, environ):
        return self.description
    def get_headers(self, environ):
        return [('Content-Type', 'text/plain')]

class BadRequest400(PlainTextHTTPException):
    code = 400

class Unauthorised401(PlainTextHTTPException):
    code = 401

class Forbidden403(PlainTextHTTPException):
    code = 403
    def get_body(self, environ):
        return ("Insufficient permissions: " + self.description)

class NotFound404(PlainTextHTTPException):
    code = 404

class MethodNotAllowed405(PlainTextHTTPException):
    code = 405

@contextlib.contextmanager
def convert_internal_errors():
    """Context manager to convert Python exceptions to HTTP errors"""
    try:
        yield
    except (NoResultFound, ValueError) as exc:
        raise BadRequest400(str(exc))
    except InsufficientSystemPermissions as exc:
        raise Forbidden403(str(exc))

def auth_required(f):
    """Decorator that reports a 401 error if the user is not logged in"""
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        if not identity.current.user:
            raise Unauthorised401("Authenticated user required")
        return f(*args, **kwds)
    return wrapper

def read_json_request(request):
    """Helper that throws a 400 error if the request has no JSON data"""
    data = request.json
    if not data:
        raise BadRequest400("No JSON payload in request")
    return data
