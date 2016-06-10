import sys
import re
import collections

#
# process output of osx malloc_history into folded call stacks
# that can be visualized using the calltree tool
#

def msg(*ss):
    print >>sys.stderr, ' '.join(str(s) for s in ss)

# regexp for parsing lines
pat = '(ALLOC|FREE) +0x([0-9a-f]+)(?:-0x[0-9a-f]+ +\[size=([0-9]+)\])?: +(.*)'
pat = re.compile(pat)

# regexp for splitting function names
fun = '[(<]'
fun = re.compile(fun)

addrs = {}         # (size, allocating stack) for each addr
allocated = {}     # cumulative size for each stack
folded = {}        # stacks converted to folded form for output

total_size = 0
max_size = 0
last_size = 0

sep = ';'
MB = 1024.0 * 1024.0

# headers
print '# metric=MB format=%.3f'
print 'time;MB;stack'

def output_sample():
    for stack in allocated:
        if allocated[stack]:
            print sep.join([str(t), str(allocated[stack]/MB), folded[stack]])

# for each stack
for t, line in enumerate(sys.stdin):

    # parse line
    m = pat.match(line)
    if m:

        # get info
        event, addr, size, stack = m.groups()
        if event=='ALLOC':
            size = int(size)
            addrs[addr] = (-size, stack)
            if not stack in folded:
                f = sep.join(fun.split(s,1)[0].strip() for s in stack.split('|')[1:])
                folded[stack] = 'ROOT;' + f
                allocated[stack] = 0
        elif event=='FREE':
            size, stack = addrs[addr]

        # running stats
        allocated[stack] += size
        total_size += size
        max_size = max(total_size, max_size)

        # output this sample if total size has changed by more than a given proportion
        if abs(total_size-last_size) > 0.05 * max_size:
            output_sample()
            last_size = total_size


output_sample()

msg('max_size', max_size)
