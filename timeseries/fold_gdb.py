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


#
# process gdb stack samples into a form
# that can be visualized by the calltree tool
#

sep = ';'
start = None

def get_time(t):
    t = dateutil.parser.parse(t)
    if not t.tzinfo:
        tz = datetime(*time.gmtime()[:6]) - datetime(*time.localtime()[:6])
        t = pytz.utc.localize(t+tz)
    return t

def msg(*s):
    print >>sys.stderr, ' '.join(s) 

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
        
def read_gdb(f):

    stack = []
    t = None

    plevel = '^#([0-9]+) +'
    paddr = '(?:0x[0-9a-f]+ in )?'
    pfunc = '((?:[^(]|\(anonymous namespace\))+)'
    pargs = '.*?'
    #pfunc = '((?:[^)]|\)[^ ])*)'
    #pargs = '((?: ?\(.*\) ?)+ *)'
    pfile = '(?:at (.*):([0-9]+))? ?(?:from (.*)|)?\n$'
    pat = plevel + paddr + pfunc + pargs + pfile
    pat = re.compile(pat)
    
    def print_stack(stack, t, state):
        global start
        if not start:
            start = t
            print '# metric=threads format=%%.2f start=%s' % start.isoformat()
            print 'time;threads;state;stack'
        t = (t-start).total_seconds()
        print str(t) + sep + '1' + sep + state + sep + sep.join(reversed(stack))
        return []

    for line in f:
        if line.startswith('==='):
            if stack:
                stack = print_stack(stack, t, states[lwp])
            states = collections.defaultdict(str)
            t = line.split()[1]
            t = get_time(t)
        elif line.startswith('state:'):
            for f in line.split()[1:]:
                l, s = f.split('=')
                states[l] = '+' + s
        elif line.startswith('Thread'):
            if stack:
                stack = print_stack(stack, t, states[lwp])
            m = re.search('LWP ([0-9]+)', line)
            lwp = m.group(1)
        elif line.startswith('#'):
            m = pat.match(line)
            if not m:
                msg('not matched:', repr(line))
            else:
                #level, func, args, at_file, at_ln, from_file = m.groups()
                level, func, at_file, at_ln, from_file = m.groups()
                func = func.strip()
                func = simplify(func)
                if at_ln:
                    func += ':' + at_ln
                stack.append(func)

    # last one
    if stack:
        print_stack(stack, t, states[lwp])

read_gdb(sys.stdin)
