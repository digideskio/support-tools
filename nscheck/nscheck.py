import struct
import sys
import mmap
import os
import traceback
import string

# for initializing repaired file
zeros = '\0' * (1024*1024)

# entry classifications
empty, good, repairable, irreparable = range(4)

# hash a namespace name (see Namespace::hash() in namespace-inl.h)
def ns_hash(name):
    x = 0
    for c in name:
        x = x * 131 + ord(c)
    return (x & 0x7fffffff) | 0x8000000

# check a single .ns file
class NsFile:

    # cumulative state per ns file
    def __init__(self):
        self.seen_names = set()
        self.n_repairable = 0
        self.n_irreparable = 0

    # classify an entry
    def classify(self, view, at, db):
    
        # extract entry info
        hash, name = struct.unpack('< I 128s', view[at:at+132])
        try: name = name[0:name.index('\0')]
        except ValueError: pass
    
        # classify
        classification, message = good, 'OK'
        if not hash:
            classification, message = empty, 'OK'
        elif not name.startswith(db + '.'):
            classification, message = repairable, 'BAD NAME'
        elif hash != ns_hash(name):
            classification, message = irreparable, 'BAD HASH'
        elif name in self.seen_names:
            classification, message = irreparable, 'DUPLICATE NAME'
    
        # update cumulative state, finish
        self.seen_names.add(name)
        if classification == repairable:
            self.n_repairable += 1
        if classification == irreparable:
            self.n_irreparable += 1
        return name, classification, message

    def check(self, fn, old_view, new_view):
        db = os.path.basename(fn).split('.')[0]
        entry_len = 628
        at = 0
        while at+entry_len <= len(old_view):
            name, classification, message = self.classify(old_view, at, db)
            if repair:
                if classification == repairable:
                    message += ' - REPAIRED'
                elif classification == irreparable:
                    message += ' - NOT REPAIRED'
                if classification==good or classification==irreparable:
                    new_view[at:at+entry_len] = old_view[at:at+entry_len]
            else:
                if classification == repairable:
                    message += ' - REPAIRABLE'
                elif classification == irreparable:
                    message += ' - NOT REPAIRABLE'
            if classification != empty:
                print '%08x: namespace name=%s  %s' % (at, repr(name)[1:-1], message)
            at += entry_len
    
    def open_and_check(self, old_fn):

        print 'checking %s' % old_fn        
        old_f = new_f = old_view = new_view = None

        try:

            # map old file for reading
            old_f = open(old_fn, 'rb')
            sz = os.fstat(old_f.fileno()).st_size
            old_view = mmap.mmap(old_f.fileno(), sz, prot=mmap.PROT_READ)

            # open repaired file for writing, zero it, map it
            if repair:
                new_fn = old_fn + '.repaired'
                new_f = open(new_fn, 'w+b')
                i = 0
                while i < sz:
                    l = min(len(zeros), sz-i)
                    new_f.write(zeros[0:l])
                    i += l
                new_f.flush() # ensure everything actually written to file
                new_view = mmap.mmap(new_f.fileno(), sz, prot=mmap.PROT_WRITE)

            # check it
            self.check(old_fn, old_view, new_view)

            # summarize status
            if repair:
                os.fsync(new_f.fileno()) # ensure all changes flushed to disk
                print '%d errors were detected and repaired' % self.n_repairable
                if self.n_irreparable:
                    print '%d errors could not be repaired - please contact MongoDB support' % \
                        self.n_irreparable
                else:
                    backup_fn = old_fn + '.backup'
                    try:
                        if os.path.exists(backup_fn):
                            raise Exception('%s already exists' % backup_fn)
                        os.rename(old_fn, backup_fn)
                        os.rename(new_fn, old_fn)
                        print '%s has been repaired; old file has been saved as %s' % \
                            (old_fn, backup_fn)
                    except Exception, e:
                        print 'could not rename files to complete repair: %s' % e
            else:
                print '%d detected errors need repair' % self.n_repairable
                if self.n_irreparable:
                    print '%d errors cannot be repaired - please contact MongoDB support' % \
                        self.n_irreparable
            print

        except Exception, e:
            print 'could not check %s: %s' % (old_fn, e)
            traceback.print_exc()

        # close stuff
        if old_view: old_view.close()
        if old_f: old_f.close()
        if new_view: new_view.close()
        if new_f: new_f.close()


def walk(fn):
    if os.path.isdir(fn):
        for n in sorted(os.listdir(fn)):
            walk(os.path.join(fn, n))
    elif fn.endswith('.ns'):
        NsFile().open_and_check(fn)

repair = '--repair' in sys.argv[1:]

if __name__ == "__main__":
    for fn in sys.argv[1:]:
        if not fn.startswith('--'):
            walk(fn)
