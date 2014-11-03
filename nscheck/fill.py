import sys
import os

MiB = 1024*1024
GiB = 1024*MiB

fn = sys.argv[1]
buf = 'x' * 4096

print 'filling file', fn

f = open(fn, 'wb')

n = 0
while True:
    try:
        f.write(buf)
        n += len(buf)
        if (n%GiB == 0):
            print '%d GiB' % (n/GiB)
    except Exception as e:
        print '%.3f GiB' % (float(n)/GiB)
        print e
        break

os.remove(fn)
