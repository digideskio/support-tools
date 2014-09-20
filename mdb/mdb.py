import datetime
import struct
import sys
import collections
import base64
import mmap
import os

try:
    import snappy
except:
    #print 'snappy not available, will not decompress sections'
    snappy = None

#
# 2.4 for 2.6
#

try:
    from collections import defaultdict
except:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *args, **kwargs):
            dict.__init__(self, *args, **kwargs)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                self[key] = value = self.default_factory()
                return value

def xstruct(s):
    if hasattr(struct, 'Struct'): return struct.Struct(s)
    else: return s

structs = {}

def unpack_from(fmt, buf, start=0):
    if type(fmt)==str:
        if hasattr(struct, 'Struct'):
            if not fmt in structs:
                structs[fmt] = struct.Struct(fmt)
            fmt = structs[fmt]
        else:
            return struct.unpack(fmt, buf[start:start+struct.calcsize(fmt)])
    return fmt.unpack_from(buf, start)  



#
# bson
#

def get_char(buf, at):
    return at+1, ord(buf[at])

def get_int(buf, at):
    return at+4, unpack_from('i', buf, at)[0]

def get_cstring(buf, at):
    l = buf.find('\0', at) - at
    return at+l+1, buf[at:at+l]

def info_doc(buf, at):
    at, l = get_int(buf, at)
    return at, ('DOC len=%x(%d) EOO=%x' % (l, l, at+l-5))

def info_string(buf, at):
    a, l = get_int(buf, at)
    sl = buf.find('\0', a) - a
    info = 'string len=%d strlen=%d' % (l, sl)
    if do_bson_detail:
        info += ' "' + buf[a:a+l-1] + '"'
    if l > 0 and l < 16*1024*1024 and sl < l: pass
    elif sl != l-1: info += ' WARNING: EMBEDDED NULL'
    else: info += ' ERROR: NO NULL'
    return a+l, info


def info_cstring(buf, at):
    a, l = get_char(buf, at)
    info = 'string len=%d' % l
    if do_btree_detail:
        info += ' "' + buf[a:a+l] + '"'
    return a+l, info
    
def info_bindata(buf, at):
    at, l = get_int(buf, at)
    at, sub = get_char(buf, at)
    info = 'bindata len=%d sub=%d' % (l, sub)
    if do_bson_detail:
        for c in buf[at:at+l]:
            info += ' %02x' % ord(c)
        info += ' ' + base64.b64encode(buf[at:at+l])
    return at+l, info

def info_regexp(buf, at):
    at, e = get_cstring(buf, at)
    at, o = get_cstring(buf, at)
    return at, ('regexp len(e)=%d len(o)=%d' % (len(e), len(o)))

def info_basic(name, l, buf, at):
    for i in range(0,l):
        name += ' %02x' % ord(buf[at+i])
    return at+l, name

def info_time(name, l, fmt, scale=1, skip=0):
    def info(buf, at):
        t = unpack_from(fmt, buf, at+skip)[0] / scale
        at, info = info_basic(name, l, buf, at)
        try: t = datetime.datetime.utcfromtimestamp(t).isoformat() + 'Z'
        except Exception, e: t = str(e)
        return at, info + ' =' + t
    return info

def info_double(buf, at):
    d = unpack_from('d', buf, at)[0]
    at, info = info_basic('double', 8, buf, at)
    return at, '%s =%g' % (info, d)

def info_simple(name, l):
    def info(buf, at):
        return info_basic(name, l, buf, at)        
    return info

types = {
    0x01: info_double,
    0x02: info_string,
    0x03: info_doc,
    0x04: info_doc,
    0x05: info_bindata,
    0x06: info_simple('undefined', 0),
    0x07: info_time('objectid', 12, '>i'),
    0x08: info_simple('boolean', 1),
    0x09: info_time('datetime', 8, 'q', scale=1000),
    0x0a: info_simple('null', 0),
    0x0b: info_regexp,
    0x10: info_simple('int32', 4),
    0x11: info_time('timestamp', 8, 'i', skip=4),
    0x12: info_simple('int64', 8),
    0x7f: info_simple('maxkey', 0),
    0xff: info_simple('minkey', 0),
}

ctypes = {
    0x04: info_double,
    0x06: info_cstring,
    0x08: info_time('objectid', 12, '>i'),
}

def print_record_bson(buf, at, l):
    print_bson(buf, at, None)

