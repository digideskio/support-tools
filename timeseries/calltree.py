#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re
import argparse
from datetime import datetime, timedelta
import collections
import math
import os
import json
import pytz
import time
import dateutil.parser
import cgi

def dbg(*ss):
    if __name__=='__main__' and opt.dbg:
        sys.stderr.write(' '.join(str(s) for s in ss) + '\n')

def msg(*ss):
    sys.stderr.write(' '.join(str(s) for s in ss) + '\n')


#
# html stuff
#
# All non-ascii stuff is encoded here as utf-8 to avoid Unicode encoding issues on output
# However this requires that the eventual display medium understand utf-8
# We ensure that for html by using a charset declaration
# For display on a terminal or cut&paste into a file utf-8 support is required
#

def elt(name, attrs={}):
    if opt.html:
        sys.stdout.write('<%s' % name)
        for a in sorted(attrs):
            sys.stdout.write(' %s="%s"' % (a, attrs[a]))
        sys.stdout.write('>')

def eltend(name, attrs, *content):
    if opt.html:
        elt(name, attrs)
        put(*content)
        end(name)

def end(name):
    if opt.html:
        sys.stdout.write('</' + name + '>')

def put(*content):
    for s in content:
        sys.stdout.write(s)

def put_html(s):
    if opt.html:
        put(s)

#
# our html
#

html_down = '▽ '
html_right = '▷ '

html_script = '''
    function _hide(ctl, e) {
        if (ctl!='none') {
            e.style.display = 'none'
            document.getElementById('t'+e.id).innerHTML = '%s'
        } else {
            e.style.display = 'block'
            document.getElementById('t'+e.id).innerHTML = '%s'
        }
    }
    function hide(id) {
        var e = document.getElementById(id)
        _hide(e.style.display, e)
    }
    function _hide_all(ctl, e) {
        _hide(ctl, e)
        for (var i in e.childNodes) {
            var c = e.childNodes[i]
            if (c.tagName=='DIV')
                _hide_all(ctl, c)
        }
    }
    function hide_all(id) {
        var e = document.getElementById(id)
        _hide_all(e.style.display, e)
    }
'''  % (html_right, html_down)

html_style = '''
    pre, .fixed {
      font-family: menlo, "lucida console", courier, fixed;
      font-size: 8pt;
    }
    body {
      font-family: sans-serif;
      font-size: 9pt
    }
'''

html_help = '''
    Click on <span class='fixed'>%s</span> or <span class='fixed'>%s</span>
    to hide or show direct children of item.<br/>
    Click on a function name to hide or show all descendents of item.
''' % (html_down, html_right)

def html_head():
    elt('html')
    elt('head')
    elt('meta', {'charset':'utf-8'})
    elt('script')
    put_html(html_script)
    end('script')
    elt('style')
    if opt.graph_width: put_html(html.graphing_css)
    put_html(html_style)
    end('style')
    end('head')
    elt('body')
    put_html(html_help)
    elt('pre')

def html_foot():
    end('pre')
    end('body')
    end('html')
    

#
# call tree
#

def simplify_templates(func):
    func = func.strip()
    simple = ''
    t = 0
    for c in func:
        if c=='<':
            if t==0:
                simple += '<...>'
            t += 1
        elif c=='>':
            t -= 1
        elif t==0:
            simple += c
    return simple
        
