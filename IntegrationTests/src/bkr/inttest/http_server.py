import SimpleHTTPServer
import SocketServer


class HTTPServer(object):

    def __init__(self, port):
        self.handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        self.httpd = SocketServer.TCPServer(("", port), self.handler)

    def start(self):
        self.httpd.serve_forever()

if __name__ in ('main', '__main__'):
    server = HTTPServer(19998)
    server.start()