def print_bson(buf, at, l=None):
    if l is None:
        at, l = get_int(buf, at)
        end = at + l - 4
    else:
        end = at + l
    #print "len=%x(%d) end=%x" % (l, l, end)
    while at < end:
        print '%x:' % at,
        at, t = get_char(buf, at)
        if t==0:
            print "EOO"
        else:
            ok = False
            if t in types:
                a, name = get_cstring(buf, at)
                if a<=end and len(name)>0 and len(name)<1000:
                    a, info = types[t](buf, a)
                    if a<=end:
                        print '%s: %s' % (name, info)
                        at = a
                        ok = True
            if not ok:
                print '? %02x %c' % (t, chr(t))



#
# journal
#

def hex(s):
    return ''.join(c.encode('hex') for c in s)

def hash(buf):
    n = len(buf) / 8 / 2;
    s = xstruct('< %dQ' % n)
    a = unpack_from(s, buf)
    a = sum(a[i]^i for i in range(n))
    b = unpack_from(s, buf, n*8)
    b = sum(b[i]^i for i in range(n))
    c = 0L
    for i in range(n*8*2, len(buf)):
        cc = ord(buf[i])
        if cc >= 128: cc -= 256
        c = (c << 8) | cc
    m = 0xffffffffffffffffL
    return (a^len(buf))&m, (b^c)&m

def print_journal(fn):

    # file structure
    header_struct = xstruct('< 5s 20s 1s 128s 2s Q')
    section_struct = xstruct('< I Q Q')
    footer_struct = xstruct('< I QQ Q 4s')
    align = 8192

    # open file
    f = open(fn, 'rb')
    sz = os.fstat(f.fileno()).st_size # 2.4 won't accept 0
    buf = mmap.mmap(f.fileno(), sz, prot=mmap.PROT_READ)
    
    # file header
    magic, date, _, path, _, fileid = unpack_from(header_struct, buf)
    path = path[:path.find('\0')]
    date = date[:date.find('\0')]
    print '%08x: header magic=%s date=%s path=%s fid=%x' % (0, hex(magic), date, path, fileid)
    at = 8192
    
    # traverse file
    while at < len(buf):
    
        # section header
        l, lsn, fid = unpack_from(section_struct, buf, at)
        lp = (l + align-1) & ~(align-1)
        section_at = at + 20
        footer_at = at + l - 32
        ok = 'OK'
        if fid!=fileid: fid = 'BAD'
        print '%08x: section l=%x(%d) lp=%x(%d) lsn=%x(%d) fid=%x(%s)' % \
            (at, l, l, lp, lp, lsn, lsn, fid, ok)
    
        # compute hash, compare with footer
        sentinel, hash_a, hash_b, reserved, magic = unpack_from(footer_struct, buf, footer_at)
        computed_hash_a, computed_hash_b = hash(buf[at:footer_at])
        hash_ok = 'OK'
        if not (hash_a==computed_hash_a and hash_b==computed_hash_b): ok = 'BAD'
        print '%08x: hash=%08x:%08x(%s)' % (at, computed_hash_a, computed_hash_b, hash_ok)
    
        # section
        try:
            if snappy:
                section = snappy.uncompress(buf[section_at:footer_at])
                print '%08x: uncompressed length=%x(%d)' % (section_at, len(section), len(section))
                if do_journal_entries:
                    print_journal_entries(section)
        except Exception, e:
            print '%08x: %s' % (section_at, e)
    
        # section footer
        print '%08x: footer sentinel=%x hash=%08x:%08x(%s) magic=%s' % \
            (footer_at, sentinel, hash_a, hash_b, hash_ok, hex(magic))
    
        # next section
        at += lp
    
    # eof
    print '%08x: eof' % len(buf)
    print '%08x: at' % at


def print_journal_entries(section):
    at = 0
    while at < len(section):
        (op,) = unpack_from('< I', section, at)
        if op==0xffffffff: # footer
            print '%08x: op=footer(%x)' % (at, op)
            break
        elif op==0xfffffffd: # create
            (l,) = unpack_from('< Q', section, at+20)
            fn = section[at+28:section.find('\0',at+28)]
            print '%08x: op=create(%x) l=%x(%d) fn=%s' % (at, op, l, l, fn)
            at += 28 + len(fn) + 1
            ctx = fn.split('.')[0]
        elif op==0xfffffffe: # context
            ctx = section[at+4:section.find('\0',at+4)]
            print '%08x: op=context(%x) ctx=%s' % (at, op, ctx)
            at += 4 + len(ctx) + 1
        elif op==0xfffffffc: # drop
            print '%08x: op=drop(%x) STOPPING NOT IMPL' % (at, op)
            break
        else: # write
            l = op
            ofs, f = unpack_from('< I I', section, at+4)
            sfx = f & 0x7fffffff
            if (sfx==0x7fffffff): sfx = 'ns'
            if (f&0x80000000): db = 'local'
            else: db = ctx
            print '%08x: op=write f=%x fn=%s ofs=%x(%d) l=%x(%d) ' % \
                (at, f, db + '.' + str(sfx), ofs, ofs, l, l)
            at += op + 12