class node:

    count = 0
    processed = 0
    printed = 0

    def __init__(self):
        self.filters = []
        self.count = 0
        self.counts = collections.defaultdict(float)
        self.min_count = None
        self.max_count = None
        self.children = {}
        node.count += 1

    def _add_func(self, func, t, count=1):
        if not opt.templates:
            func = simplify_templates(func)
        if not func in self.children:
            self.children[func] = node()
        child = self.children[func]
        child.count += count
        child.counts[t] += count
        return child

    def add_stack(self, stack, t, extra=None, state=None, count=1):
        if stack:
            if extra:
                stack.append(extra)
            stack.reverse()
            if state:
                stack.append(state)
            if opt.reverse:
                stack.append('LEAF')
                stack.reverse()
            for f in self.filters:
                f(stack)
            n = self # root
            n.count += count
            self.counts[t] += count
            for func in stack:
                n = n._add_func(func, t, count)
        return []

    def prt(self, pfx=''):

        if node.printed>0 and node.printed%1000==0:
            msg('printed %d nodes (%0.f%%)' % (node.printed, node.printed*100/node.count))
        node.printed += 1

        # prune
        if len(pfx) > opt.max_depth:
            return

        # format for avg and max
        fmt = opt.fmt + ' ' + opt.fmt + ' '

        # children in order sorted by count
        children = sorted(self.children, key=lambda c: self.children[c].count, reverse=True)
        for i, func in enumerate(children):
            child = self.children[func]

            # avg, max counts for this node
            avg_count = child.avg_count
            max_count = child.max_count

            # tree lines
            if pfx and i<len(children)-1: p = opt.tree_mid
            elif pfx and i>0: p = opt.tree_last
            else: p = ' '
            pc = opt.tree_line if pfx and i<len(children)-1 else ' '

            # print the info
            put('%7s %7s ' % ((opt.fmt%avg_count)[0:7],( opt.fmt%max_count)[0:7]))
            graph_child(func, child)
            put(pfx+p)
            elt('span', {'id':'t%d' % opt.html_id, 'onClick':'hide(%d)'% opt.html_id})
            put_html(html_down)
            end('span')
            elt('span', {'onClick':'hide_all(%d)' % opt.html_id})
            if opt.html:
                func = cgi.escape(func)
            put(func)
            end('span')
            put('\n')
            elt('div', {'id':str(opt.html_id)})
            opt.html_id += 1
            child.prt(pfx+pc)
            end('div')

    # compute opt.max_count to scale all graphs to max_count
    def pre_graph(self):

        if node.processed>0 and node.processed%1000==0:
            msg('processed %d nodes (%0.f%%)' % (node.processed, node.processed*100/node.count))
        node.processed += 1

        for func in self.children:
            child = self.children[func]
            if opt.buckets:
                bcounts = collections.defaultdict(int)
                for t in child.counts.keys():
                    bt = bucket_time(t)
                    bcounts[bt] += float(child.counts[t]) / opt.samples_per_t[bt]
                child.counts = bcounts
            child.min_count = 0
            child.max_count = max(child.counts.values())
            child.avg_count = float(sum(child.counts[t] for t in opt.times)) / len(opt.times)
            for t in child.counts:
                if opt.graph_scale=='log':
                    c = child.counts[t]
                    c = max(math.log(c)+2,0) if c else 0
                    child.counts[t] = c
                    opt.min_count = 0
                    opt.max_count = max(opt.max_count, c)
                elif opt.graph_scale=='common':
                    opt.min_count = 0
                    opt.max_count = max(opt.max_count, child.counts[t])
            child.pre_graph()

def bucket_time(t):
    s0 = t - opt.t0
    s1 = s0 // opt.buckets * opt.buckets
    return t + (s1-s0)

def just_filter(pattern):
    def f(stack):
        s = stack_sep.join(stack)
        if not re.search(pattern, s):
            del stack[:]
    return f

stack_sep = ','

# xxx not working yet
def hide_filter(arg):
    parts = arg.split('/')
    pattern = parts[0]
    repl = parts[1] if len(parts)>1 else lambda m: '..' * m.string.count(stack_sep)
    def f(stack):
        s = stack_sep.join(stack)
        s = re.sub(pattern, repl, s)
        stack[:] = s.split(stack_sep)
    return f

#
# maintain times internally relative to t0
#

def f2t(f):
    return t0 + timedelta(seconds=f)

def t2f(t):
    return (t-t0).total_seconds()

def get_time(t):
    t = dateutil.parser.parse(t)
    if not t.tzinfo:
        tz = datetime(*time.gmtime()[:6]) - datetime(*time.localtime()[:6])
        t = pytz.utc.localize(t+tz)
    return t2f(t)

#
#
#

def progress(f, every=10000):

    # start time
    t = time.time()

    # file size for % msgs
    try:
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)
    except Exception as e:
        dbg('no size:', e)
        size = None

    # enumerate lines
    for n, line in enumerate(f):
        yield line
        if n>0 and n%every==0:
            s = 'processed %d lines' % n
            if size:
                s += ' (%d%%)' % (100.0*f.tell()/size)
            msg(s)

    # final stats
    t = time.time() - t
    dbg('%d lines, %.3f s, %d lines/s' % (n, t, n/t))



