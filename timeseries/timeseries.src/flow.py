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

saved = None
opened = []

def put(*content):
    for s in content:
        out.write(s)
        if saved != None:
            saved.append(s)

def elt(name, attrs={}):
    opened.append(name)
    put('<%s' % name)
    for a in sorted(attrs):
        put(' %s="%s"' % (a, attrs[a]))
    put('>')

def eltend(name, attrs={}, *content):
    elt(name, attrs)
    put(*content)
    end(name)

def end(name):
    assert(opened.pop()==name)
    put('</' + name + '>')

def endall():
    while opened:
        end(opened[-1])

def td(cls, *content):
    elt('td', {'class':cls})
    if content:
        put(*content)
        end('td')

def start_save():
    global saved
    saved = []

def get_save():
    return ''.join(saved)


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
            data = self.rfile.read(l)
            req = urlparse.parse_qs(data)
            self.prepare()
            self.server.opt = html.zoom(self.server.opt, req['start'][0], req['end'][0])
        elif self.path=='/save':
            l = int(self.headers.getheader('content-length', 0))
            req = urlparse.parse_qs(self.rfile.read(l))
            fn = req['fn'][0]
            open(fn, 'w').write(get_save())
            util.msg('saved to', fn)

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
