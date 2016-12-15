
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
A simple HTTP server for testing. It serves the directory tree under the base 
directory given with --base. DELETE requests are allowed if --writable is given.

It also treats the following paths specially:

/redirect/<status>/<path>
    Responds with a <status> redirect to <path>.

/error/<status>[/...]
    Responds with a <status> error. Extra path information is ignored.

/slow/<delay>[/...]
    Waits <delay> seconds and then responds with a dummy response body. Extra 
    path information is ignored.
"""

import os, os.path
import re
import time
import shutil
import urlparse
import mimetypes
import wsgiref.util, wsgiref.simple_server

class Application(object):

    def __init__(self, basepath, writable=False, response_headers=[]):
        assert basepath not in (None, '', '/')
        self.basepath = basepath
        self.writable = writable
        self.response_headers = [tuple(h.split(':', 1)) for h in response_headers]

    def __call__(self, environ, start_response):
        path_info = os.path.normpath(environ['PATH_INFO'])
        assert '..' not in path_info
        assert path_info.startswith('/')
        response_headers = list(self.response_headers)
        m = re.match(r'/redirect/(\d+)/(.*)$', path_info)
        if m:
            response_headers.append(('Location',
                    wsgiref.util.application_uri(environ) + m.group(2)))
            start_response('%s Redirected' % m.group(1), response_headers)
            return []
        m = re.match(r'/error/(\d+)(/?.*)$', path_info)
        if m:
            start_response('%s Error' % m.group(1), response_headers)
            return []
        m = re.match(r'/slow/(\d+)(/?.*)$', path_info)
        if m:
            time.sleep(int(m.group(1)))
            start_response('204 No Content', response_headers)
            return []
        localpath = os.path.join(self.basepath, path_info.lstrip('/'))
        if os.path.isdir(localpath) and not environ['PATH_INFO'].endswith('/'):
            response_headers.append(('Location',
                    wsgiref.util.request_uri(environ, include_query=False) + '/'))
            start_response('301 Moved', response_headers)
            return []
        if not os.path.exists(localpath):
            start_response('404 Not Found', response_headers)
            return []
        if environ['REQUEST_METHOD'] in ('GET', 'HEAD'):
            if os.path.isdir(localpath):
                listing = '\n'.join(os.listdir(localpath))
                response_headers.append(('Content-Length', str(len(listing))))
                response_headers.append(('Content-Type', 'text/plain'))
                start_response('200 OK', response_headers)
                return [listing]
            else:
                response_headers.append(('Content-Length', str(os.path.getsize(localpath))))
                mimetype, encoding = mimetypes.guess_type(localpath)
                response_headers.append(('Content-Type', mimetype or 'application/octet-stream'))
                start_response('200 OK', response_headers)
                return wsgiref.util.FileWrapper(open(localpath, 'r'))
        elif environ['REQUEST_METHOD'] == 'DELETE' and self.writable:
            shutil.rmtree(localpath)
            start_response('204 No Content', response_headers)
            return []
        else:
            start_response('405 Method Not Allowed', response_headers)
            return []

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--base', metavar='PATH')
    parser.add_option('--writable', action='store_true')
    parser.add_option('--add-response-header', dest='response_headers',
            metavar='HEADER', action='append', default=[])
    opts, args = parser.parse_args()
    if not opts.base:
        parser.error('Specify base directory with --base')
    application = Application(opts.base, opts.writable, opts.response_headers)
    server = wsgiref.simple_server.make_server('', 19998, application)
    server.serve_forever()
