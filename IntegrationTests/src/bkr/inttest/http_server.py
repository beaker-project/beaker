
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import SimpleHTTPServer
import SocketServer


class HTTPServer(SocketServer.TCPServer):

    def __init__(self, port):
        self.allow_reuse_address = True
        self.handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        SocketServer.TCPServer.__init__(self, ('', port), self.handler)

if __name__ in ('main', '__main__'):
    server = HTTPServer(19998)
    server.serve_forever()
