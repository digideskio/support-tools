import struct
import sys
import mmap
import os
import traceback

entry_len = 628

def check(m, db):
    at = 0
    errors = 0
    while at+entry_len <= len(m):
        hash, name = struct.unpack('< I 128s', m[at:at+132])
        if hash:
            name = name[0:name.find('\0')]
            if not name.startswith(db + '.'):
                err = 'ERROR'
                if repair:
                    m[at:at+entry_len] = '\0' * entry_len
                    err += ' - REPAIRED'
                if detail:
                    print '%08x: namespace %s' % (at, err)
                errors += 1
            else:
                if detail:
                    print '%08x: namespace name=%s OK' % (at, name)
        at += entry_len
    return errors

def walk(fn):
    if os.path.isdir(fn):
        for n in os.listdir(fn):
            walk(os.path.join(fn, n))
    elif fn.endswith('.ns'):
        if detail:
            print 'checking %s' % fn
        f = m = None
        try:
            mode, prot = 'rb', mmap.PROT_READ
            if repair:
                mode, prot = 'a+b', mmap.PROT_READ | mmap.PROT_WRITE
            f = open(fn, mode)
            sz = os.fstat(f.fileno()).st_size # 2.4 won't accept 0
            m = mmap.mmap(f.fileno(), sz, prot=prot)
            errors = check(m, os.path.basename(fn).split('.')[0])
            if errors:
                print 'checked %s: %d ERRORS' % (fn, errors)
            else:
                print 'checked %s: OK' % (fn)
        except Exception, e:
            print 'problem checking %s: %s' % (fn, e)
            #traceback.print_exc()
        if m: m.close()
        if f: f.close()

repair = '--repair' in sys.argv[1:]
detail = '--detail' in sys.argv[1:] or repair

for fn in sys.argv[1:]:
    if not fn.startswith('--'):
        walk(fn)
