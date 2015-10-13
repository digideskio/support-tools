import BaseHTTPServer
import pkgutil
import subprocess
import sys
import urlparse

import flow
import html
import os
import util


#
# html helpers
#

class Ses:

    def __init__(self):
        self.saved = None
        self.opened = []
        self.out = sys.stdout
        self.in_progress = False
        self.title = []
        self.advice = []

    def put(self, *content):
        for s in content:
            self.out.write(s)
            if self.saved != None:
                self.saved.append(s)
    
    def elt(self, name, attrs={}):
        self.opened.append(name)
        self.put('<%s' % name)
        for a in sorted(attrs):
            self.put(' %s="%s"' % (a, attrs[a]))
        self.put('>')
    
    def eltend(self, name, attrs={}, *content):
        self.elt(name, attrs)
        self.put(*content)
        self.end(name)
    
    def end(self, name):
        assert(self.opened.pop()==name)
        self.put('</' + name + '>')
    
    def endall(self, ):
        while self.opened:
            self.end(self.opened[-1])
    
    def td(self, cls, *content):
        self.elt('td', {'class':cls})
        if content:
            self.put(*content)
            self.end('td')
    
    def start_save(self):
        self.saved = []
    
    def get_save(self):
        return ''.join(self.saved)

    def progress(self, msg):
        if self.in_progress:
            self.put(msg + '<br/>')
        util.msg(msg)
    
    def advise(self, msg):
        self.advice.append(msg)
    
    def add_title(self, fn):
        self.title.append(os.path.basename(fn))



#
#
#

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

    def prepare(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.server.ses.out = self.wfile

    def param(self, name, q, convert):
        if name in q:
            value = convert(q[name])
            setattr(self.server.ses.opt, name, value)
            #util.msg(name, value)

    def do_GET(self):
        self.prepare()
        html.page(self.server.ses, server=True)

    def do_POST(self):
        util.msg('POST', self.path)
        if self.path=='/zoom':
            l = int(self.headers.getheader('content-length', 0))
            q = urlparse.parse_qs(self.rfile.read(l))
            self.param('after', q, lambda x: float(x[0]))
            self.param('before', q, lambda x: float(x[0]))
            self.param('cursors', q, lambda x: map(float, x))
            self.param('level', q, lambda x: int(x[0]))
            self.send_response(301) # redirect
            self.send_header('Location', '/')
        elif self.path=='/save':
            l = int(self.headers.getheader('content-length', 0))
            req = urlparse.parse_qs(self.rfile.read(l))
            fn = req['fn'][0]
            open(fn, 'w').write(get_save())
            util.msg('saved to', fn)

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
        ses = flow.Ses()
        ses.opt = opt
        httpd = BaseHTTPServer.HTTPServer(('', opt.port), Handler)
        httpd.ses = ses
        util.msg('listening for a browser request for %s' % url)
        httpd.serve_forever()
    else:
        ses = flow.Ses()
        ses.out = sys.stdout
        ses.opt = opt
        html.page(ses, server=False)
