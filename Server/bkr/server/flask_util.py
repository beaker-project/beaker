
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
from flask import request, redirect
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.bexceptions import BX, InsufficientSystemPermissions, DatabaseLookupError, \
    StaleTaskStatusException
from bkr.server.search_utility import lucene_to_sqlalchemy
from bkr.server.util import absolute_url, strip_webpath

# http://flask.pocoo.org/snippets/45/
def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return (best == 'application/json' and
            request.accept_mimetypes[best] > request.accept_mimetypes['text/html'])

class PaginationRequiredException(HTTPException):
    code = 302
    # delete the following when we have Werkzeug 0.9:
    def __init__(self, response):
        self.response = response
    def get_response(self, environ):
        return self.response

def json_collection(query, columns=None, extra_sort_columns=None, max_page_size=500,
                    default_page_size=20, force_paging_for_count=500,skip_count=False):
    """
    Helper function for Flask request handlers which want to return 
    a collection of resources as JSON.

    The return value is a Python dict suitable for serialization into JSON, in 
    a format corresponding to Beaker's API for "pageable JSON collections" 
    (defined in documentation/server-api/http.rst). The caller can either 
    return a JSON response directly by passing the return value to 
    flask.jsonify(), or serialize it and embed it in an HTML response.
    """
    if columns is None:
        columns = {}
    if extra_sort_columns is None:
        extra_sort_columns = {}
    result = {}
    if request.args.get('q') and columns:
        query = query.filter(lucene_to_sqlalchemy(request.args['q'],
                search_columns=columns,
                default_columns=set(columns.values())))
        result['q'] = request.args['q']
    if not skip_count:
        total_count = query.order_by(None).count()
        result['count'] = total_count
        force_paging = (total_count > force_paging_for_count)
    else:
        force_paging = True
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
            page_size = min(page_size, max_page_size)
        elif not request_wants_json():
            # For the web UI, we always do paging even if the query params 
            # didn't request it.
            page_size = default_page_size
        elif force_paging and request_wants_json():
            # If an API user didn't request paging but we are forcing it 
            # because of the result size, then we redirect them to the URL with 
            # a page_size= param added, as a way of indicating that they should 
            # be using paging. There's no point doing this for the web UI though.
            if request.query_string:
                url = '%s?%s&page_size=%s' % (request.path, request.query_string, default_page_size)
            else:
                url = '%s?page_size=%s' % (request.path, default_page_size)
            # absolute_url() prepends webpath so strip it off first
            url = absolute_url(strip_webpath(url))
            raise PaginationRequiredException(response=redirect(url))
        elif force_paging:
            page_size = default_page_size
        else:
            page_size = None
        if page_size:
            query = query.limit(page_size)
            page = int(request.args.get('page', 1))
            if page > 1:
                query = query.offset((page - 1) * page_size)
            result['page'] = page
            result['page_size'] = page_size
        result['entries'] = query.all()
        if len(result['entries']) < page_size and 'count' not in result:
            # Even if we're not counting rows for performance reason, we know 
            # we have reached the end of the rows if we returned fewer than the 
            # page size. In this case we can infer the total count and return 
            # it to the client, so that they know they are at the last page.
            result['count'] = (page - 1) * page_size + len(result['entries'])
    return result

def render_tg_template(template_name, data):
    """
    Helper for Flask handlers to render a Kid template in 
    a TurboGears-compatible way. This reimplements the bare minimum TG magic 
    bits needed to successfully render a template inheriting from master.kid.
    """
    from turbogears.view import render
    # These are the widgets which are always included on every page (as defined 
    # in tg.include_widgets) minus Mochikit because we are not using that in any 
    # new code.
    from bkr.server.widgets import jquery, beaker_js, beaker_css
    data['tg_css'] = beaker_css.retrieve_css()
    data['tg_js_head'] = jquery.retrieve_javascript() + beaker_js.retrieve_javascript()
    data['tg_js_bodytop'] = []
    data['tg_js_bodybottom'] = []
    # If the worker has previously handled a CherryPy request then 
    # cherrypy.request will be left behind from that, and 
    # turbogears.util.request_available will be fooled into thinking we are 
    # actually inside CherryPy. The base implementation of 
    # turbogears.widgets.Widget#display tries to check tg_template_enginename if 
    # it thinks a CherryPy request is available, so we just set it here to 
    # avoid AttributeErrors in that code (since we really aren't inside 
    # a CherryPy request at this point).
    import cherrypy
    try:
        cherrypy.request.tg_template_enginename = 'kid'
    except AttributeError:
        pass
    return render(data, template_name)

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

class Gone410(PlainTextHTTPException):
    code = 410

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
    except StaleTaskStatusException as exc:
        raise Conflict409(unicode(exc))
    except (BX, NoResultFound, ValueError, DatabaseLookupError) as exc:
        raise BadRequest400(unicode(exc))

def auth_required(f):
    """Decorator that reports a 401 error if the user is not logged in"""
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        if not identity.current.user:
            if request.method in ['GET', 'HEAD'] and not request_wants_json():
                forward_url = request.path
                if request.query_string:
                    forward_url += '?' + request.query_string
                return redirect(absolute_url('/login', forward_url=forward_url))
            raise Unauthorised401("Authenticated user required")
        return f(*args, **kwds)
    return wrapper

def admin_auth_required(f):
    """Decorator that reports a 403 error if the user is not an admin"""
    @auth_required
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        if not identity.current.user.is_admin():
            raise Forbidden403("You are not a member of the admin group")
        return f(*args, **kwds)
    return wrapper

def read_json_request(request):
    """Helper that throws a 400 error if the request has no JSON data"""
    data = request.json
    if not data:
        raise UnsupportedMediaType415("No JSON payload in request")
    return data

_stringbool_true_values = frozenset(['true', 't', 'yes', 'y', 'on', '1'])
_stringbool_false_values = frozenset(['false', 'f', 'no', 'n', 'off', '0'])
def stringbool(value):
    """
    Conversion function for mapping strings like 'true' and 'false' to Python 
    bools. Use this with request.args.get(). Conversion rules match the same 
    ones used by the TG/FormEncode StringBool validator.
    """
    if value.lower() in _stringbool_true_values:
        return True
    elif value.lower() in _stringbool_false_values:
        return False
    else:
        raise ValueError('Value %r is not a valid boolean value' % value)
