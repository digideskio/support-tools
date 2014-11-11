import struct
import sys
import os
import datetime

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
# util
#

def flags_string(strings, flags):
    fs = []
    for i in strings:
        if flags&i:
            fs.append(strings[i])
    return '+'.join(fs)

class indent:
    def __init__(self):
        self._delta = '  '
        self.reset()
    def reset(self):
        self._indent = ''
    def get(self):
        return self._indent
    def set(self, indent):
        self._indent = indent
    def indent(self):
        self._indent += self._delta
    def outdent(self):
        self._indent = self._indent[:-len(self._delta)]
    def prt(self, at, s):
        print '%08x:%s %s' % (at, self._indent, s)

indent = indent()


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
    return at, ('DOC len=0x%x(%d) EOO=0x%x' % (l, l, at+l-5))

def info_string(buf, at):
    a, l = get_int(buf, at)
    sl = buf.find('\0', a) - a
    info = 'string len=%d strlen=%d' % (l, sl)
    if do_bson_detail:
        #info += ' "' + buf[a:a+l-1] + '"'
        info += ' =' + repr(buf[a:a+l-1])
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

def print_bson(buf, at, l=None, null_name=False):
    if l is None:
        at, l = get_int(buf, at)
        end = at + l - 4
    else:
        end = at + l
    while at < end:
        at, t = get_char(buf, at)
        if t==0:
            indent.outdent()
            indent.prt(at, 'EOO')
        else:
            ok = False
            if t in types:
                a, name = get_cstring(buf, at)
                if a<=end and (len(name)>0 or null_name) and len(name)<1000:
                    a, info = types[t](buf, a)
                    if a<=end:
                        indent.prt(at, '%s: %s' % (repr(name), info))
                        if types[t]==info_doc:
                            indent.indent()
                        at = a
                        ok = True
            if not ok:
                indent.prt(at, '? %02x %c' % (t, chr(t)))
    return end


def embedded_bson(buf, at, end, *args, **kwargs):
    if do_bson:
        if end-at >= 4:
            at, l = get_int(buf, at)
            i = indent.get()
            indent.indent()
            indent.prt(at, 'DOC len=%d' % l)
            indent.indent()
            l -= 4
            print_bson(buf, at, l, *args, **kwargs)
            indent.set(i)
            at += l
        if at < end:
            indent.indent()
            indent.prt(at, ' '.join(('%02x' % ord(c)) for c in buf[at:end]))
            indent.outdent()

#
# cells (entries) in a page
#

# cell.i
CELL_SHORT_KEY = 1
CELL_SHORT_KEY_PFX = 2
CELL_SHORT_VALUE = 3

CELL_ADDR_DEL = (0)            # Address: deleted
CELL_ADDR_INT = (1 << 4)       # Address: internal 
CELL_ADDR_LEAF = (2 << 4)      # Address: leaf
CELL_ADDR_LEAF_NO = (3 << 4)   # Address: leaf no overflow
CELL_DEL = (4 << 4)            # Deleted value
CELL_KEY = (5 << 4)            # Key
CELL_KEY_OVFL = (6 << 4)       # Overflow key
CELL_KEY_OVFL_RM = (12 << 4)   # Overflow key (removed)
CELL_KEY_PFX = (7 << 4)        # Key with prefix byte
CELL_VALUE = (8 << 4)          # Value
CELL_VALUE_COPY = (9 << 4)     # Value copy
CELL_VALUE_OVFL = (10 << 4)    # Overflow value
CELL_VALUE_OVFL_RM = (11 << 4) # Overflow value (removed)

# intpack.i
# 10xxxxxx          -> xxxxxx
# 110xxxxx yyyyyyyy -> xxxxxyyyyyyyy + 64
# 1110xxxx ...      -> ...
def unpack_uint(buf, at=0):
    i = ord(buf[at])
    if i&0xC0==0x80: # 1 byte
        return at+1, i&0x3F
    elif i&0xE0==0xC0: # 2 byte
        return at+2, (((i&0x1F)<<8) | ord(buf[at+1])) + 64
    elif i&0xE0==0xE0: # multi-byte
        i &= 0xF
        x = 0
        for j in range(i):
            x = (x<<8) | ord(buf[at+1+j])
        return at+1+i, x + 8192 + 64 # check this
    else:
        raise Exception('unhandled uint 0x%x)' % i)

