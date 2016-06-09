import collections
import mmap
import os
import re
import struct
import zlib
import sys

def msg(*s):
    print >>sys.stderr, ' '.join(s)

#
# basic bson parser, to be extended as needed
# has optional special handling for ftdc:
#     returns numeric types as int64
#     ignores non-metric fields
# returns result as tree of OrderedDict, preserving order
#

int32 = struct.Struct('<i')
uint32 = struct.Struct('<I')
int64 = struct.Struct('<q')
uint64 = struct.Struct('<Q')
double = struct.Struct('<d')

BSON = collections.OrderedDict

def read_bson_doc(buf, at, ftdc=False):
    doc = BSON()
    doc_len = int32.unpack_from(buf, at)[0]
    doc.bson_len = doc_len
    doc_end = at + doc_len
    at += 4
    while at < doc_end:
        bson_type = ord(buf[at])
        at += 1
        name_end = buf.find('\0', at)
        n = buf[at : name_end]
        at = name_end + 1
        if bson_type==0: # eoo
            return doc
        elif bson_type==1: # double
            v = double.unpack_from(buf, at)[0]
            if ftdc: v = int(v)
            l = 8
        elif bson_type==2: # string
            l = uint32.unpack_from(buf, at)[0]
            at += 4
            v = buf[at : at+l-1] if not ftdc else None
        elif bson_type==3: # subdoc
            v = read_bson_doc(buf, at, ftdc)
            l = v.bson_len
        elif bson_type==4: # array
            v = read_bson_doc(buf, at, ftdc)
            l = v.bson_len
            if not ftdc: v = v.values() # return as array
        elif bson_type==8: # bool
            v = ord(buf[at])
            l = 1
        elif bson_type==5: # bindata
            l = uint32.unpack_from(buf, at)[0]
            at += 5 # length plus subtype
            v = buf[at : at+l] if not ftdc else None
        elif bson_type==7: # objectid
            v = None # xxx always ignore for now
            l = 12
        elif bson_type==9: # datetime
            v = uint64.unpack_from(buf, at)[0]
            v = int(v) if ftdc else v / 1000.0
            l = 8
        elif bson_type==16: # int32
            v = int32.unpack_from(buf, at)[0]
            if ftdc: v = int(v)
            l = 4
        elif bson_type==17: # timestamp
            v = BSON()
            v['t'] = int(uint32.unpack_from(buf, at)[0]) # seconds
            v['i'] = int(uint32.unpack_from(buf, at+4)[0]) # increment
            l = 8
        elif bson_type==18: # int64
            v = int(int64.unpack_from(buf, at)[0])
            l = 8
        else:
            raise Exception('unknown type %d(%x) at %d(%x)' % (bson_type, bson_type, at, at))
        if v != None:
            doc[n] = v
        at += l
    assert(not 'eoo not found') # should have seen an eoo and returned


def decode_chunk(chunk_doc):
    
    # our result is a map from metric keys to list of values for each metric key
    # a metric key is a path through the sample document represented as a tuple
    metrics = collections.OrderedDict()

    # decompress chunk data field
    data = chunk_doc['data']
    data = data[4:] # skip uncompressed length, we don't need it
    data = zlib.decompress(data)

    # read reference doc from chunk data, ignoring non-metric fields
    ref_doc = read_bson_doc(data, 0, ftdc=True)
    #print_bson_doc(ref_doc)

    # traverse the reference document and extract map from metrics keys to values
    def extract_keys(doc, n=()):
        for k, v in doc.items():
            nn = n + (k,)
            if type(v)==BSON:
                extract_keys(v, nn)
            else:
                metrics[nn] = [v]
    extract_keys(ref_doc)

    # get nmetrics, ndeltas
    nmetrics = uint32.unpack_from(data, ref_doc.bson_len)[0]
    ndeltas = uint32.unpack_from(data, ref_doc.bson_len+4)[0]
    nsamples = ndeltas + 1
    at = ref_doc.bson_len + 8
    if nmetrics != len(metrics):
        # xxx remove when SERVER-20602 is fixed
        msg('ignoring bad chunk: nmetrics=%d, len(metrics)=%d' % (
            nmetrics, len(metrics)))
        return None

    # unpacks ftdc packed ints
    def unpack(data, at):
        res = 0
        shift = 0
        while True:
            b = ord(data[at])
            res |= (b&0x7F) << shift
            at += 1
            if not (b&0x80):
                if res > 0x7fffffffffffffff: # negative 64-bit value
                    res = int(res-0x10000000000000000)
                return res, at
            shift += 7

    # unpack, run-length, delta, transpose the metrics
    nzeroes = 0
    for metric_values in metrics.values():
        value = metric_values[-1]
        for _ in xrange(ndeltas):
            if nzeroes:
                delta = 0
                nzeroes -= 1
            else:
                delta, at = unpack(data, at)
                if delta==0:
                    nzeroes, at = unpack(data, at)
            value += delta
            metric_values.append(value)
    assert(at==len(data))

    # our result
    return metrics


#
#
#

stacks = {}

def get_stack_definitions(mongod_log):
    for line in open(mongod_log):
        m = re.search('heapProfile (stack[0-9]+): ({.*})', line)
        if m:
            shortName = m.group(1)
            stack = m.group(2)
            stack = ';'.join(re.findall('[0-9]+: "([^"]*)"', stack))
            stacks[shortName] = stack

def get_chunks(dn):

    # for each file in diagnostic.data in sorted order
    for fn in sorted(os.listdir(dn)):

        # open and map file
        fn = os.path.join(dn, fn)
        msg('reading', fn)
        f = open(fn)
        buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        at = 0

        # traverse the file reading type 1 chunks
        while at < len(buf):
            try:
                chunk_doc = read_bson_doc(buf, at)
                at += chunk_doc.bson_len
                if chunk_doc['type']==1:
                    yield decode_chunk(chunk_doc)
            except Exception as e:
                msg('stopping at bad bson doc (%s)' % e)
                return

        # bson docs should exactly cover file
        assert(at==len(buf))

def get_stacks(mongod_log, diagnostic_data):
    get_stack_definitions(mongod_log)
    print '# metric=MB format=%.3f'
    print 'time;MB;stack'
    for metrics in get_chunks(diagnostic_data):
        ts = metrics[('serverStatus', 'localTime')]
        for m, vs in metrics.items():
            if m[:3]==('serverStatus','heapProfile','stacks') and m[-1]=='activeBytes':
                shortName = m[3]
                for t, v in zip(ts,vs):
                    t = t / 1000.0
                    v = v / 1024.0 / 1024.0
                    print str(t) + ';' + str(v) + ';' + stacks[shortName]

if (len(sys.argv) != 3):
    msg('usage: %s mongod_log diagnostic_data' % sys.argv[0])
    sys.exit(-1)

get_stacks(mongod_log=sys.argv[1], diagnostic_data=sys.argv[2])

