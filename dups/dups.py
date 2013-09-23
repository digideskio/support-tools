import sys
import itertools

if len(sys.argv) != 3:
    print "usage: dups filename blocksize"
    sys.exit(-1)

f = open(sys.argv[1])
blocksize = int(sys.argv[2])

# map blocks to file offset (implemented as hash table)
blocks = {}

# report matching blocks
#
# don't report blocks of 0s
#
# in any case report number of non-0 bytes because it is not uncommon
# to have by coincidence identical blocks that are mostly 0s
# with only a couple of matching non-0 bytes at the beginning

for offset in itertools.count(0, blocksize):
    block = f.read(blocksize)
    if not block:
        break
    try:
        # if we've seen this block before and it's not all 0s then report it
        match = blocks[block]
        nonzero = blocksize - block.count('\0')
        if nonzero > 0:
            print "0x%x matches 0x%x; %d non-zero bytes" % (offset, match, nonzero)
    except KeyError:
        # remember offset of block iff we haven't seen this block before
        blocks[block] = offset
