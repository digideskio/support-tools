#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import datetime
import collections

html_down = '▽ '
html_right = '▷ '

#html_down = 'v '
#html_right = '> '

html_head = '''
<html>
  <head>
    <meta charset="utf-8"/>
    <script>
      function toggle(ctl, e) {
          if (ctl!='none') {
              e.style.display = 'none'
              document.getElementById('t'+e.id).innerHTML = '%s'
          } else {
              e.style.display = 'block'
              document.getElementById('t'+e.id).innerHTML = '%s'
          }
      }
      function hide(i) {
          var e = document.getElementById(i)
          toggle(e.style.display, e)
      }
      function hidec(i) {
          var children = document.getElementById(i).childNodes
          var ctl = undefined
          for (var i in children) {
              var c = children[i]
              if (c.tagName=='DIV') {
                  if (!ctl)
                      ctl = children[i].style.display
                  toggle(ctl, c)
              }
          }
      }
    </script>
    <style>
      pre {
        font-family: menlo, "lucida console", courier, fixed;
        font-size: 8pt;
      }
      body {
        font-family: sans-serif;
        font-size: 9pt
      }
    </style>
  </head
  <body>
    Click on a triangle to open or close an item.<br/>
    Click on a function name to open or close all children of that function
    <pre>
''' % (html_right, html_down)

html_foot = '''
    </pre>
  </body
</html>
'''


class node:

    def __init__(self):
        self.filters = []
        self.count = 0
        self.counts = collections.defaultdict(int)
        self.bins = collections.defaultdict(int)
        self.children = {}

    def add_func(self, func, t, o):
        if not func in self.children:
            self.children[func] = node()
        child = self.children[func]
        child.count += 1
        child.counts[t] += 1
        return child

    def add_stack(self, stack, t, o):
        if stack:
            stack.reverse()
            for f in self.filters:
                f(stack)
            n = self # root
            n.count += 1
            for func in stack:
                n = n.add_func(func, t, o)
        return []

    def prt(self, samples, pfx, o):

        # prune
        if len(pfx) > o.max_depth:
            return

        # children in order sorted by count
        children = sorted(self.children, key=lambda c: self.children[c].count, reverse=True)
        for i, func in enumerate(children):
            child = self.children[func]

            # avg number of threads
            thr = float(child.count) / samples

            # tree lines
            if pfx and i<len(children)-1: x = o.tree_mid
            elif pfx and i>0: x = o.tree_last
            else: x = ' '
            xc = o.tree_line if pfx and i<len(children)-1 else ' '

            # graph over time for this call site
            if o.graph:
                bars = u' ▁▂▃▄▅▆▇█'
                height = lambda count: int(float(count) / (o.max_bin*(1+1e-10)) * len(bars))
                graph = ''.join(bars[height(child.bins[i])] for i in range(o.graph))
            else:
                graph = ''

            if o.html:
                h1 = '<span id="t%d" onClick="hide(%d)">%s</span><span onClick="hidec(%d)">' % \
                     (o.html_id, o.html_id, html_down, o.html_id)
                h2 = '</span>\n<div id="%d">' % o.html_id
                o.html_id += 1
            else:
                h1 = ''
                h2 = '\n'

            # print the info
            sys.stdout.write('%5d %6.2f %s%s%s%s%s' % \
                (child.count, thr, graph.encode('utf-8'), pfx+x, h1, func, h2))

            # recursively print children
            child.prt(samples, pfx+xc, o)
            if o.html:
                sys.stdout.write('</div>')


    # divide counts into bins, and compute o.max_bin to scale all graphs to max_bin
    def graph(self, o):
        interval = (o.tmax - o.tmin).total_seconds() * (1+1e-10) / o.graph
        for func in self.children:
            child = self.children[func]
            for t in child.counts:
                bin = int((t - o.tmin).total_seconds() / interval)
                child.bins[bin] += child.counts[t]
                o.max_bin = max(o.max_bin, child.bins[bin])
            child.graph(o)

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
    p.add_argument('--html', action='store_true',
                   help='produce interactive html output; save to file and open in browser')
    o = p.parse_args()

    root = node()
    for s in o.just: root.filters.append(just_filter(s))
    #for s in o.hide: root.filters.append(hide_filter(s))

    if o.tree=='utf-8': o.tree_line, o.tree_mid, o.tree_last = '│', '├', '└'
    elif o.tree=='ascii': o.tree_line, o.tree_mid, o.tree_last = '|', '+', '+'
    elif o.tree=='none': o.tree_line, o.tree_mid, o.tree_last = ' ', ' ', ' '

    o.after = o.after.replace('T', ' ')
    o.before = o.before.replace('T', ' ')
    o.after = datetime.datetime.strptime(o.after, '%Y-%m-%d %H:%M:%S')
    o.before = datetime.datetime.strptime(o.before, '%Y-%m-%d %H:%M:%S')

    o.max_bin = 0
    o.tmin = None
    o.tmax = None

    samples = 0
    stack = []
    t = None
    for line in sys.stdin:
        if line.startswith('==='):
            stack = root.add_stack(stack, t, o)
            t = line.split()[1]
            t = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%f')
            if t>=o.after and t<o.before:
                samples += 1
                o.tmin = min(t, o.tmin) if o.tmin else t
                o.tmax = max(t, o.tmax) if o.tmax else t
            if o.dbg: print 'after', o.after, 't', t, 'before', o.before
        elif line.startswith('#') and t>=o.after and t<o.before:
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
                if o.dbg:
                    print line.strip()
                    print m.groups()
                level, func, args, from_file, at_file, at_ln = m.groups()
                if level=='0':
                    stack = root.add_stack(stack, t, o)
                func = func.strip()
                if not o.templates: func = simplify(func)
                if at_ln and not o.no_line_numbers: func += ':' + at_ln
                stack.append(func)
    root.add_stack(stack, t, o)

    # print result
    if o.html:
        print html_head
        o.html_id = 0
    print '%d samples, %d traces, %.2f threads' % (samples, root.count, float(root.count)/samples)
    print 'count    thr  %sstack' % (' ' * o.graph)
    if o.graph:
        root.graph(o)
    root.prt(samples, '', o)
    if o.html:
        print html_foot

main()
