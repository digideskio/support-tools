import collections
import math
import mmap
import os
import struct
import time
import zlib

import ftdc
import util

#
# for efficient processing metric names are represented as a single string
# consisting of the BSON path elements joined by SEP
# use / instead of . because some metrics names include .
# xxx now used elsewhere, e.g. for ordinary json, so this should move...
#

SEP = '/'

def join(*s):
    return ftdc.SEP.join(s)


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


def print_bson_doc(doc, prt=util.msg, indent=''):
    for k, v in doc.items():
        if type(v)==BSON:
            prt(indent + k)
            print_bson_doc(v, prt, indent+'    ')
        else:
            prt(indent + k, v)
        

#
# manage the lazy decoding of a chunk
# state 0: chunk doc has been obtained; this is very fast as these are only pointers into the file
# state 1: data has ben zlib decompressed, metadata and ref sample extracted, but no deltas
#          this is useful for the case where we show only one document per chunk
# state 2: sample deltas have been processed and all samples obtained
#

class Chunk:

    def __init__(self, chunk_doc):
        self.chunk_doc = chunk_doc
        self._id = chunk_doc['_id']
        self._len = chunk_doc.bson_len
        self.state = 0 # 0: nothing read; 1: read ref doc and metadata; 2: read all incl deltas
        self.metrics = None
        self.nsamples = 0
        self.nmetrics = 0
        self.ndeltas = 0
        self.data = None

    def __len__(self):
        return self._len

    def get_first(self):

        # did we already read ref doc and metadata?
        if self.state >= 1:
            assert(self.metrics)
            return self.metrics

        # map from metric names to list of values for each metric
        # metric names are paths through the sample document
        self.metrics = collections.OrderedDict()
        self.metrics._id = self.chunk_doc['_id']
    
        # decompress chunk data field
        data = self.chunk_doc['data']
        data = data[4:] # skip uncompressed length, we don't need it
        data = zlib.decompress(data)
    
        # read reference doc from chunk data, ignoring non-metric fields
        ref_doc = read_bson_doc(data, 0, ftdc=True)
        #print_bson_doc(ref_doc)
    
        # traverse the reference document and extract metric names
        def extract_names(doc, n=''):
            for k, v in doc.items():
                nn = n + ftdc.SEP + k if n else k
                if type(v)==BSON:
                    extract_names(v, nn)
                else:
                    self.metrics[nn] = [v]
        extract_names(ref_doc)
    
        # get nmetrics, ndeltas
        self.nmetrics = uint32.unpack_from(data, ref_doc.bson_len)[0]
        self.ndeltas = uint32.unpack_from(data, ref_doc.bson_len+4)[0]
        self.nsamples = self.ndeltas + 1
        at = ref_doc.bson_len + 8
        if self.nmetrics != len(self.metrics):
            # xxx remove when SERVER-20602 is fixed
            util.msg('ignoring bad chunk: nmetrics=%d, len(metrics)=%d' % (
                self.nmetrics, len(self.metrics)))
            return None
        #assert(self.nmetrics==len(metrics))

        # record data and position in data for decompressing deltas when we need them
        self.data = data[at:]

        # release the chunk_doc as the needed info is now parsed into self.metrics, self.data, etc.
        self.chunk_doc = None

        # our result, containing only the first (reference) sample
        self.state = 1
        return self.metrics

    def get_all(self):
        
        # did we already process the deltas?
        if self.state >= 2:
            return self.metrics

        # read the first reference sample and metadata if we haven't already
        self.get_first()

        # self.data was left where the deltas are encoded by self.get_first()
        data = self.data
        at = 0

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
        for metric_values in self.metrics.values():
            value = metric_values[-1]
            for _ in xrange(self.ndeltas):
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
    
        # release the data as the info it contained is now in self.metrics
        self.data = None

        # our result
        self.state = 2
        return self.metrics


#
# manage the file cache
# entries are invalidated if file mod time changes
#

