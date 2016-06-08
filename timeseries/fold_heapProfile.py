import sys
import json
import dateutil.parser

t0 = dateutil.parser.parse('1970-01-01T00:00:00Z')

print '# metric=MB format=%.3f'
print 'time;MB;stack'

for line in sys.stdin:
    try:
        j = json.loads(line)
        t = (dateutil.parser.parse(j['localTime'])-t0).total_seconds()
        stacks = j['heapProfile']['stacks']
        for _, stackInfo in stacks.items():
            stack = stackInfo['stack']
            s = ';'.join(stack[str(k)] for k in reversed(range(len(stack))))
            ab = stackInfo['activeBytes']
            if type(ab)==dict:
                ab = ab['floatApprox']
            mb = float(ab) / (1024*1024)
            print '%s;%s;%s' % (t, mb, s)
    except ValueError:
        pass
