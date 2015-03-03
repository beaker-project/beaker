
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
from flask import request, jsonify, redirect
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.bexceptions import BX, InsufficientSystemPermissions
from bkr.server.search_utility import lucene_to_sqlalchemy

def json_collection(columns=None, extra_sort_columns=None, min_page_size=20,
                    max_page_size=500, default_page_size=20, force_paging_for_count=500):
    """
    Decorator factory for Flask request handlers which want to return 
    a collection of resources as JSON. The decorated function should return 
    a SQLAlchemy Query object.

    There are API docs for this in documentation/server-api/http.rst.
    """
    if columns is None:
        columns = {}
    if extra_sort_columns is None:
        extra_sort_columns = {}
    def decorator(func):
        @functools.wraps(func)
        def _json_collection_decorated(*args, **kwargs):
            result = {}
            query = func(*args, **kwargs)
            if request.args.get('q') and columns:
                query = query.filter(lucene_to_sqlalchemy(request.args['q'],
                        search_columns=columns,
                        default_columns=set(columns.values())))
                result['q'] = request.args['q']
            total_count = query.order_by(None).count()
            result['count'] = total_count
            total_columns = columns.copy()
            total_columns.update(extra_sort_columns)
            if request.args.get('sort_by') in total_columns:
                result['sort_by'] = request.args['sort_by']
                sort_columns = total_columns[request.args['sort_by']]
                if not isinstance(sort_columns, tuple):
                    sort_columns = (sort_columns,)
                if request.args.get('order') == 'desc':
                    sort_order = 'desc'
                else:
                    sort_order = 'asc'
                result['order'] = sort_order
                query = query.order_by(None)
                for sort_column in sort_columns:
                    if sort_order == 'desc':
                       query = query.order_by(sort_column.desc())
                    else:
                       query = query.order_by(sort_column)
            with convert_internal_errors():
                if 'page_size' in request.args:
                    page_size = int(request.args['page_size'])
                    page_size = min(max(page_size, min_page_size), max_page_size)
                    query = query.limit(page_size)
                    page = int(request.args.get('page', 1))
                    if page > 1:
                        query = query.offset((page - 1) * page_size)
                    result['page'] = page
                    result['page_size'] = page_size
                elif total_count > force_paging_for_count:
                    if request.query_string:
                        url = request.url + ('&page_size=%s' % default_page_size)
                    else:
                        url = request.base_url + ('?page_size=%s' % default_page_size)
                    return redirect(url)
                result['entries'] = query.all()
            return jsonify(result)
        return _json_collection_decorated
    return decorator

# Error handling helpers that play nice with the Beaker CLI.
# These report HTTP errors as plain text responses containing just the
# error message details, which the client then intercepts and displays as
# the error message for a failed command.

class PlainTextHTTPException(HTTPException):
    """A base class for returning error details as plain text"""
    def get_body(self, environ):
        return self.description
    def get_headers(self, environ):
        return [('Content-Type', 'text/plain; charset=UTF-8')]

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

class Conflict409(PlainTextHTTPException):
    code = 409

class UnsupportedMediaType415(PlainTextHTTPException):
    """
    HTTP error response for when the *request* content type is not supported. 
    Not the same as 406 Not Acceptable.
    """
    code = 415

class ServiceUnavailable503(PlainTextHTTPException):
    code = 503

@contextlib.contextmanager
def convert_internal_errors():
    """Context manager to convert Python exceptions to HTTP errors"""
    try:
        yield
    except InsufficientSystemPermissions as exc:
        raise Forbidden403(unicode(exc))
    except (BX, NoResultFound, ValueError) as exc:
        raise BadRequest400(unicode(exc))

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
        raise UnsupportedMediaType415("No JSON payload in request")
    return data
