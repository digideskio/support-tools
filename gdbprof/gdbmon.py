#!/usr/bin/python

import datetime
import itertools
import os
import signal
import subprocess
import sys
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--debug', '-d', action='store_true', dest='dbg')
parser.add_argument('pid', type=int)
parser.add_argument('delay', type=float, nargs='?')
parser.add_argument('count', type=int, nargs='?')
o = parser.parse_args()

if not o.delay:
    o.count = 1

cmd = ['gdb', '-p', str(o.pid), '--interpreter=mi']
gdb = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def put(cmd):
    if o.dbg: print >>sys.stderr, 'PUT', cmd
    gdb.stdin.write(cmd + '\n')

def get(response, show=False):
    if o.dbg: print >>sys.stderr, 'GET', response
    while True:
        line = gdb.stdout.readline().strip()
        if line.startswith('^error'):
            raise Exception(line)
        elif line.startswith(response):
            if o.dbg: print >>sys.stderr, 'GOT expected', len(line), line
            return line[len(response)+1:]
        elif line.startswith('~'):
            if show:
                line = line[1:].strip('"').replace('\\n', '\n')
                print line,
        else:
            if o.dbg: print >>sys.stderr, 'GOT unexpected', line
            pass

put('cont')
get('^running')

for i in (range(o.count) if o.count else itertools.count()):
    if o.delay: time.sleep(o.delay)
    if o.dbg: print >>sys.stderr, 'SIGSTOP'
    os.kill(int(o.pid), signal.SIGSTOP)
    get('*stopped')
    sys.stdout.write(datetime.datetime.now().strftime('=== %FT%T.%f \n'))
    put('thread apply all bt')
    get('^done', True)
    if o.dbg: print >>sys.stderr, 'SIGCONT'
    os.kill(int(o.pid), signal.SIGCONT)
    put('cont')
    sys.stdout.flush()
    get('^running')
