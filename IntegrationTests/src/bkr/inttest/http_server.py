#!/usr/bin/python

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
"""

import os, os.path
import re
import shutil
import urlparse
import wsgiref.util, wsgiref.simple_server

class Application(object):

    def __init__(self, basepath, writable=False):
        assert basepath not in (None, '', '/')
        self.basepath = basepath
        self.writable = writable

    def __call__(self, environ, start_response):
        path_info = os.path.normpath(environ['PATH_INFO'])
        assert '..' not in path_info
        assert path_info.startswith('/')
        m = re.match(r'/redirect/(\d+)/(.*)$', path_info)
        if m:
            start_response('%s Redirected' % m.group(1), [('Location',
                    wsgiref.util.application_uri(environ) + m.group(2))])
            return []
        localpath = os.path.join(self.basepath, path_info.lstrip('/'))
        if os.path.isdir(localpath) and not environ['PATH_INFO'].endswith('/'):
            start_response('301 Moved', [('Location',
                    wsgiref.util.request_uri(environ, include_query=False) + '/')])
            return []
        if not os.path.exists(localpath):
            start_response('404 Not Found', [])
            return []
        if environ['REQUEST_METHOD'] == 'GET':
            start_response('200 OK', [])
            if os.path.isdir(localpath):
                return '\n'.join(os.listdir(localpath))
            else:
                return wsgiref.util.FileWrapper(open(localpath, 'r'))
        elif environ['REQUEST_METHOD'] == 'DELETE' and self.writable:
            shutil.rmtree(localpath)
            start_response('204 No Content', [])
            return []
        else:
            start_response('405 Method Not Allowed', [])
            return []

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--base', metavar='PATH')
    parser.add_option('--writable', action='store_true')
    opts, args = parser.parse_args()
    if not opts.base:
        parser.error('Specify base directory with --base')
    application = Application(opts.base, opts.writable)
    server = wsgiref.simple_server.make_server('', 19998, application)
    server.serve_forever()