def unhandled_desc(desc):
    raise Exception('unhandled desc=0x%x\n' % desc)        

def record_id(buf, at, sz):
    x = buf[at:at+sz]
    try:
        _, x = unpack_uint(x)
        return 'pack(' + str(x) + ')'
    except:
        return repr(x)
    

# collection, internal, key: record id (maybe partial?)
# collection, leaf, key:     record id
# collection, leaf, value:   bson
# index,      internal, key: bson (mabye compact? maybe partial?)
# index,      leaf, key:     bson (maybe compact?)
# index,      leaf, value:   record id
def cell_kv(desc, buf, at, is_short, is_key):
    start = at
    if is_short:
        at, sz = at+1, desc >> 2
        info = 'short'
    else:
        at, sz = unpack_uint(buf, at+1)
        sz += 64
        info =  'long'
    end = at + sz
    if is_collection:
        if is_key:
            x = record_id(buf,at,sz)
            indent.prt(start, 'key desc=0x%x(%s) sz=%d key=%s' % (desc, info, sz, x))
        else:
            indent.prt(start, 'val desc=0x%x(%s) sz=%d' % (desc, info, sz))
            embedded_bson(buf, at, end)
    elif is_index:
        if is_key:
            indent.prt(start, 'key desc=0x%x(%s) sz=%d' % (desc, info, sz))
            embedded_bson(buf, at, end, null_name=True)
        else:
            x = ' '.join(('%02x' % ord(c)) for c in buf[at:at+sz])
            indent.prt(start, 'val desc=0x%x(%s) sz=%d val=%s' % (desc, info, sz, x))
    else:
        if is_key:
            x = repr(buf[at:at+sz])
            indent.prt(start, 'key desc=0x%x(%s) sz=%d key=%s' % (desc, info, sz, x))
        else:
            indent.prt(start, 'val desc=0x%x(%s) sz=%d' % (desc, info, sz))
    return end

def cell_addr(desc, buf, at):
    a, sz = unpack_uint(buf, at+1)
    aa, a1 = unpack_uint(buf, a)
    aa, a2 = unpack_uint(buf, aa)
    aa, a3 = unpack_uint(buf, aa)
    #x = ' '.join('%02x'%ord(c) for c in buf[a:a+sz])
    indent.prt(at, 'val desc=0x%x sz=%d addr=%d,%d,0x%x' % (desc, sz, a1, a2, a3))
    return a + sz

def cell(buf, at):
    desc = ord(buf[at])
    if   desc&3==CELL_SHORT_KEY:      return cell_kv(desc, buf, at, is_short=True, is_key=True)
    elif desc&3==CELL_SHORT_VALUE:    return cell_kv(desc, buf, at, is_short=True, is_key=False)
    elif desc&3==CELL_SHORT_KEY_PFX:  unhandled_desc(desc)
    elif desc==CELL_KEY:              return cell_kv(desc, buf, at, is_short=False, is_key=True)
    elif desc==CELL_VALUE:            return cell_kv(desc, buf, at, is_short=False, is_key=False)
    elif desc==CELL_ADDR_LEAF_NO:     return cell_addr(desc, buf, at)
    else:                             unhandled_desc(desc)

#
# block_desc - 4KB at beginning of file
#

# block.h: WT_BLOCK_DESC, struct __wt_block_desc
block_desc_struct = struct.Struct('< I H H I I')
BLOCK_MAGIC = 120897

def block_desc(buf, at):
    block_desc = buf[at:at+block_desc_struct.size]
    magic, major, minor, cksum, _ = block_desc_struct.unpack(block_desc)
    ok = 'OK' if magic==BLOCK_MAGIC else 'ERROR'
    indent.prt(at, 'block_desc magic=%d(%s) major=%d minor=%d cksum=0x%x' % \
        (magic, ok, major, minor, cksum))
    return at + 4096