#
#
#

btree_header_struct = xstruct("7s 7s H H H H")
btree_key_struct = xstruct("7s 7s H")
diskloc56_struct = xstruct("i 3s")

def diskloc56(buf):
    o, f = unpack_from(diskloc56_struct, buf)
    f = (ord(f[2])*256+ord(f[1]))*256+ord(f[0])
    return f, o

def print_btree(buf, at, l=None):
    parent, next, flags, empty, top, n = unpack_from(btree_header_struct, buf, at)
    parent_f, parent_o = diskloc56(parent)
    next_f, next_o = diskloc56(next)
    print '%x: btree parent=%d:%x next=%d:%x flags=%x empty=%x(%d) top=%x(%d) n=%x(%d)' % \
        (at, parent_f,parent_o, next_f,next_o, flags, empty, empty, top, top, n, n)
    kds = set()
    for i in range(n):
        a = at + 22 + 16*i
        child, loc, kdo = unpack_from(btree_key_struct, buf, a)
        child_f,child_o = diskloc56(child)
        loc_f,loc_o = diskloc56(loc)
        kd = at + 22 + kdo
        print '%x: key child=%d:%x loc=%d:%x kdo=%x kd=%x' % (a, child_f,child_o, loc_f,loc_o, kdo, kd),
        if do_btree_detail:
            print 'rec=%x' % at,
            t = ord(buf[kd])
            if t in ctypes:
                _, detail = ctypes[t](buf, kd+1)
            else:
                detail = ''
                for j in range(1,13):
                    detail += '%02x' % ord(buf[kd+j])
            print '%02x' % t, detail,
        print
        kds.add(kd)
    kds = list(sorted(kds))
    kds.append(at+l-16)
    for i in range(len(kds)-1):
        kd = kds[i]
        kdl = kds[i+1] - kds[i]
        print '%x: kd len=%x(%d)' % (kd, kdl, kdl),
        for j in range(kdl):
            print '%02x' % ord(buf[kd+j]),
        print
            

#
# extra per-record info
#

extra_info = defaultdict(str)

def do_pending(pending):
    if pending:
        pending()
    return None

def records_list(buf, start, end, at, do_next, pending):
    i = 0
    seen = set()
    while start <= at and at < end:
        if at in seen:
            pending = do_pending(pending)
            if do_next: print 'ERROR loop in next list at %x' % at
            else: print 'ERROR loop in prev list at %x' % at
            break
        seen.add(at)
        rlen, ext, next, prev, blen = unpack_from(record_struct, buf, at)
        if do_next:
            extra_info[(buf,at)] += ' first+%d' % i
            at = next
        else:
            extra_info[(buf,at)] += ' last-%d' % i
            at = prev
        i += 1
    return pending


def ts_key(buf, at):
    info_ts = info_time('', 8, 'i', skip=4)
    if buf[at+20:at+24]==chr(0x11)+'ts'+chr(0):
        k = buf[at+24:at+32][::-1]
        _, ts = info_ts(buf, at+24)
        prt = ts[ts.find('='):]
        return k, prt
    else:
        return None, None

def records_key(buf, at, end, ext_at, key, name):
    keys = []
    def do_keys(buf, at, do_bson, rlen, ext, next, prev, blen, pending):
        k, prt = key(buf, at)
        if k:
            keys.append((at, k, prt))
    visit_records(buf, at, end, None, do_keys, ext_at)
    keys = sorted(keys, key=lambda x: x[1])
    for i in range(len(keys)):
        at, k, prt = keys[i]
        extra_info[(buf,at)] += ' %s+%d %s' % (name, i, prt)



#
# records
#

record_struct = xstruct('i i i i I')