#
# read folded stacks
#

def read_folded(filters):

    root = node()
    root.filters = filters
    first = True
    freq = None
    time_field = 0
    metric_field = 1
    stack_field = 2
    state_field = None
    times = set()

    # start time for fp time values as specified in .folded file
    # we provide an arbitrary default value in case start isn't specified
    start = dateutil.parser.parse('2000-01-01T00:00:00Z')

    for line in progress(sys.stdin):
        line = line.strip()
        if not line: continue
        fields = line.split(';')
        if line.startswith('#'):
            for nv in line[1:].split():
                n, v = nv.split('=')
                if n=='freq': freq = float(v)
                elif n=='metric': opt.name = v
                elif n=='format': opt.fmt = v
                elif n=='start': start = dateutil.parser.parse(v)
        elif first:
            first = False
            for i, n in enumerate(fields):
                if n=='time': time_field = i
                elif n==opt.name: metric_field = i
                elif n=='stack': stack_field = i
                elif n=='state': state_field = i
        else:
            t = float(fields[time_field]) # relative to start
            t += (start-t0).total_seconds() # now relative to t0
            if t>=opt.after and t<opt.before:
                count = float(fields[metric_field])
                state = fields[state_field] if state_field is not None else ''
                root.add_stack(fields[-1:stack_field-1:-1], t, count=count, state=state)
                times.add(t)
                opt.traces += 1
                opt.tmin = min(t, opt.tmin) if opt.tmin else t
                opt.tmax = max(t, opt.tmax) if opt.tmax else t

    # compute distinct times
    opt.times = list(sorted(times))
    opt.samples = opt.traces if freq else len(opt.times)

    # bucketed times
    if opt.buckets:
        opt.t0 = min(opt.times)
        opt.samples_per_t = collections.defaultdict(float)
        for t in opt.times:
            if freq:
                opt.samples_per_t[bucket_time(t)] = freq * opt.buckets 
            else:
                opt.samples_per_t[bucket_time(t)] += 1

    return root


#
# time series graphs
#

def graph(ts=None, ys=None, ymin=None, ymax=None, shaded=True):
    graphing.html_graph(
        data=[(ts, ys, 'black')] if ts else [],
        tmin=opt.tmin, tmax=opt.tmax, width=opt.graph_width,
        ymin=ymin, ymax=ymax, height=1.1, ticks=opt.graph_ticks,
        shaded=shaded
    )

def graph_child(func, child):
    if opt.graph_width:
        times = opt.times
        ymin = child.min_count if opt.graph_scale=='separate' else opt.min_count
        ymax = child.max_count if opt.graph_scale=='separate' else opt.max_count
        if func=='+S': shaded = 'shaded-cold'
        elif func=='+R': shaded = 'shaded-hot'
        else: shaded = True
        graph(times, child.counts, ymin, ymax, shaded=shaded)

# read times series files
def read_series():
    if opt.series:
        opt.merges = True # xxx get from cmd line instead?
        opt.level = 0 # xxx get from cmd line instead?
        opt.progress_every = 1000 # xxx get from elsewhere?
        opt.relative = False
        series = [graph[0] for graph in graphing.get_graphs(opt.series, opt)]
        if not opt.tmin:
            opt.tmin = min(min(ts) for _, ts, _ in series)
            opt.tmax = max(max(ts) for _, ts, _ in series)
        return series

def graph_series(series):
    if series:
        put('avg.val max.val\n')
        for s in series:
            if s.ys.values():
                yavg = sum(s.ys.values()) / len(s.ys.values())
                put(('%7g'%yavg)[0:7], ' ', ('%7g'%s.ymax)[0:7], ' ')
                graph(s.ts, s.ys, 0, s.ymax)
                put(' ', s.name, '\n')
        put('\n')

#
#
#

