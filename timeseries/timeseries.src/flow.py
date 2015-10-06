import BaseHTTPServer
import pkgutil
import subprocess
import sys
import urlparse

import html
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

    def prepare(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        global out
        out = self.wfile

    def do_GET(self):
        if self.path=='/':
            self.prepare()
            html.page(self.server.opt, server=True)
        else:
            util.msg(self.path, 'NOT FOUND')
            self.send_response(404)

    def do_POST(self):
        util.msg('POST', self.path)
        if self.path=='/zoom':
            l = int(self.headers.getheader('content-length', 0))
            req = urlparse.parse_qs(self.rfile.read(l))
            self.prepare()
            self.server.opt = html.zoom(self.server.opt, req['start'][0], req['end'][0])
            


#
#
#

def main(opt):

    url = 'http://localhost:%d' % opt.port

    if opt.browser:

        opt.server = True
        cmd = None

        if sys.platform=='darwin':
            cmd = 'sleep 1; open -a "Google Chrome" %s' % url
        elif sys.platform=='linux2':
            cmd = 'sleep 1; google-chrome %s &' % url

        if cmd:
            rc = subprocess.call(cmd, shell=True)
            if rc != 0:
                util.msg('can\'t open browser; is Google Chrome installed?')
        else:
            util.msg('don\'t know how to open a browser on your platform')


    if opt.server:
        httpd = BaseHTTPServer.HTTPServer(('', opt.port), Handler)
        httpd.opt = opt
        util.msg('listening for a browser request for %s' % url)
        httpd.serve_forever()
    else:
        global out
        out = sys.stdout
        html.page(opt, server=False)
