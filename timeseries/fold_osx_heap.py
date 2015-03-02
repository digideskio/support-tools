#
# processes call trees produced by osx malloc_history
# into "folded" form that can be accepted by calltree tool (aka gdbprof)
#

import sys
import re

pat = '([^0-9]+) ([0-9]+) \(([^)]+)\) ([^(]+)'
pat = re.compile(pat)
stack = ['ROOT']

print '# metric=MB format=%.3f'
print 'time;MB;stack'

def leaf():
    print '0;' + str(last_size/1024/1024) + ';' + ';'.join(stack)

for line in sys.stdin:
    m = pat.match(line)
    if m:
        level = (len(m.group(1))-3) / 2
        count = int(m.group(2))
        size = m.group(3)
        if size.endswith('M'): size = float(size[:-1]) * 1024 * 1024
        elif size.endswith('K'): size = float(size[:-1]) * 1024
        else: size = float(size)
        fun = m.group(4).strip()
        if level >= len(stack):
            stack.append(fun)
        elif level >= 1:
            leaf()
            stack = stack[0:level]
            stack.append(fun)
        last_size = size

leaf()
