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

def html(s):
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
    html(html_script)
    end('script')
    elt('style')
    if opt.graph_width: html(timeseries.graph_style)
    html(html_style)
    end('style')
    end('head')
    elt('body')
    html(html_help)
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

    def __init__(self):
        self.filters = []
        self.count = 0
        self.counts = collections.defaultdict(float)
        self.min_count = None
        self.max_count = None
        self.children = {}

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
            html(html_down)
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
    s0 = (t - opt.t0).total_seconds()
    s1 = s0 // opt.buckets * opt.buckets
    return t + timedelta(0, s1-s0)

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

def get_time(t):
    t = dateutil.parser.parse(t)
    if not t.tzinfo:
        tz = datetime(*time.gmtime()[:6]) - datetime(*time.localtime()[:6])
        t = pytz.utc.localize(t+tz)
    return t

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

    # xxx use relative floats for times internally instead of dates
    start = dateutil.parser.parse('2000-01-01T00:00:00Z')

    for line in sys.stdin:
        fields = line.strip().split(';')
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
            t = float(fields[time_field])
            t = start + timedelta(0, t)
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
    timeseries.html_graph(
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
        series = [graph[0] for graph in timeseries.get_graphs(opt.series, opt)]
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

    def datetime_parse(t):
        t = dateutil.parser.parse(t)
        if not t.tzinfo:
            t = pytz.utc.localize(t+opt.tz)
        return t
    
    opt.after = get_time(opt.after)
    opt.before = get_time(opt.before)

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

    if opt.series or opt.graph_width:
        global timeseries
        import timeseries

    # read stuff
    root = read_folded(filters)
    series = read_series()

    # bucketize times
    if opt.buckets:
        i = 0
        t0 = min(opt.times)
        t1 = max(opt.times)
        opt.times = []
        for i in range(int((t1-t0).total_seconds() / opt.buckets) + 1):
            opt.times.append(t0 + timedelta(0, i*opt.buckets))

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

    msg('start:', opt.tmin)
    msg('finish:', opt.tmax)

main()
