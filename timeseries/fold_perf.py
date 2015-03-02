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
# process the output of perf cpu profile statistics into a form
# that can be visualized by the calltree tool
#

first = True
add_total = False
t0 = None
captured = None
stacks = []
stack = []

sep = ';'

def get_time(t):
    t = dateutil.parser.parse(t)
    if not t.tzinfo:
        tz = datetime(*time.gmtime()[:6]) - datetime(*time.localtime()[:6])
        t = pytz.utc.localize(t+tz)
    return t

def output_sample(stack, t, proc):
    stack.append(proc)
    stacks.append((stack, t))

def print_samples(captured, t0, t):
    start = captured - timedelta(0, t - t0)
    print '# metric=threads format=%%.2f freq=%g start=%s' % (freq, start.isoformat())
    print 'time;threads;stack'
    for stack, t in stacks:
        if add_total:
            stack.append('TOTAL')
        print str(t-t0) + sep + '1' + sep + sep.join(reversed(stack))

for line in sys.stdin:
    line = line[:-1]
    start_marker = '# captured on: '
    if line.startswith(start_marker): # comment with start time
        if not captured:
            captured = get_time(line[len(start_marker):])
    elif line.startswith('# cmdline'):
        m = re.search('-F ?([0-9]+)', line)
        if m:
            freq = float(m.groups()[0])
        if '-a' in line:
            add_total = True
    elif line.startswith('#'): # comment
        pass
    elif line.startswith('\t'): # line of a stack trace
        func = re.split('[ \t(<]+', line)[2]
        if func != '[unknown]':
            stack.append(func)
    elif line: # start of stack trace
        if stack:
            output_sample(stack, t, proc)
        stack = []
        proc = line.split()[0]
        fields = line.split()
        t = fields[3] if fields[2].startswith('[') else fields[2]
        t = float(t[:-1])
        if not t0:
            t0 = t


# last one
output_sample(stack, t, proc)

# print them
print_samples(captured, t0, t)