def print_record(buf, at, print_content, rlen, ext, next, prev, blen, pending=None):
    if find: found = buf.find(find, at, at+rlen)
    if not find or found >= 0:
        pending = do_pending(pending)
        print '%s%x: record rlen=%x(%d) end=%x ext=%x' % (exts[buf], at, rlen, rlen, at+rlen, ext),
        print 'next=%x prev=%x blen=%x(%d)%s' % (next, prev, blen, blen, extra_info[(buf,at)])
        if find:
            print '%s%x: found off=%x(%d)' % (exts[buf], found, found-at, found-at),
            for i in range(len(find) + 8):
                print '%02x' % ord(buf[found-4+i]),
            print
        if print_content:
            print_content(buf, at+16, rlen)
    return pending


def visit_records(buf, at, end, print_content, per_record, ext_at=None, pending=None):
    skipped = 0
    while at < end:
        rlen, ext, next, prev, blen = unpack_from(record_struct, buf, at)
        if ext_at and ext==ext_at and skipped!=0:
            print 'skipped', skipped
            skipped = 0
        bad = (ext_at!=None and ext!=ext_at) or rlen<=0
        if skipped==0:
            prt = print_content
            if bad: prt = None
            pending = per_record(buf, at, prt, rlen, ext, next, prev, blen, pending)
        if bad:
            at += 1
            skipped += 1
        else:
            at += rlen


#
# extents
#

extent_struct = xstruct('i i i i i i i 128s i i i i i')

def extent(buf, at, check):
    sig, loc_f,loc_o, next_f,next_o, prev_f,prev_o, ns, l, first_f,first_o, last_f,last_o = \
        unpack_from(extent_struct, buf, at)
    if sig != 0x41424344:
        if check:
            print 'ERROR: bad sig %x at %x(%d)' % (sig, at, at)
        return None, None, None
    ns = ns[:ns.find('\0')]
    #is_inx = '$' in ns and '_' in ns # xxx hack
    is_inx = '.$' in ns # xxx hack
    if is_inx and do_btree: print_content = print_btree
    elif not is_inx and do_bson: print_content = print_record_bson
    else: print_content = None
    def pending():
        print '%d:%x: extent sig=%x loc=%d:%x' % (loc_f, at, sig, loc_f, loc_o),
        print 'next=%d:%x prev=%d:%x' % (next_f, next_o, prev_f, prev_o),
        print 'ns=%s len=%x(%d)' % (ns, l, l),
        print 'first=%d:%x last=%d:%x' % (first_f, first_o, last_f, last_o)
    if do_records:
        if is_inx: r0 = at + 0x1000
        else: r0 = at + 176
        if do_records_next:
            pending = records_list(buf, r0, at+l, first_o, True, pending)
        if do_records_prev:
            pending = records_list(buf, r0, at+l, last_o, False, pending)
        if do_records_oplog:
            records_key(buf, r0, at+l, at, ts_key, 'ts')
        visit_records(buf, r0, at+l, print_content, print_record, at, pending)
        #def visit_records(buf, at, end, do_bson, per_record, ext_at=None, pending=None):
    else:
        pending()
    return next_f, next_o, l

def extents(buf, at, end):
    while at+176 < end:
        _, _, l = extent(buf, at, False)
        if l is None:
            break
        at += l

#
# files as buffers
#

bufs = {}
exts = defaultdict(str)

def get_buf(dbpath, db, ext):
    fn = dbpath + '/' + db + '.' + str(ext)
    if not fn in bufs:
        try:
            f = open(fn, 'rb')
            sz = os.fstat(f.fileno()).st_size # 2.4 won't accept 0
            m = mmap.mmap(f.fileno(), sz, prot=mmap.PROT_READ)
            bufs[fn] = m
            exts[m] = str(ext) + ':'
        except Exception, e:
            print e
            raise
    return bufs[fn]


#
#
#


ns_struct = xstruct('i 128s ii  i i  152s    iiii  i i 160s i i ii i ii ii   i  ii   ii ii i')
#                      name 1st last buckets stats l n inx      pf f ce cfnr vv mk   ex ip

inx_details_struct = xstruct('i i i i')


