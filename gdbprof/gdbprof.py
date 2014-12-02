#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import datetime
import collections
import math
import os
import json


#
# html stuff
#

html_down = '▽ '
html_right = '▷ '

def elt(name, **attrs):
    if opt.html:
        sys.stdout.write('<%s' % name)
        for a in attrs:
            sys.stdout.write(' %s="%s"' % (a, attrs[a]))
        sys.stdout.write('>')

def eltend(name, **attrs):
    if opt.html:
        elt(name, **attrs)
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

def html_head():
    elt('html')
    elt('head')
    elt('meta', charset='utf-8')
    elt('script')
    html(html_script % (html_right, html_down))
    end('script')
    elt('style')
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
'''

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

#
# time series graph
#

def graph(ts=None, ys=None, ymin=None, ymax=None):
    if opt.graph:
        elt('svg', width='%dem' % opt.graph, height='1.1em', viewBox='0 0 %d 1.1' % opt.graph)
        if ts:
            tspan = (opt.tmax-opt.tmin).total_seconds()
            yspan = (ymax - ymin)* (1+1e-10)
            if yspan==0:
                ymin -= 1
                yspan = 1
            gx = lambda t: (t-opt.tmin).total_seconds() / tspan * opt.graph
            gy = lambda y: (1.0 - (float(y)-ymin) / yspan) * 0.95 + 0.05
            line = ' '.join('%g,%g' % (gx(t), gy(ys[t])) for t in ts)
            shade = '0,1.05 ' + line + ' %d,1.05' % opt.graph
            eltend('polygon', points=shade, style='fill:rgb(230,230,230); stroke:none;')
            eltend('polyline', points=line, style='fill:none; stroke:black; stroke-width:0.1')
            for i in range(opt.graph_ticks+1):
                x = opt.graph * i / opt.graph_ticks
                style = 'stroke:rgba(255,0,0,0.2); stroke-width:0.1'
                eltend('line', x1=x, x2=x, y1=0, y2=1, style=style)
        eltend('line', x1=0, x2=1, y1=0, y2=1, style='stroke:red, stroke-width:10')
        end('svg')

def graph_child(opt, child):
    ymin = child.min_count if opt.graph_scale=='separate' else opt.min_count
    ymax = child.max_count if opt.graph_scale=='separate' else opt.max_count
    graph(opt.times, child.counts, ymin, ymax)


#
# call tree
#

class node:

    def __init__(self):
        self.filters = []
        self.count = 0
        self.counts = collections.defaultdict(int)
        self.min_count = None
        self.max_count = None
        self.bins = collections.defaultdict(int)
        self.children = {}

    def add_func(self, func, t):
        if not func in self.children:
            self.children[func] = node()
        child = self.children[func]
        child.count += 1
        child.counts[t] += 1
        return child

    def add_stack(self, stack, t):
        if stack:
            stack.reverse()
            for f in self.filters:
                f(stack)
            n = self # root
            n.count += 1
            for func in stack:
                n = n.add_func(func, t)
        return []

    def prt(self, pfx=''):

        # prune
        if len(pfx) > opt.max_depth:
            return

        # children in order sorted by count
        children = sorted(self.children, key=lambda c: self.children[c].count, reverse=True)
        for i, func in enumerate(children):
            child = self.children[func]

            # avg number of threads
            avg_thr = float(child.count) / opt.samples
            max_thr = child.max_count

            # tree lines
            if pfx and i<len(children)-1: p = opt.tree_mid
            elif pfx and i>0: p = opt.tree_last
            else: p = ' '
            pc = opt.tree_line if pfx and i<len(children)-1 else ' '

            # print the info
            put('%7.2f %7.2f ' % (avg_thr, max_thr))
            graph_child(opt, child)
            put(pfx+p)
            elt('span', id='t%d' % opt.html_id, onClick='hide(%d)'% opt.html_id)
            html(html_down)
            end('span')
            elt('span', onClick='hide_all(%d)' % opt.html_id)
            put(func)
            end('span')
            put('\n')
            elt('div', id=str(opt.html_id))
            opt.html_id += 1
            child.prt(pfx+pc)
            end('div')

    # compute opt.max_count to scale all graphs to max_count
    def pre_graph(self):
        for func in self.children:
            child = self.children[func]
            child.min_count = 0
            child.max_count = max(child.counts.values())
            for t in child.counts:
                if opt.graph_scale=='log':
                    c = child.counts[t]
                    c = math.log(c)+2 if c else -10
                    child.counts[t] = c
                    opt.min_count = 0
                    opt.max_count = max(opt.max_count, c)
                elif opt.graph_scale=='common':
                    opt.min_count = 0
                    opt.max_count = max(opt.max_count, child.counts[t])
            child.pre_graph()

def simplify(func):
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
# time series
#

def op_for(fmt, s):
    if s=='max': return lambda ys, t, d: max(ys[t], d)
    if s=='count':
        count_min_ms = float(fmt.get("count_min_ms", 0))
        return lambda ys, t, d: ys[t]+1 if d>=count_min_ms else ys[t]

def series_one(formats, series):

    fmt_name, fn = series.split(':',2)
    fmt_name_params = fmt_name.split('(')
    fmt_name = fmt_name_params[0]
    fmt = formats[fmt_name]
    if len(fmt_name_params)>1:
        params = fmt_name_params[1].strip(' )')
        params = params.split(',')
        for p in params:
            n, v = p.split('=')
            fmt[n] = v
    description = fmt.get('description', fmt_name).format(**fmt)

    delta = fmt.get('delta', False)
    if delta:
        last_t = None

    buckets = float(fmt.get('bucket_size', 0))
    if buckets:
        t0 = dateutil.parser.parse('2000-01-01')
        op = op_for(fmt, fmt['bucket_op'])

    queue = fmt.get('queue', False)
    if queue:
        queue_times = []
        queue_min_ms = float(fmt.get('queue_min_ms', 0))

    ts = []
    ys = collections.defaultdict(int)

    for line in open(fn):
        line = line.strip()
        m = re.search(fmt['re'], line)
        if m:
            t, d = m.groups()
            t, d = dateutil.parser.parse(t), float(d)
            if delta:
                if last_t:
                    ts.append(t)
                    ys[t] = (d-last_d) / (t-last_t).total_seconds()
                last_t = t
                last_d = d
            elif buckets:
                s0 = (t - t0).total_seconds()
                s1 = s0 // buckets * buckets
                t = t + datetime.timedelta(0, s1-s0)
                ys[t] = op(ys, t, d)
            elif queue:
                if d>queue_min_ms:
                    ms = datetime.timedelta(0, d/1000.0)
                    queue_times.append((t-ms,+1))
                    queue_times.append((t,-1))
            else:
                ts.append(t)
                ys[t] = d

    if buckets:
        tmin = min(ys.keys())
        tmax = max(ys.keys())
        n = int((tmax-tmin).total_seconds() / buckets)
        dt = datetime.timedelta(0, buckets)
        ts = [tmin + dt*i for i in range(n+1)]
    elif queue:
        q = 0
        for t, d in sorted(queue_times):
            q += d
            ys[t] = q
            ts.append(t)

    return description, ts, ys

def series_load(formats, fn):
    if opt.dbg: print >>sys.stderr, '===', fn
    try:
        for fmt in json.load(open(fn)):
            if opt.dbg: print >>sys.stderr, fmt['name']
            formats[fmt['name']] = fmt
    except Exception as e:
        if opt.dbg:
            print >>sys.stderr, e

def series_all():
    global dateutil
    import dateutil.parser
    formats = {}
    series_load(formats, os.path.join(os.path.dirname(__file__), 'timeseries.json'))
    series_load(formats, 'timeseries.json')
    return [series_one(formats, s) for s in opt.series]

def series_prt(series):
    if series:
        put('avg.val max.val\n')
        for label, ts, ys in series:
            ymax = max(ys.values())
            yavg = float(sum(ys.values())) / len(ys)
            put('%7g %7g ' % (yavg, ymax))
            graph(ts, ys, 0, ymax)
            put(' ', label, '\n')
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
    p.add_argument('--graph', '-g', type=int, default=0,
                   help='produce a graph with the specified number of buckets')
    p.add_argument('--graph-scale', choices=['common', 'separate', 'log'], default='common')
    p.add_argument('--graph-ticks', type=int, default=5)
    p.add_argument('--html', action='store_true',
                   help='produce interactive html output; save to file and open in browser')
    p.add_argument('--series', nargs='*', default=[])
    global opt
    opt = p.parse_args()

    root = node()
    for s in opt.just: root.filters.append(just_filter(s))
    #for s in opt.hide: root.filters.append(hide_filter(s))

    if opt.tree=='utf-8': opt.tree_line, opt.tree_mid, opt.tree_last = '│', '├', '└'
    elif opt.tree=='ascii': opt.tree_line, opt.tree_mid, opt.tree_last = '|', '+', '+'
    elif opt.tree=='none': opt.tree_line, opt.tree_mid, opt.tree_last = ' ', ' ', ' '

    opt.after = opt.after.replace('T', ' ')
    opt.before = opt.before.replace('T', ' ')
    opt.after = datetime.datetime.strptime(opt.after, '%Y-%m-%d %H:%M:%S')
    opt.before = datetime.datetime.strptime(opt.before, '%Y-%m-%d %H:%M:%S')

    opt.max_count = float('-inf')
    opt.min_count = float('inf')
    opt.tmin = None
    opt.tmax = None
    opt.times = []
    opt.samples = 0
    opt.html_id = 0

    # profile
    stack = []
    t = None
    for line in sys.stdin:
        if line.startswith('==='):
            stack = root.add_stack(stack, t)
            t = line.split()[1]
            t = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%f')
            if t>=opt.after and t<opt.before:
                opt.times.append(t)
                opt.samples += 1
                opt.tmin = min(t, opt.tmin) if opt.tmin else t
                opt.tmax = max(t, opt.tmax) if opt.tmax else t
            if opt.dbg: print 'after', opt.after, 't', t, 'before', opt.before
        elif line.startswith('#') and t>=opt.after and t<opt.before:
            plevel = '^#([0-9]+) +'
            paddr = '(?:0x[0-9a-f]+ in )?'
            pfunc = '((?:[^)]|\)[^ ])*)'
            pargs = '((?: ?\(.*\) ?)+ *)'
            pfile = '(?:from (.*)|at (.*):([0-9]+))?\n$'
            pat = plevel + paddr + pfunc + pargs + pfile
            m = re.match(pat, line)
            if not m:
                print 'not matched:', repr(line)
            else:
                if opt.dbg:
                    print line.strip()
                    print m.groups()
                level, func, args, from_file, at_file, at_ln = m.groups()
                if level=='0':
                    stack = root.add_stack(stack, t)
                func = func.strip()
                if not opt.templates: func = simplify(func)
                if at_ln and not opt.no_line_numbers: func += ':' + at_ln
                stack.append(func)
    root.add_stack(stack, t)

    # read times series files
    series = series_all()
    if not opt.tmin:
        opt.tmin = min(min(ts) for _, ts, _ in series)
        opt.tmax = max(max(ts) for _, ts, _ in series)

    # print result
    html_head()
    series_prt(series)
    threads = float(root.count)/opt.samples if opt.samples else 0
    put('%d samples, %d traces, %.2f threads\n' % (opt.samples, root.count, threads))
    root.pre_graph()
    put('avg.thr max.thr  ')
    graph()
    put('call tree\n')
    root.prt()
    html_foot()

main()
