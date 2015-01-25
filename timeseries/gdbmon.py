#!/usr/bin/python

import datetime
import itertools
import os
import signal
import subprocess
import sys
import time
import optparse
import select


print ' '.join(sys.argv)
sys.stdout.flush()

parser = optparse.OptionParser()
parser.add_option('--debug', '-d', action='store_true', dest='dbg')
o, args = parser.parse_args()
o.pid = int(args[0]) if len(args)>0 else None
o.delay = float(args[1]) if len(args)>1 else None
o.count = float(args[2]) if len(args)>2 else None

if not o.pid:
    print 'usage: gdbmon pid [delay [count]]'
    sys.exit(-1)

if not o.delay:
    o.count = 1

def dbg(*ss):
    if o.dbg:
        sys.stderr.write(' '.join(str(s) for s in ss) + '\n')

def put(cmd):
    if o.dbg: print >>sys.stderr, 'PUT', cmd
    gdb.stdin.write(cmd + '\n')

def get(response, show=False, timeout=None):
    dbg('GET', response)
    while True:
        rlist, _, _ = select.select([gdb.stdout], [], [], timeout)
        if not rlist:
            dbg('TIMEOUT')
            return None
        line = gdb.stdout.readline().strip()
        if line.startswith('^error'):
            raise Exception(line)
        elif line.startswith(response):
            dbg('GOT expected', len(line), line)
            return line[len(response)+1:]
        elif line.startswith('~'):
            if show:
                line = line[1:].strip('"').replace('\\n', '\n')
                print line,
        elif not line: # EOF - gdb terminated
            sys.exit(0)
        else:
            dbg('GOT unexpected', line)
            pass

cmd = ['gdb', '-p', str(o.pid), '--interpreter=mi']
gdb = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

put('cont')
get('^running')

for i in itertools.count():
    if o.delay: time.sleep(o.delay)
    t0 = time.time()
    while True: # timeout and retry handles race condition btw thread starts and SIGTRAP
        dbg('SIGTRAP')
        os.kill(int(o.pid), signal.SIGTRAP)
        if get('*stopped', timeout=1):
            break
    t1 = time.time()
    sys.stdout.write(datetime.datetime.utcnow().strftime('\n=== %FT%T.%f+0000 \n'))
    put('thread apply all bt')
    get('^done', True)
    t2 = time.time()
    if o.count and i==o.count-1:
        break
    dbg('cont')
    put('cont')
    get('^running')
    t3 = time.time()
    print '\ntimes: stop %.3f traces %.3f cont %.3f' % (t1-t0, t2-t1, t3-t2)
    sys.stdout.flush()
