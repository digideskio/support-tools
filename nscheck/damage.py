import sys
import mmap
import os

fn = sys.argv[1]
off = int(sys.argv[2],0)
l = int(sys.argv[3],0)

mode, prot = 'a+b', mmap.PROT_READ | mmap.PROT_WRITE
f = open(fn, mode)
sz = os.fstat(f.fileno()).st_size # 2.4 won't accept 0
m = mmap.mmap(f.fileno(), sz, prot=prot)

m[off:off+l] = 'xyz\0' * (l/4)
