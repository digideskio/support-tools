import re
import sys

stack = []
trace = 0

def put():
    global stack
    if stack:
        print str(trace) + ';1;' + ';'.join(reversed(stack))
        stack = []

print 'time;count;stack'

for line in sys.stdin:

    m = re.match('[. ]+(\d+) +Id: ', line)
    if m:
        if m.group(1)=='0':
            put()
            trace += 1

    m = re.match('Child-SP', line)
    if m:
        put()

    #m = re.match('(?: | \*)([0-9]+) +([^\(]+)\(.*', line)
    #000000d1`19c9e530 00007ff7`18b6a428 KERNELBASE!WaitForMultipleObjectsEx+0xe1
    m = re.match('[0-9a-f]+`[0-9a-f]+ [0-9a-f]+`[0-9a-f]+ ([^+]+)', line)
    if m:
        stack.append(m.group(1).strip())

put()
