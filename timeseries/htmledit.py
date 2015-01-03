import BaseHTTPServer
import subprocess
import sys

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(original_page)
    def do_PUT(self):
        try:
            n = int(self.headers["Content-Length"])
            new_page = self.rfile.read(n)
            open(fn, 'w').write(new_page)
            print 'saved', n, 'bytes to', fn
        except Exception as e:
            print e

port = 8888
fn = sys.argv[1]
original_page = open(fn).read()
httpd = BaseHTTPServer.HTTPServer(('localhost', 8888), Handler)
url = 'http://localhost:{port}/{fn}'.format(port=port, fn=fn)
subprocess.call(['open', url])
httpd.serve_forever()
