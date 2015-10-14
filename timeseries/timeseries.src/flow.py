import BaseHTTPServer
import json
import os
import pipes
import pkgutil
import shlex
import subprocess
import sys
import uuid
import urllib
import urlparse

import __main__
import flow
import html
import util


#
# html helpers
#

class Ses:

    sessions = {}

    def __init__(self, opt, path=None):
        self.saved = None
        self.opened = []
        self.out = sys.stdout
        self.in_progress = False
        self.title = []
        self.advice = []
        self.opt = opt
        if not path:
            path = '/%d' % len(Ses.sessions)
        self.path = path
        Ses.sessions[self.path] = self

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

    def prepare(self, ses):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        ses.out = self.wfile

    def do_GET(self):
        _, _, path, _, query, _ = urlparse.urlparse(self.path)
        if path=='/open':
            query = urlparse.parse_qs(query)
            args = shlex.split(query['args'][0])
            opt = __main__.get_opt(args)
            ses = Ses(opt) # new session
            self.send_response(302) # temporary redirect
            self.send_header('Location', ses.path)
        elif path in Ses.sessions:
            ses = Ses.sessions[path]
            self.prepare(ses)
            html.page(ses, server=True)
        else:
            self.send_response(404) # not found

    def do_POST(self):
        util.msg('POST', self.path)
        if self.path.endswith('/model'):
            path = self.path[:-len('/model')] # strip off /model to get session path
            ses = Ses.sessions[path]
            l = int(self.headers.getheader('content-length', 0))
            data = self.rfile.read(l)
            js = json.loads(data)
            for name in js:
                setattr(ses.opt, name, js[name])
        elif self.path=='/save':
            l = int(self.headers.getheader('content-length', 0))
            req = urlparse.parse_qs(self.rfile.read(l))
            fn = req['fn'][0]
            open(fn, 'w').write(get_save())
            util.msg('saved to', fn)

def browser(url, delay=0):

    # what os?
    if sys.platform=='darwin':
        cmd = 'sleep 1; open -a "Google Chrome" "%s"' % url
    elif sys.platform=='linux2':
        cmd = 'sleep 1; google-chrome "%s" &' % url

    # launch it
    if cmd:
        rc = subprocess.call(cmd, shell=True)
        if rc != 0:
            util.msg('can\'t open browser; is Google Chrome installed?')
    else:
        util.msg('don\'t know how to open a browser on your platform')


def main(opt):

    url = 'http://localhost:%d' % opt.port
    if opt.browser:
        browser(url, delay=1)
        opt.server = True
        cmd = None

    if opt.server:
        ses = flow.Ses(opt, '/')
        httpd = BaseHTTPServer.HTTPServer(('', opt.port), Handler)
        httpd.ses = ses # default session - xxx bad idea?
        util.msg('listening for a browser request for %s' % url)
        httpd.serve_forever()
    elif opt.connect:
        args = ' '.join(pipes.quote(s) for s in sys.argv[1:])
        args = urllib.urlencode({'args': args})
        util.msg('xxx oc', opt.connect)
        url = opt.connect + '/open?' + args
        util.msg('xxx', url)
        browser(url)
    else:
        ses = flow.Ses(opt)
        ses.out = sys.stdout
        html.page(ses, server=False)
