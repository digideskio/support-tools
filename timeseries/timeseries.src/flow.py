import BaseHTTPServer
import json
import os
import pipes
import shlex
import subprocess
import sys
import urllib
import urlparse

import __main__
import html
import util


#
# html helpers
#

class Ses:

    sessions = {}

    def __init__(self, opt, path=None, server=False):
        self.saved = None
        self.opened = []
        self.out = sys.stdout
        self.title = []
        self.advice = []
        self.opt = opt
        if not path:
            path = '/%d' % len(Ses.sessions)
        self.path = path
        self.server = server
        Ses.sessions[self.path] = self

    def put(self, *content):
        for s in content:
            self.out.write(s)
            if self.saved != None:
                self.saved.append(s)
    
    def elt(self, name, attrs=None):
        self.opened.append(name)
        self.put('<%s' % name)
        if attrs:
            for a in sorted(attrs):
                self.put(' %s="%s"' % (a, attrs[a]))
        self.put('>')
    
    def eltend(self, name, attrs=None, *content):
        self.elt(name, attrs)
        self.put(*content)
        self.end(name)
    
    def end(self, name):
        assert(self.opened.pop()==name)
        self.put('</' + name + '>')
    
    def endall(self):
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
        if self.server:
            self.put(msg + '<br/><script>this.document.body.scrollIntoView(false)</script>')
        util.msg(msg)
    
    def advise(self, msg, pos=-1):
        if pos >= 0:
            self.advice.insert(pos, msg)
        else:
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

        # parse command-line args passed in url query string as an 'args' parameter
        def query2opt(query):
            args = shlex.split(query['args'][0])
            return __main__.get_opt(args)

        # parse url, extracting path and query portions
        _, _, path, _, query, _ = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(query)

        # query to root is redirected to default session 0
        if path=='/':
            self.send_response(301) # permanent
            self.send_header('Location', '/0')

        # open a new view in a new window
        # expects command-line arg string in url parameter "args"
        # parse off the query, open new session based on that, then redirect to bare session url
        elif path=='/open':
            opt = query2opt(query) # parse url "args" parameter
            ses = Ses(opt, server=True) # new session
            self.send_response(302) # temporary redirect
            self.send_header('Location', ses.path)

        # top-level page: return the container, which includes
        #   progress message area - loaded via /ses/progress url in progress phase (below)
        #   content area - loaded via /ses/content url in content phase (below)
        elif path in Ses.sessions:
            ses = Ses.sessions[path]
            self.prepare(ses)
            html.container(ses)

        # info for a given time t
        elif path.endswith('/info'):
            path = path.rsplit('/', 1)[0]
            ses = Ses.sessions[path]
            t = float(query['t'][0])
            self.prepare(ses)
            html.info(ses, t)

        # raw info for a given time t
        elif path.endswith('/raw'):
            path = path.rsplit('/', 1)[0]
            ses = Ses.sessions[path]
            t = float(query['t'][0])
            self.prepare(ses)
            html.raw(ses, t, kind='raw')

        elif path.endswith('/metadata'):
            path = path.rsplit('/', 1)[0]
            ses = Ses.sessions[path]
            t = float(query['t'][0])
            self.prepare(ses)
            html.raw(ses, t, kind='metadata')

        # progress phase: load the data in preparation for generating content
        # while emitting progress messages. We also accept new view parameters to open
        # new view in current window as command-line arg string in url parameter "args"
        elif path.endswith('/progress'):
            path = path.rsplit('/', 1)[0]
            ses = Ses.sessions[path]
            if 'args' in query:
                ses.opt = query2opt(query) # parse url "args" parameter
            self.prepare(ses)
            html.load(ses)

        # content phase: generate actual html view from graph data loadedin progress phase
        elif path.endswith('/content'):
            path = path.rsplit('/', 1)[0]
            ses = Ses.sessions[path]
            self.prepare(ses)
            html.page(ses)
            
        # otherwise not found
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
            open(fn, 'w').write(ses.get_save())
            util.msg('saved to', fn)

def browser(url):

    # what os?
    if sys.platform=='darwin':
        cmd = 'sleep 1; open -a "Google Chrome" "%s"' % url
    elif sys.platform=='linux2':
        cmd = 'sleep 1; google-chrome "%s" &' % url
    elif sys.platform=='win32':
        cmd = 'timeout 2 && start /b chrome "%s" &' % url
    else:
        raise Exception('unknown platform ' + sys.platform)

    # launch it
    if cmd:
        rc = subprocess.call(cmd, shell=True)
        if rc != 0:
            util.msg('can\'t open browser; is Google Chrome installed?')
    else:
        util.msg('don\'t know how to open a browser on your platform')


def main(opt):

    if opt.browser:
        opt.server = True

    # --server or --browser
    if opt.server:
        httpd = None
        for opt.port in range(opt.port, opt.port+100):
            try:
                httpd = BaseHTTPServer.HTTPServer(('', opt.port), Handler)
                break
            except Exception as e:
                util.msg('can\'t open port %d: %s' % (opt.port, e))
        if not httpd:
            raise e
        httpd.ses = Ses(opt, path='/0', server=True) # default session
        url = 'http://localhost:%d' % opt.port
        util.msg('listening for a browser request for %s' % url)
        if opt.browser:
            browser(url)
        httpd.serve_forever()

    # --connect
    elif opt.connect:
        args = ' '.join(pipes.quote(s) for s in sys.argv[1:])
        args = urllib.urlencode({'args': args})
        url = opt.connect + '/open?' + args
        browser(url)

    # standalone static html
    else:
        ses = Ses(opt, server=False)
        ses.out = sys.stdout
        html.page(ses)
