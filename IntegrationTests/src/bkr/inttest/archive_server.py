#!/usr/bin/python

"""
A fake archive server for Beaker logs. It answers the following paths:

/redirect/<status>/<path>
    Responds with a <status> redirect to <path>.

/<path>
    Allows GET and DELETE of files underneath the base path of the server.
"""

import os, os.path
import re
import shutil
import urlparse
import wsgiref.util, wsgiref.simple_server

class ArchiveServer(object):

    def __init__(self, basepath):
        assert basepath not in (None, '', '/')
        self.basepath = basepath

    def wsgi(self, environ, start_response):
        m = re.match(r'/redirect/(\d+)/(.*)$', environ['PATH_INFO'])
        if m:
            start_response('%s Redirected' % m.group(1), [('Location',
                    wsgiref.util.application_uri(environ) + m.group(2))])
            return []
        assert '..' not in environ['PATH_INFO']
        assert environ['PATH_INFO'].startswith('/')
        localpath = os.path.join(self.basepath, environ['PATH_INFO'].lstrip('/'))
        if os.path.isdir(localpath) and not localpath.endswith('/'):
            start_response('301 Moved', [('Location',
                    wsgiref.util.request_uri(environ, include_query=False) + '/')])
            return []
        if not os.path.exists(localpath):
            start_response('404 Not Found', [])
            return []
        if environ['REQUEST_METHOD'] == 'GET':
            start_response('200 OK', [])
            return wsgiref.util.FileWrapper(open(localpath, 'r'))
        elif environ['REQUEST_METHOD'] == 'DELETE':
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
    opts, args = parser.parse_args()
    if not opts.base:
        parser.error('Specify base directory with --base')
    server = wsgiref.simple_server.make_server('', 19998, ArchiveServer(opts.base).wsgi)
    server.serve_forever()
