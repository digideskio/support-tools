import BaseHTTPServer
import html
import sys
import util


#
# html helpers
#

def elt(name, attrs={}):
    out.write('<%s' % name)
    for a in sorted(attrs):
        out.write(' %s="%s"' % (a, attrs[a]))
    out.write('>')

def eltend(name, attrs={}, *content):
    elt(name, attrs)
    put(*content)
    end(name)

def end(name):
    out.write('</' + name + '>')

def put(*content):
    for s in content:
        out.write(s)

def td(cls, *content):
    elt('td', {'class':cls})
    if content:
        put(*content)
        end('td')

#
#
#

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        global out
        out = self.wfile
        html.page(self.server.opt)


#
#
#

def main(opt):

    if opt.server:
        port = 8888
        httpd = BaseHTTPServer.HTTPServer(('', port), Handler)
        httpd.opt = opt
        util.msg('listening')
        httpd.serve_forever()
    else:
        global out
        out = sys.stdout
        html.page(opt)
