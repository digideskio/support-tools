#!/usr/bin/python

import sys
import re
import argparse

class node:

    def __init__(self):
        self.filters = []
        self.count = 0
        self.children = {}

    def add_func(self, func):
        if not func in self.children:
            self.children[func] = node()
        child = self.children[func]
        child.count += 1
        return child

    def add_stack(self, stack):
        stack.reverse()
        for f in self.filters:
            f(stack)
        n = self # root
        n.count += 1
        for func in stack:
            n = n.add_func(func)

    def prt(self, samples, level=0, max_depth=float('inf')):
        if level > max_depth:
            return
        for func in sorted(self.children, key=lambda c: self.children[c].count, reverse=True):
            child = self.children[func]
            thr = float(child.count) / samples
            print '%5d %6.2f %s %s' % (child.count, thr, ' ' * level, func)
            child.prt(samples, level+1)

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
    #p.add_argument('--debug', '-d', action='store_true', dest='dbg')
    p.add_argument('--max-depth', '-m', dest='max_depth', type=int, default=float('inf'),
                   help='maximum stack depth to display')
    p.add_argument('--templates', '-t', action='store_true',
                   help='don\'t suppress C++ template args')
    p.add_argument('--no-line-numbers', '-n', dest='no_line_numbers', action='store_true',
                   help='don\'t include line numbers in function names')
    p.add_argument('--just', '-j', dest='just', action='append', default=[],
                   help='include only stacks matching this pattern')
    o = p.parse_args()

    root = node()
    for s in o.just: root.filters.append(just_filter(s))
    #for s in o.hide: root.filters.append(hide_filter(s))

    samples = 0
    stack = []
    for line in sys.stdin:
        if line.startswith('==='):
            samples += 1
        elif line.startswith('#'):
            pat = '^#([0-9]+) +(?:0x[0-9a-f]+ in )?(.*) \(.* (?:from (.*)|at (.*):([0-9]+))\n?$'
            m = re.match(pat, line)
            if not m:
                print 'not matched:', repr(line)
            else:
                level, func, from_file, at_file, at_ln = m.groups()
                if level=='0' and stack:
                    root.add_stack(stack)
                    stack = []
                if not o.templates: func = simplify(func)
                if at_ln and not o.no_line_numbers: func += ':' + at_ln
                stack.append(func)
    if stack:
        root.add_stack(stack)

    # print result
    print '%d samples, %d traces, %.2f threads' % (samples, root.count, float(root.count)/samples)
    print 'count    thr  stack'
    root.prt(samples, max_depth=o.max_depth)

main()