#
# block_manager - 4KB at end of file
#

def pair(buf, at):
    at, x = unpack_uint(buf, at)
    at, y = unpack_uint(buf, at)
    return at, x, y
    
def extlist(buf, at):
    at, magic, zero = pair(buf, at)
    ok = 'OK' if magic==71002 else 'ERROR' # xxx
    indent.prt(at, 'magic=%d(%s) zero=%d' % (magic, ok, zero))
    while True:
        at, off, sz = pair(buf, at)
        indent.prt(at, 'off=0x%x sz=0x%x' % (off, sz))
        if off==0:
            break


#
# page
#

# btmem.h: WT_PAGE_HEADER, struct __wt_page_header
page_header_struct = struct.Struct('< Q Q I I B B 2s')

page_types = {
    0: 'INVALID',        # Invalid page
    1: 'BLOCK_MANAGER',  # Block-manager page
    2: 'COL_FIX',        # Col-store fixed-len leaf
    3: 'COL_INT',        # Col-store internal page
    4: 'COL_VAR',        # Col-store var-length leaf page
    5: 'OVFL',           # Overflow page
    6: 'ROW_INT',        # Row-store internal page
    7: 'ROW_LEAF',       # Row-store leaf page */
}

# block.h: WT_BLOCK_HEADER, struct __wt_block_header
block_header_struct = struct.Struct('< I I B 3s')

def page(buf, at):

    # sz is relative to this
    start = at
    if do_entry:
        print

    # page header
    page_header = buf[at:at+page_header_struct.size]
    recno, gen, msz, entries, t, flags, _ = page_header_struct.unpack(page_header)
    ts = page_types[t] if t in page_types else None
    fs = flags_string({1: 'comp', 2: 'all0', 4: 'no0'}, flags)
    indent.prt(at, 'page recno=%d gen=%d msz=0x%x entries=%d type=%d(%s) flags=0x%x(%s)' % \
        (recno, gen, msz, entries, t, ts, flags, fs))
    at += page_header_struct.size

    # block header
    block_header = buf[at:at+block_header_struct.size]
    sz, cksum, flags, _ = block_header_struct.unpack(block_header)
    fs = flags_string({1: 'cksum'}, flags)
    indent.prt(at, 'block sz=0x%x cksum=0x%x flags=0x%x(%s)' % (sz, cksum, flags, fs))
    at += block_header_struct.size

    # entries
    indent.indent()
    if ts=='BLOCK_MANAGER':
        if do_block_manager_entry:
            extlist(buf, at)
    elif ts=='ROW_INT' or ts=='ROW_LEAF':
        if do_entry:
            for i in range(entries):
                at = cell(buf, at)
        else:
            print 'unhandled page type'
    indent.outdent()

    # done
    return start + (sz if ts and recno==0 else 4096) # xxx need better recovery


#
#
#

print '===', ' '.join(sys.argv[0:])

# file
fn = sys.argv[2]

# what type of file?
if 'c' in sys.argv[1]:
    is_collection = True
elif 'i' in sys.argv[1]:
    is_index = True
else:
    b = os.path.basename(fn)
    is_collection = b.startswith('collection') or b.startswith('_mdb_catalog')
    is_index = b.startswith('index')

# what to do
do_page = 'p' in sys.argv[1]
do_entry = 'e' in sys.argv[1]
do_block_manager_entry = do_entry or 'm' in sys.argv[1]
do_bson = 'b' in sys.argv[1] or 'B' in sys.argv[1]
do_bson_detail = 'B' in sys.argv[1]

# read the file xxx use mmap
f = open(fn)
buf = f.read()

if do_page:
    at = int(sys.argv[3], 0) if len(sys.argv)>3 else 0
    if at==0:
        at = block_desc(buf, at)
        while at < len(buf):
            at = page(buf, at)
    else:
        page(buf, at)