def collection(dbpath, ns):
    db = ns.split('.')[0]
    nsbuf = get_buf(dbpath, db, 'ns')
    at = 0
    while at+628 <= len(nsbuf):
        _, name, first_f,first_o, last_f,last_o, buckets, \
            _, _, count_l, count_h, lastExtentSize, nIndexes, indexes, \
            isCapped, maxDocsInCapped, _, _, systemFlags, \
            ce_f,ce_o, cfnr_f,cfnr_o, _, mkl, mkh,  _, _, extra, _, inProgress = \
            unpack_from(ns_struct, nsbuf, at)
        count = (count_h << 32) + count_l
        mk = (mkh << 32) + mkl
        name = name[:name.find('\0')]
        if (ns==db and name!='') or name==ns:
            print '%08x: namespace name=%s first=%d:%x last=%d:%x, ce=%d:%x, cfn=%d:%x' % \
                (at, name, first_f, first_o, last_f, last_o, ce_f, ce_o, cfnr_f, cfnr_o)
            if do_collection_indexes:
                print 'nIndexes=%d extra=%d inProgress=%d mk=%x' % \
                    (nIndexes, extra, inProgress, mk)
                for i in range(nIndexes+inProgress):
                    if i<10: a = at+324+i*16
                    else: a = at+132+8+extra+(i-10)*16
                    inx = nsbuf[a:a+16]
                    btree_f, btree_o, info_f, info_o = unpack_from(inx_details_struct, inx)
                    print '%x: index %d: btree %d:%x info %d:%x mk %d' % \
                        (a, i, btree_f, btree_o, info_f, info_o, (mk>>i)&1)
                    if do_collection_details:
                        ibuf =  get_buf(dbpath, db, info_f)
                        visit_records(ibuf, info_o, info_o+1, print_record_bson, print_record)
                        bbuf =  get_buf(dbpath, db, btree_f)
                        visit_records(bbuf, btree_o, btree_o+1, print_btree, print_record)
            if do_free:
                for i in range(19):
                    f, a = unpack_from('i i', buckets, i*8)
                    j = 0
                    while True:
                        print "free[%d]+%d %d:%x" % (i, j, f, a)
                        if f < 0:
                            break
                        try:
                            xbuf = get_buf(dbpath, db, f)
                            extra_info[(xbuf,a)] += ' free[%d]+%d' % (i, j)
                            _, _, f, a, _ = unpack_from(record_struct, xbuf, a)
                            j += 1
                        except:
                            break
            if do_extents:
                f, o = first_f, first_o
                while o is not None and o > 0:
                    xbuf = get_buf(dbpath, db, f)
                    f, o, _ = extent(xbuf, o, True)
        elif ns==db and do_collection_details:
            print '%08x: empty' % at
        at += 628


# 
# 
# 
# 

print '===', ' '.join(sys.argv)
flags = sys.argv[1]

do_extents = 'x' in flags 
do_grep = 'g' in flags
do_records = 'r' in flags
do_records_multi = 's' in flags
do_records_next = 'n' in flags
do_records_prev = 'p' in flags
do_bson = 'b' in flags or 'B' in flags
do_bson_detail = 'B' in flags
do_btree = 't' in flags or 'T' in flags
do_btree_detail = 'T' in flags
do_records_oplog = 'o' in flags
do_collection = 'c' in flags or 'C' in flags
do_collection_details = 'C' in flags
do_collection_indexes = 'i' in flags
do_free = 'f' in flags
do_journal = 'j' in flags
do_journal_entries = 'e' in flags # not impl

find = ''

print_content = None
if do_btree: print_content = print_btree
if do_bson: print_content = print_record_bson

if do_journal:
    print_journal(sys.argv[2])
elif do_collection:
    dbpath = sys.argv[2]
    ns = sys.argv[3]
    collection(dbpath, ns)
elif do_grep: # mdb g[b] file bytes
    buf = open(sys.argv[2]).read()
    find = ''
    for c in sys.argv[3:]:
        if len(c)==2: find += chr(int(c,16))
        else: find += c
    do_records = True
    extents(buf, 0x2000, len(buf))
elif do_extents: # mdb x[rb] file [addr]
    buf = open(sys.argv[2]).read()
    if len(sys.argv) > 3: # single extent
        at = int(sys.argv[3], 0)
        end = at+177
    else: # whole file
        at = 0x2000
        end = len(buf)
    extents(buf, at, end)
elif do_records: # mdb r[b] file addr
    buf = open(sys.argv[2]).read()
    at = int(sys.argv[3], 0)
    visit_records(buf, at, at+1, print_content, print_record)
elif do_records_multi: # mdb s[b] file addr
    buf = open(sys.argv[2]).read()
    at = int(sys.argv[3], 0)
    visit_records(buf, at, len(buf), print_content, print_record)
elif do_bson: # mdb b file addr [len]
    buf = open(sys.argv[2]).read()
    at = int(sys.argv[3], 0)
    l = None
    if len(sys.argv)>4: l = int(sys.argv[4])
    print_bson(buf, at, l)
