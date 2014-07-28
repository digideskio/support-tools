import datetime
import struct
import sys
import collections
import base64

#
# bson
#

def get_char(buf, at):
    return at+1, ord(buf[at])

def get_int(buf, at):
    return at+4, struct.unpack_from('i', buf, at)[0]

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
        t = struct.unpack_from(fmt, buf, at+skip)[0] / scale
        at, info = info_basic(name, l, buf, at)
        try: t = datetime.datetime.utcfromtimestamp(t).isoformat() + 'Z'
        except Exception as e: t = str(e)
        return at, info + ' =' + t
    return info

def info_double(buf, at):
    d = struct.unpack_from('d', buf, at)[0]
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
#
#

btree_header_struct = struct.Struct("7s 7s H H H H")
btree_key_struct = struct.Struct("7s 7s H")
diskloc56_struct = struct.Struct("i 3s")

def diskloc56(buf):
    o, f = diskloc56_struct.unpack_from(buf)
    f = (ord(f[2])*256+ord(f[1]))*256+ord(f[0])
    return f, o

def print_btree(buf, at, l=None):
    parent, next, flags, empty, top, n = btree_header_struct.unpack_from(buf, at)
    parent_f, parent_o = diskloc56(parent)
    next_f, next_o = diskloc56(next)
    print '%x: btree parent=%d:%x next=%d:%x flags=%x empty=%x(%d) top=%x(%d) n=%x(%d)' % \
        (at, parent_f,parent_o, next_f,next_o, flags, empty, empty, top, top, n, n)
    kds = set()
    for i in range(n):
        a = at + 22 + 16*i
        child, loc, kdo = btree_key_struct.unpack_from(buf, a)
        child_f,child_o = diskloc56(child)
        loc_f,loc_o = diskloc56(loc)
        kd = at + 22 + kdo
        print '%x: key child=%d:%x loc=%d:%x kdo=%x kd=%x' % (a, child_f,child_o, loc_f,loc_o, kdo, kd),
        if do_btree_detail:
            print 'rec=%x' % at,
            bytes = ''
            for j in range(1,13):
                bytes += '%02x' % ord(buf[kd+j])
            print '%02x' % ord(buf[kd]), bytes,
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

extra_info = collections.defaultdict(str)

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
            print 'ERROR loop in %s list at %x' % ('next' if do_next else 'prev', at)
            break
        seen.add(at)
        rlen, ext, next, prev, blen = record_struct.unpack_from(buf, at)
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

record_struct = struct.Struct('i i i i I')

def print_record(buf, at, print_content, rlen, ext, next, prev, blen, pending=None):
    f = buf.find(find, at, at+rlen)
    if f >= 0:
        pending = do_pending(pending)
        print '%x: record rlen=%x(%d) end=%x ext=%x' % (at, rlen, rlen, at+rlen, ext),
        print 'next=%x prev=%x blen=%x(%d)%s' % (next, prev, blen, blen, extra_info[(buf,at)])
        if find:
            print '%x: found off=%x(%d)' % (f, f-at, f-at),
            for i in range(len(find) + 8):
                print '%02x' % ord(buf[f-4+i]),
            print
        if print_content:
            print_content(buf, at+16, rlen)
    return pending


def visit_records(buf, at, end, print_content, per_record, ext_at=None, pending=None):
    skipped = 0
    while at < end:
        rlen, ext, next, prev, blen = record_struct.unpack_from(buf, at)
        if ext_at and ext==ext_at and skipped!=0:
            print 'skipped', skipped
            skipped = 0
        bad = (ext_at!=None and ext!=ext_at) or rlen<=0
        if skipped==0:
            pending = per_record(buf, at, print_content if not bad else None, rlen, ext, next, prev, blen, pending)
        if bad:
            at += 1
            skipped += 1
        else:
            at += rlen


#
# extents
#

extent_struct = struct.Struct('i i i i i i i 128s i i i i i')

def extent(buf, at, check):
    sig, loc_f,loc_o, next_f,next_o, prev_f,prev_o, ns, l, first_f,first_o, last_f,last_o = \
        extent_struct.unpack_from(buf, at)
    if sig != 0x41424344:
        if check:
            print 'ERROR: bad sig %x at %x(%d)' % (sig, at, at)
        return None, None, None
    ns = ns[:ns.find('\0')]
    is_inx = '$' in ns and '_' in ns # xxx hack
    if is_inx and do_btree: print_content = print_btree
    elif not is_inx and do_bson: print_content = print_record_bson
    else: print_content = None
    def pending():
        print '%d:%x: extent sig=%x loc=%d:%x' % (loc_f, at, sig, loc_f, loc_o),
        print 'next=%x:%x prev=%x:%x' % (next_f, next_o, prev_f, prev_o),
        print 'ns=%s len=%x(%d)' % (ns, l, l),
        print 'first=%x:%x last=%x:%x' % (first_f, first_o, last_f, last_o)
    if do_records:
        r0 = at+176 if not is_inx else at+0x1000
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

def get_buf(fn):
    if not fn in bufs:
        bufs[fn] = open(fn).read()
    return bufs[fn]

def get_db_buf(dbpath, db, ext):
    return get_buf(dbpath + '/' + db + '.' + str(ext))


#
#
#

ns_struct = struct.Struct('i 128s i i   i i  152s    iiii  i i 160s i i ii i i i i i')
#                            name first last buckets stats l n inx          ce  cfnr

def collection(dbpath, ns):
    db = ns.split('.')[0]
    nsbuf = get_db_buf(dbpath, db, 'ns')
    at = 0
    while at+628 <= len(nsbuf):
        _, name, first_f,first_o, last_f,last_o, buckets, \
            _, _, _, _, lastExtentSize, nIndexes, indexes, \
            isCapped, maxDocsInCapped, _, _, systemFlags, \
            ce_f,ce_o, cfnr_f,cfnr_o = \
            ns_struct.unpack_from(nsbuf, at)
        name = name[:name.find('\0')]
        if (ns==db and name!='') or name==ns:
            print '--- %s first=%d:%x last=%d:%x, ce=%d:%x, cfn=%d:%x' % \
                (name, first_f, first_o, last_f, last_o, ce_f, ce_o, cfnr_f, cfnr_o)
            #print lastExtentSize, nIndexes
            if do_free:
                for i in range(19):
                    f, a = struct.unpack_from('i i', buckets, i*8)
                    j = 0
                    while f >= 0:
                        print "free[%d]+%d %d:%x" % (i, j, f, a)
                        try:
                            xbuf = get_db_buf(dbpath, db, f)
                            extra_info[(xbuf,a)] += ' free[%d]+%d' % (i, j)
                            _, _, f, a, _ = record_struct.unpack_from(xbuf, a)
                            j += 1
                        except:
                            #print "can't open file %d" % f
                            break
            if do_extents:
                f, o = first_f, first_o
                while o is not None and o > 0:
                    xbuf = get_db_buf(dbpath, db, f)
                    f, o, _ = extent(xbuf, o, True)
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
do_collection = 'c' in flags
do_free = 'f' in flags

find = ''

print_content = None
if do_btree: print_content = print_btree
if do_bson: print_content = print_record_bson

if do_collection:
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
    l = int(sys.argv[4]) if len(sys.argv)>4 else None
    print_bson(buf, at, l)
