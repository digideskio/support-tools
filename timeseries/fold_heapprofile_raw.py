import sys
import struct
import re
import os

addrs = {}

# headers for calltree tool
print '# metric=MB format=%.3f'
print 'time;MB;stack'

# each file
for sample in sys.argv[1:]:
    
    # file time is sample time
    stat = os.stat(sample)
    t = stat.st_mtime

    # read symbols
    ignore = re.compile('(\(.*\))?<.*>$')
    f = open(sample)
    while True:
        line = f.readline().strip()
        if line.startswith('--- profile'):
            break
        elif line.startswith('0x'):
            addr, funs = line.split(' ', 1)
            addr = int(addr,0)
            funs = funs.split('--')
            addrs[addr] = [ignore.sub('', fun) for fun in funs]
    
    # get next 64-bit int from file
    uint64 = struct.Struct('<Q')
    def next_uint64(f):
        return uint64.unpack(f.read(8))[0]

    # skip profile header
    for i in range(5):
        next_uint64(f)

    # read profile
    while True:
        try:
            size = next_uint64(f)
        except struct.error: # eof
            break
        count = next_uint64(f)
        stack = []
        for i in range(count):
            addr = next_uint64(f)
            if addr != 0xffffffffffffffff:
                stack += addrs[addr]
        mb = size / 1024.0 / 1024.0
        if mb >= 1:
            print str(t) + ';' + str(mb) + ';' + ';'.join(reversed(stack))