def main():

    p = argparse.ArgumentParser()
    p.add_argument('--dbg', '-d', action='store_true')
    p.add_argument('--max-depth', '-m', type=int, default=float('inf'),
                   help='maximum stack depth to display')
    p.add_argument('--templates', '-t', action='store_true',
                   help='don\'t suppress C++ template args')
    p.add_argument('--no-line-numbers', '-l', action='store_true',
                   help='don\'t include line numbers in function names')
    p.add_argument('--just', '-j', action='append', default=[],
                   help='include only stacks matching this pattern')
    p.add_argument('--tree', '-e', choices=['utf-8', 'ascii', 'none'], default='utf-8',
                   help='tree lines can be drawn with utf-8 (default) or ascii, or can be omitted')
    p.add_argument('--after', '-a', default='1900-01-01T00:00:00',
                   help='include only samples at or after this time, in yyyy-mm-ddThh:mm:ss format')
    p.add_argument('--before', '-b', default='9999-01-01T00:00:00',
                   help='include only samples before this time, in yyyy-mm-ddThh:mm:ss format')
    p.add_argument('--buckets', type=float, default=None, help=
                   'group counts into buckets of the specified length, in floating point seconds')
    p.add_argument('--graph-width', type=int, default=20,
                   help='produce a graph with the specified width, in ems (0 to disable)')
    p.add_argument('--graph-scale', choices=['common', 'separate', 'log'], default='common')
    p.add_argument('--graph-ticks', type=int, default=5)
    p.add_argument('--text', action='store_true',
                   help='produce text instead of interactive html output')
    p.add_argument('--series', nargs='*', default=[])
    p.add_argument('--tz', type=float, nargs=1, default=None)
    p.add_argument('--threads', type=str, nargs='+', default=None)
    p.add_argument('--reverse', action='store_true')
    global opt
    opt = p.parse_args()

    filters = []
    for s in opt.just: filters.append(just_filter(s))
    #for s in opt.hide: filters.append(hide_filter(s))

    if opt.tree=='utf-8': opt.tree_line, opt.tree_mid, opt.tree_last = '│', '├', '└'
    elif opt.tree=='ascii': opt.tree_line, opt.tree_mid, opt.tree_last = '|', '+', '+'
    elif opt.tree=='none': opt.tree_line, opt.tree_mid, opt.tree_last = ' ', ' ', ' '

    if opt.tz==None:
        opt.tz = datetime(*time.localtime()[:6]) - datetime(*time.gmtime()[:6])
    else:
        opt.tz = timedelta(hours=opt.tz[0])

    opt.html = not opt.text
    if not opt.html:
        opt.graph_width = 0

    if opt.threads:
        opt.threads = set(opt.threads)

    opt.max_count = float('-inf')
    opt.min_count = float('inf')
    opt.tmin = None
    opt.tmax = None
    opt.times = []
    opt.samples = 0
    opt.traces = 0
    opt.html_id = 0
    opt.name = 'threads'
    opt.fmt = '%.2f'

    # import timeseries if we are generating graphs
    # we will maintain times internally relative to t0
    global graphing, util, html, t0
    if opt.series or opt.graph_width:
        sys.path.append('timeseries.src')
        import util
        import graphing
        import html
        t0 = util.t0
    else:
        t0 = dateutil.parser.parse('2000-01-01T00:00:00Z')

    # parse and adjust opt.after,before
    opt.after = get_time(opt.after)
    opt.before = get_time(opt.before)

    # read stuff
    root = read_folded(filters)
    series = read_series()

    # bucketize times
    if opt.buckets:
        i = 0
        b0 = min(opt.times)
        b1 = max(opt.times)
        opt.times = []
        for i in range(int((b1-b0) / opt.buckets) + 1):
            opt.times.append(b0 + i*opt.buckets)

    # canonical times
    opt.times = sorted(set(opt.times))

    # disable graph if only one sample
    if opt.samples < 2:
        opt.graph_width = 0

    # print result
    html_head()
    graph_series(series)
    put('%d samples\n' % opt.samples) # xxx report traces too
    root.pre_graph()
    put('%7.7s %7.7s  ' % ('avg.' + opt.name, 'max.' + opt.name))
    if opt.graph_width or opt.series: graph()
    put('call tree\n' if not opt.reverse else 'reverse call tree\n')
    root.prt()
    html_foot()

    msg('start:', f2t(opt.tmin))
    msg('finish:', f2t(opt.tmax))

main()