class File(util.Cache):

    # on __init__ we read the sequence of chunks in the file
    # this does minimal actual work since it mmaps the files
    # and only needs to read a few bytes for each chunk to construct
    # the chunk bson document, consisting largely of pointers into the file
    def __init__(self, fn):
        
        # open and map file
        f = open(fn)
        buf = mmap.mmap(f.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
        at = 0

        # traverse the file reading type 1 chunks
        self.chunks = []
        while at < len(buf):
            try:
                chunk_doc = read_bson_doc(buf, at)
                at += chunk_doc.bson_len
                if chunk_doc['type']==1:
                    self.chunks.append(Chunk(chunk_doc))
            except Exception as e:
                util.msg('stopping at bad bson doc (%s)' % e)
                return

        # bson docs should exactly cover file
        assert(at==len(buf))

    def __iter__(self):
        return iter(self.chunks)


#
# reads the metrics file or directory specified by fn
# yields a sequence of metrics dictionaries
#

def read(ses, fn, opt, progress=True):

    # initial progress message
    if progress:
        ses.progress('reading %s' % fn)

    # metrics files start with 'metrics.'
    is_ftdc_file = lambda fn: os.path.basename(fn).startswith('metrics.')

    # get concatenated list of chunks for all files
    chunks = []
    if os.path.isdir(fn):
        for f in sorted(os.listdir(fn)):
            if is_ftdc_file(f):
                chunks += File.get(os.path.join(fn,f))
    elif is_ftdc_file(fn):
        chunks += File.get(fn)
    if not chunks:
        raise Exception(fn + ' is not an ftdc file or directory')

    # compute time ranges for each chunk using _id timestamp
    for i in range(len(chunks)):
        t = chunks[i]._id
        fudge = -300 # xxx _id is end instead of start; remove when SERVER-20582 is fixed
        chunks[i].start_time = t + fudge
        if i>0:
            chunks[i-1].end_time = t
    chunks[-1].end_time = float('inf') # don't know end time; will filter last chunk later

    # roughly filter by timespan using _id timestamp as extracted above
    # fine filtering will be done in series_process_dict
    in_range = lambda chunk: chunk.start_time <= opt.before and chunk.end_time >= opt.after
    filtered_chunks = [chunk for chunk in chunks if in_range(chunk)]

    # init stats for progress report
    total_bytes = sum(len(chunk) for chunk in filtered_chunks)
    read_chunks = 0
    read_samples = 0
    read_bytes = 0
    used_samples = 0

    # compute number of output samples desired for overview mode
    # uses time-filtered data sizes so resolution automatically increases for smaller timespans
    # returns a subset of the samples, aiming for each sample to represent same number of bytes,
    # except that we return at least one sample for each chunk
    if opt.overview=='heuristic':
        overview = 1000
        util.msg('limiting output to %d samples; use --overview to override' % overview)
    elif opt.overview=='none':
        overview = float('inf')
    else:
        overview = int(opt.overview)
    overview_bytes = int(max(total_bytes / overview, 1))

    # we already filtered filtered_chunk_docs by type and time range
    for chunk in filtered_chunks:

        # compute desired subset of metrics based on target number of samples
        max_samples = (read_bytes+len(chunk)) / overview_bytes - read_bytes / overview_bytes
        if max_samples <= 1:
            metrics = chunk.get_first()
            metrics = BSON((n,[v[0]]) for (n,v) in metrics.items())
            used_samples += 1
        else:
            metrics = chunk.get_all()
            every = int(math.ceil(float(chunk.nsamples)/max_samples))
            if every != 1:
                metrics = BSON((n,v[0::every]) for (n,v) in metrics.items())
            used_samples += chunk.nsamples / every
        yield metrics

        # report progress
        read_chunks += 1
        read_bytes += len(chunk)
        read_samples += chunk.nsamples
        if progress and (read_chunks%10==0 or read_bytes==total_bytes):
            msg = '%d chunks, %d samples, %d bytes (%.0f%%), %d bytes/sample; %d samples used' % (
                read_chunks, read_samples, read_bytes, 100.0*read_bytes/total_bytes,
                read_bytes/read_samples, used_samples
            )
            ses.progress(msg)

    if used_samples != read_samples:
        s = 'displaying overview of ~%d of ~%d samples in selected time range (use z to zoom in)'
        ses.advise(s % (used_samples, read_samples))
    else:
        ses.advise('displaying all ~%d samples in selected time range' % used_samples)

#
# get raw metrics at a specified time. bit of a hack:
#   only includes metrics, does not include full reference doc
#   metrics are not stored as bson document so we reconstruct one from the SEP-joined metrics names
#   assumes 'serverStatus/localTime' exists
#
def info(ses, fn, t, prt=util.msg):

    class Opt:
        def __init__(self, t):
            self.after = t
            self.before = float('inf')
            self.overview = 'none'

    def put_bson(bson, n, v):
        if len(n)>1:
            if not n[0] in bson:
                bson[n[0]] = BSON()
            put_bson(bson[n[0]], n[1:], v)
        else:
            bson[n[0]] = v

    # xxx assumes this exists
    time_metric = ftdc.join('serverStatus', 'localTime')

    # find and print the first sample after t (only)
    for metrics in read(ses, fn, Opt(t), progress=False):
        for sample, sample_time in enumerate(metrics[time_metric]):
            sample_time = sample_time / 1000.0
            if sample_time >= t:
                break
        bson = BSON()
        for name, value in metrics.items():
            put_bson(bson, name.split(ftdc.SEP), value[sample])
        prt('%s at t=%.3f' % (fn, t))
        print_bson_doc(bson, prt, '    ')
        break

def dbg(fn, opt, show=True):
    def pt(t):
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(t/1000)) + ('.%03d' % (t%1000))
    for metrics in read(None, fn, opt):
        if show:
            if 'serverStatus.localTime' in metrics:
                sslt = metrics['serverStatus.localTime']
                util.msg(metrics._id, pt(metrics._id), pt(sslt[0]), pt(sslt[-1]),
                         'ds', len(sslt), 'ms', len(metrics))
            else:
                #print 'no serverStatus.localTime'
                util.msg(metrics.keys())

